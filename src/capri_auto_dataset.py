"""Automatic STT + word-aligned WAV segmentation for Capri's Piper Studio.

Uses local faster-whisper/Silero VAD, then ffmpeg for sample-accurate PCM output.
AI transcripts are drafts; the Studio does not approve them for training.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Callable, Iterable
import uuid
from capri_piper_import import audio_duration_seconds

AUTO_STT_WINDOW_SECONDS = 600.0  # Bounded to 10 minutes of decoded audio in memory
import wave


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str
    probability: float = 1.0


@dataclass(frozen=True)
class Phrase:
    start: float
    end: float
    text: str
    confidence: float


@dataclass(frozen=True)
class Options:
    model: str = 'small'
    language: str | None = 'pl'
    min_seconds: float = 1.5
    max_seconds: float = 12.0
    pause_ms: int = 500
    margin_ms: int = 140
    beam_size: int = 5

    def checked(self) -> 'Options':
        if self.model not in ('base', 'small', 'medium', 'large-v3', 'parakeet-v3'):
            raise ValueError('Nieznany model STT.')
        if self.language not in ('pl', 'en', None):
            raise ValueError('Nieznany język transkrypcji.')
        if not (0.5 <= self.min_seconds <= 8.0 and
                self.min_seconds + 1 <= self.max_seconds <= 30 and
                100 <= self.pause_ms <= 1800 and
                0 <= self.margin_ms <= 350 and
                1 <= self.beam_size <= 8):
            raise ValueError('Nieprawidłowe ustawienia automatycznego cięcia.')
        return self


def join_word_text(words: list[Word]) -> str:
    text = ''.join(w.text if (w.text[:1].isspace() or w.text[:1] in ',.!?;:')
                   else (' ' + w.text) for w in words).strip()
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def group_words(words: Iterable[Word], opts: Options) -> list[Phrase]:
    """Prefer pauses and sentence boundaries; never cut in the middle of a word."""
    opts.checked()
    ordered = [w for w in words if w.text.strip() and math.isfinite(w.start)
               and math.isfinite(w.end) and 0 <= w.start < w.end]
    ordered.sort(key=lambda w: (w.start, w.end))
    if not ordered:
        return []
    groups: list[list[Word]] = []
    batch: list[Word] = []
    for current, word in enumerate(ordered):
        if batch and word.start - batch[-1].end >= max(0.85, opts.pause_ms / 1000 * 2):
            groups.append(batch)
            batch = []
        batch.append(word)
        if current == len(ordered) - 1:
            break
        following = ordered[current + 1]
        duration = max(0, word.end - batch[0].start)
        gap = max(0, following.start - word.end)
        natural_end = word.text.rstrip().endswith(('.', '?', '!', '…'))
        long_enough = duration >= opts.min_seconds
        hard_limit = following.end - batch[0].start >= opts.max_seconds
        if long_enough and ((gap >= opts.pause_ms / 1000)
                            or (natural_end and gap >= 0.12)
                            or hard_limit):
            groups.append(batch)
            batch = []
    if batch:
        groups.append(batch)
    # Small trailing fragments should join the previous phrase if that remains safe.
    compact: list[list[Word]] = []
    for grp in groups:
        duration = grp[-1].end - grp[0].start
        if (compact and duration < opts.min_seconds and
                grp[-1].end - compact[-1][0].start <= opts.max_seconds + 0.6 and
                grp[0].start - compact[-1][-1].end < 0.8):
            compact[-1].extend(grp)
        else:
            compact.append(grp)
    out: list[Phrase] = []
    for grp in compact:
        phrase = join_word_text(grp)
        if not phrase:
            continue
        confidence = sum(max(0.0, min(1.0, w.probability)) for w in grp) / len(grp)
        out.append(Phrase(grp[0].start, grp[-1].end, phrase, confidence))
    return out


def _which_ffmpeg() -> str:
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('FFmpeg nie jest dostępny w PATH. Zainstaluj FFmpeg i uruchom Studio ponownie.')
    return ffmpeg


def _run_ffmpeg(args: list[str], timeout: int = 240) -> None:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('FFmpeg: ' + (result.stderr or 'nieznany błąd')[-800:])


def _duration(path: Path) -> float:
    with wave.open(str(path), 'rb') as handle:
        return handle.getnframes() / max(1, handle.getframerate())


def _word_list(segments) -> list[Word]:
    words: list[Word] = []
    for seg in segments:
        if float(getattr(seg, 'no_speech_prob', 0.0) or 0) > 0.85:
            continue
        for w in (getattr(seg, 'words', None) or []):
            start, end = getattr(w, 'start', None), getattr(w, 'end', None)
            if start is None or end is None:
                continue
            words.append(Word(float(start), float(end), str(w.word),
                              float(getattr(w, 'probability', 0.5) or 0)))
    return words


def _parakeet_speech_ranges(pcm: Path, opts: Options) -> list[tuple[float,float]]:
    """Conservative energy-based cuts, instead of Whisper word timestamps.

    20 ms mono 16kHz windows, adaptive noise floor, and preferred pause cuts.
    Splits very long phrases at max_seconds. Drafts require user approval.
    """
    with wave.open(str(pcm), 'rb') as f:
        sr, channels, width = f.getframerate(), f.getnchannels(), f.getsampwidth()
        if sr != 16000 or channels != 1 or width != 2:
            raise ValueError('Parakeet Auto STT wymaga PCM16 mono 16 kHz.')
        samples = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').astype(np.float32)
    block = 320
    frames = samples[:len(samples)//block*block].reshape(-1,block)
    if len(frames) == 0:
        return []
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    floor = float(np.percentile(rms, 18))
    threshold = max(240.0, floor * 2.8)
    active = rms > threshold
    if not active.any():
        return []
    # Fill tiny gaps (<=120 ms) to avoid splitting inside consonants.
    indices = np.flatnonzero(active)
    for a,b in zip(indices[:-1],indices[1:]):
        if b-a <= 6:
            active[a:b+1] = True
    spans=[]
    starts = np.flatnonzero(active & ~np.r_[False,active[:-1]])
    stops  = np.flatnonzero(active & ~np.r_[active[1:],False])
    for a,b in zip(starts,stops):
        start,end=a*.02,(b+1)*.02
        if end-start >= .22:
            spans.append((start,end))
    if not spans:
        return []
    groups=[]
    left,right=spans[0]
    for start,end in spans[1:]:
        # Keep phrase segments within range and join close speech islands.
        if start-left >= opts.max_seconds or (start-right>=opts.pause_ms/1000 and right-left>=opts.min_seconds):
            groups.append((left,right));left,right=start,end
        else:
            right=end
    groups.append((left,right))
    bounded=[]
    for start,end in groups:
        if end-start < max(.35,opts.min_seconds/2):
            continue
        while end-start > opts.max_seconds:
            bounded.append((start,start+opts.max_seconds))
            start += opts.max_seconds
        if end-start>=.35:
            bounded.append((start,end))
    margin=opts.margin_ms/1000
    duration=len(samples)/sr
    return [(max(0.,a-margin),min(duration,b+margin)) for a,b in bounded]


def _auto_prepare_parakeet(sources, target_dir, opts, report, canceled):
    """Parakeet draft transcript per pause-bounded segment (no fake word alignment)."""
    from capri_parakeet_stt import decode_wav, installed
    if not installed():
        raise RuntimeError('Parakeet v3 nie jest zainstalowany. Uruchom Napraw Capri (menu Start).')
    ffmpeg=_which_ffmpeg()
    created=[]; output=[]
    target_dir.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='capri_parakeet_studio_') as scratch:
            work=Path(scratch)
            for i,source in enumerate(sources,1):
                if canceled():raise InterruptedError('Anulowano Auto STT Parakeet.')
                source=Path(source).expanduser().resolve()
                if not source.is_file() or source.suffix.lower() not in ('.wav','.mp3','.flac','.m4a','.ogg'):
                    raise ValueError('Niepoprawny plik audio: '+str(source))
                duration=audio_duration_seconds(source)
                for part in range(math.ceil(duration/AUTO_STT_WINDOW_SECONDS)):
                    if canceled(): raise InterruptedError('Anulowano Auto STT Parakeet.')
                    start=part*AUTO_STT_WINDOW_SECONDS
                    seconds=min(AUTO_STT_WINDOW_SECONDS,duration-start)
                    src_wav=work/f'src-{i}-{part}.wav'
                    _run_ffmpeg([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',f'{start:.3f}',
                                 '-i',str(source),'-t',f'{seconds:.3f}','-vn','-ac','1',
                                 '-ar','16000','-c:a','pcm_s16le',str(src_wav)])
                    ranges=_parakeet_speech_ranges(src_wav,opts)
                    report(f'[{i}/{len(sources)}] Parakeet część {part+1}: {len(ranges)} fragmentów')
                    for j,(begin,end) in enumerate(ranges,1):
                        if canceled():raise InterruptedError('Anulowano Auto STT Parakeet.')
                        tmp=work/f'clip-{i}-{part}-{j}.wav'
                        _run_ffmpeg([ffmpeg,'-hide_banner','-loglevel','error','-y',
                                     '-ss',f'{begin:.3f}','-i',str(src_wav),'-t',f'{end-begin:.3f}',
                                     '-vn','-ac','1','-ar','22050','-c:a','pcm_s16le',str(tmp)])
                        text=decode_wav(tmp.read_bytes()).strip()
                        if not text:
                            continue
                        target=target_dir/(uuid.uuid4().hex+'.wav')
                        created.append(target)
                        shutil.copy2(tmp,target)
                        output.append({'file':target.name,'text':text,'approved':False,
                                       'confidence':None,'source':source.name,'review':'DO SPRAWDZENIA'})
                    src_wav.unlink(missing_ok=True)
        return output
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def auto_prepare_dataset(sources: list[str | Path], target_dir: Path, options: Options,
                         *, model_dir: Path | None = None,
                         report: Callable[[str], None] | None = None,
                         canceled: Callable[[], bool] | None = None,
                         model_factory=None) -> list[dict]:
    """Return unapproved (file/text/confidence/source) records. Atomic per batch.

    No new clips become part of metadata.csv until explicitly approved in Studio.
    Existing recordings and project manifests remain untouched on failure.
    """
    opts = options.checked()
    if not sources:
        return []
    if len(sources) > 30:
        raise ValueError('Przetwarzaj najwyżej 30 plików naraz.')
    if options.model == 'parakeet-v3':
        return _auto_prepare_parakeet(sources, target_dir, opts,
                                       report or (lambda _: None),
                                       canceled or (lambda: False))
    ffmpeg = _which_ffmpeg()
    target_dir.mkdir(parents=True, exist_ok=True)
    report = report or (lambda _: None)
    canceled = canceled or (lambda: False)
    if model_factory is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError('Brak faster-whisper. Zainstaluj zależności Capri przez Napraw Capri (menu Start).') from exc
        model_factory = WhisperModel
    report('Ładowanie modelu Whisper ' + opts.model + ' (pierwszy raz może wymagać pobrania).')
    from capri_acceleration import load_whisper
    kwargs = {}
    if model_dir:
        kwargs['download_root'] = str(model_dir)
    model, actual_device = load_whisper(model_factory, opts.model, **kwargs)
    report('Auto STT: ' + ('CUDA / NVIDIA' if actual_device == 'cuda' else 'CPU (zgodnosc)'))
    created: list[Path] = []
    output: list[dict] = []
    try:
        with tempfile.TemporaryDirectory(prefix='capri_auto_stt_') as scratch:
            work = Path(scratch)
            for i, src in enumerate(sources, 1):
                if canceled():
                    raise InterruptedError('Anulowano STT; nie dodano niepełnych próbek.')
                source = Path(src).expanduser().resolve()
                if not source.is_file() or source.suffix.casefold() not in ('.wav', '.mp3', '.flac', '.m4a', '.ogg'):
                    raise ValueError('Nieprawidłowy plik audio: ' + str(source))
                # Work in bounded 10-minute windows, even for multi-hour inputs.
                # A 350 ms overlap prevents splitting spoken words at window edges.
                # Each Whisper result is converted back to the owning window,
                # so overlapping audio is never added twice to the dataset.
                total_duration = audio_duration_seconds(source)
                if total_duration < 0.8:
                    raise ValueError(f'{source.name}: nagranie jest zbyt krótkie (min. 0,8 s).')
                window_seconds = AUTO_STT_WINDOW_SECONDS
                overlap = 0.35
                total_windows = max(1, math.ceil(total_duration / window_seconds))
                report(f'[{i}/{len(sources)}] {source.name}: {total_duration:.1f} s, '
                       f'{total_windows} okien Auto STT (bez limitu 60 minut)')
                for window_index in range(total_windows):
                    if canceled():
                        raise InterruptedError('Anulowano STT; zachowano poprzedni dataset.')
                    core_start = window_index * window_seconds
                    core_end = min(total_duration, core_start + window_seconds)
                    audio_start = max(0.0, core_start - overlap)
                    audio_end = min(total_duration, core_end + overlap)
                    pcm = work / f'source_{i:02d}_part_{window_index:04d}.wav'
                    report(f'[{i}/{len(sources)}] Część {window_index+1}/{total_windows}: '
                           f'{core_start:.0f}–{core_end:.0f} s')
                    _run_ffmpeg([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                                 '-ss', f'{audio_start:.3f}', '-i', str(source),
                                 '-t', f'{audio_end - audio_start:.3f}',
                                 '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(pcm)])
                    duration = _duration(pcm)
                    try:
                        segments, _ = model.transcribe(str(pcm), language=opts.language,
                                                      beam_size=opts.beam_size, word_timestamps=True,
                                                      vad_filter=True,
                                                      vad_parameters={'min_silence_duration_ms': opts.pause_ms},
                                                      condition_on_previous_text=False)
                        segments = list(segments)
                    except Exception as exc:
                        if 'silero_vad' not in str(exc).casefold():
                            raise
                        segments, _ = model.transcribe(str(pcm), language=opts.language,
                                                      beam_size=opts.beam_size, word_timestamps=True,
                                                      vad_filter=False,
                                                      condition_on_previous_text=False)
                    words: list[Word] = []
                    for seg in segments:
                        if canceled():
                            raise InterruptedError('Anulowano automatyczną transkrypcję.')
                        for word in _word_list([seg]):
                            global_mid = audio_start + (word.start + word.end) / 2
                            if core_start <= global_mid < core_end:
                                words.append(word)
                    phrases = group_words(words, opts)
                    report(f'[{i}/{len(sources)}] Część {window_index+1}: '
                           f'{len(phrases)} fragmentów z transkrypcją')
                    for phrase in phrases:
                        if canceled():
                            raise InterruptedError('Anulowano automatyczne cięcie.')
                        margin = opts.margin_ms / 1000
                        start = max(0, phrase.start - margin)
                        end = min(duration, phrase.end + margin)
                        if end - start < 0.35 or end - start > 31:
                            report(f'Pominięto fragment o nieprawidłowej długości {end-start:.2f} s; '
                                   'sprawdź ustawienia zakresu STT.')
                            continue
                        target = target_dir / (uuid.uuid4().hex + '.wav')
                        created.append(target)  # rollback even if FFmpeg creates a partial file
                        _run_ffmpeg([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                                     '-ss', f'{start:.3f}', '-i', str(pcm), '-t', f'{end-start:.3f}',
                                     '-vn', '-ac', '1', '-ar', '22050', '-c:a', 'pcm_s16le', str(target)])
                        if _duration(target) < 0.35:
                            target.unlink(missing_ok=True)
                            created.remove(target)
                            continue
                        # Draft only: never add auto-transcribed text to training metadata.
                        output.append({'file': target.name, 'text': phrase.text,
                                       'approved': False, 'confidence': round(phrase.confidence, 3),
                                       'source': source.name, 'review': ('NISKA PEWNOŚĆ' if phrase.confidence < 0.72
                                                                         else 'DO SPRAWDZENIA')})
                    pcm.unlink(missing_ok=True)
                report(f'[{i}/{len(sources)}] Utworzono {len(output)} klipów (łącznie)')
        return output
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
