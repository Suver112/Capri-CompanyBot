"""Local optional XTTS-v2 synthesis and reference preparation.

The project can import user-provided audio samples. A user-provided default
voice recording may be bundled only with permission to redistribute it. All inference
runs on the user's machine; Coqui XTTS-v2 weights have a non-commercial license.
"""
from __future__ import annotations

from capri_paths import data_root

import os
import json
import hashlib
import wave
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import re
import sys
import importlib.util
import numpy as np

_MODEL = None
_DEVICE = None
_MODEL_LOCK = threading.RLock()
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
SUPPORTED_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".mp4", ".mov", ".mkv", ".flac", ".ogg", ".aac", ".webm", ".wma"})
MAX_IMPORT_FILES = 300
MAX_IMPORTED_SEGMENTS = 500
MAX_SOURCE_SECONDS = 1800  # prevent accidental multi-hour extractions
MIN_SEGMENT_SECONDS = 3.0
MAX_REFERENCE_FILES_PER_REPLY = 3  # 2 x main + 1 x supporting, or 3 automatic clips
MANIFEST_NAME = "capri_voice_corpus.json"
CLEANUP_MODES = ("off", "light", "vocals")
VOICE_ROLES = ("auto", "primary", "support")


def voices_dir() -> Path:
    return data_root() / "voices"


def ffmpeg_path() -> str:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(
            "Brak FFmpeg. Zainstaluj FFmpeg i dodaj go do PATH / "
            "FFmpeg unavailable; run the voice clone installer."
        ) from exc


def prepare_reference(source: str, *, start: float = 0, duration: float = 16) -> str:
    """Convert a user-selected, permission-cleared clip to clean mono 24 kHz WAV.

    The start/duration are explicit so episode dialogue can be trimmed to a
    speech-only part *without* redistributing the original audio.
    """
    src = Path(source)
    if not src.is_file():
        raise FileNotFoundError(f"Nie znaleziono nagrania / Missing audio file: {src}")
    if not (0 <= start <= 36000 and 3 <= duration <= 30):
        raise ValueError("Początek ≥ 0 s; długość próbki od 3 do 30 sekund.")
    output_dir = voices_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "capri_reference.wav"
    fd, tmp_path = tempfile.mkstemp(prefix="capri_ref_", suffix=".wav", dir=str(output_dir))
    os.close(fd)
    try:
        proc = subprocess.run(
            [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y",
             "-ss", str(start), "-i", str(src), "-t", str(duration),
             "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "24000",
             "-af", "highpass=f=80,lowpass=f=9000",
             "-c:a", "pcm_s16le", tmp_path],
            capture_output=True, text=True, timeout=90, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode != 0:
            raise RuntimeError("FFmpeg: " + proc.stderr.strip()[-650:])
        import wave
        with wave.open(tmp_path, "rb") as wav:
            audio_seconds = wav.getnframes() / max(wav.getframerate(), 1)
        if audio_seconds < 3:
            raise ValueError("Próbka jest za krótka; wybierz co najmniej 3 s czystej mowy.")
        os.replace(tmp_path, target)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return str(target)


def list_voice_files(folder: str) -> list[str]:
    """Find media recursively; ignore symlinks and limit pathological trees."""
    directory = Path(folder).expanduser()
    if not directory.is_dir():
        raise NotADirectoryError(f"Nie znaleziono folderu: {directory}")
    files = []
    for root, dirs, names in os.walk(directory, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink())
        for name in sorted(names):
            path = Path(root) / name
            if path.suffix.lower() in SUPPORTED_EXTENSIONS and path.is_file() and not path.is_symlink():
                files.append(str(path))
                if len(files) > MAX_IMPORT_FILES:
                    raise ValueError(f"W folderze jest ponad {MAX_IMPORT_FILES} plików. "
                                     "Podziel zbiór na mniejsze foldery.")
    if not files:
        raise ValueError("Nie znaleziono obsługiwanych nagrań w folderze.")
    return files


def _manifest_path() -> Path:
    return voices_dir() / MANIFEST_NAME


def is_managed_corpus_path(reference_path: str) -> bool:
    """Accept the two Capri-owned profile manifests, even across profile switches.

    Do not permit editing arbitrary JSON paths or legacy external media. Resolve
    symlinks before comparing, so a symlink cannot escape the app-owned corpus.
    """
    if not reference_path:
        return False
    appdata = Path(os.getenv("APPDATA") or Path.home())
    expected = {
        (appdata / profile / "voices" / MANIFEST_NAME).resolve()
        for profile in ("CapriOverlay", "CapriOverlay_Beta")
    }
    return Path(reference_path).resolve() in expected


def _read_manifest(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict) or data.get("format") != "capri-voice-corpus-v1":
        raise ValueError("Nieprawidłowy format biblioteki głosu.")
    return data


def _clip_stats(path: Path) -> tuple[float, float, float]:
    """Duration, RMS and sample clipping fraction; no heavyweight dependencies."""
    import numpy as np
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        duration = frames / max(1, wav.getframerate())
        # Scan a bounded number of frames to avoid large peak memory usage.
        raw = wav.readframes(min(frames, 24000 * 20))
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0 if raw else np.zeros(0, dtype=np.float32)
    rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    return duration, rms, peak


def _demucs_python() -> str:
    """Run optional Demucs in a separate environment, preserving XTTS dependencies."""
    root = Path(__file__).resolve().parent
    binary = root / ".venv_audio_clean" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if binary.is_file():
        return str(binary)
    if importlib.util.find_spec("demucs") is not None:
        return sys.executable
    raise RuntimeError(
        "Nie zainstalowano opcjonalnego silnika separacji muzyki (Demucs). "
        "albo wybierz LEKKIE ODSZUMIANIE."
    )


def _run_ffmpeg(source: str, output: str, *, start: float | None = None,
                duration: float | None = None, clean: bool = False, stereo: bool = False) -> None:
    command = [ffmpeg_path(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
    if start is not None:
        command.extend(["-ss", str(start)])
    command.extend(["-i", str(source)])
    if duration is not None:
        command.extend(["-t", str(duration)])
    command.extend(["-map", "0:a:0", "-vn", "-ac", "2" if stereo else "1",
                    "-ar", "44100" if stereo else "24000"])
    filters = ["highpass=f=80", "lowpass=f=9000"]
    if clean:
        # FFT attenuation helps with steady hiss, NOT competing voices or loud SFX.
        filters.append("afftdn=nr=8:nf=-45")
    if not stereo:
        command.extend(["-af", ",".join(filters)])
    command.extend(["-c:a", "pcm_s16le", output])
    proc = subprocess.run(command, capture_output=True, text=True, timeout=150, check=False,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if proc.returncode:
        raise RuntimeError("FFmpeg: " + (proc.stderr.strip()[-450:] or "nieznany błąd"))


def _extract_clean_voice(source: str, output: str, *, start: float, duration: float,
                         cleanup_mode: str) -> None:
    """Extract an optional cleaned voice reference to a caller-owned output path.

    Does not change the original media file or existing library entries. 'vocals'
    isolates vocal stem with Demucs; instruments/SFX can still leak or distort.
    """
    if cleanup_mode not in CLEANUP_MODES:
        raise ValueError("Nieznany tryb czyszczenia próbek.")
    if cleanup_mode != "vocals":
        return _run_ffmpeg(source, output, start=start, duration=duration,
                           clean=cleanup_mode == "light")
    python = _demucs_python()
    with tempfile.TemporaryDirectory(prefix="capri_demucs_") as temp:
        directory = Path(temp)
        source_wav = directory / "input.wav"
        _run_ffmpeg(source, str(source_wav), start=start, duration=duration, stereo=True)
        result_dir = directory / "separated"
        cmd = [python, "-m", "demucs", "-n", "htdemucs", "--two-stems", "vocals",
               "-d", "cpu", "--out", str(result_dir), str(source_wav)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=1800, check=False,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Demucs przekroczył limit czasu przetwarzania jednej próbki.") from exc
        if proc.returncode:
            raise RuntimeError("Demucs: " + (proc.stderr.strip()[-450:] or "nieznany błąd"))
        vocals = result_dir / "htdemucs" / "input" / "vocals.wav"
        if not vocals.is_file():
            raise RuntimeError("Demucs nie wygenerował ścieżki vocals.wav.")
        _run_ffmpeg(str(vocals), output, clean=True)


def _probe_source_seconds(source: str) -> float:
    """Find audio duration without decoding an entire video into memory."""
    executable = shutil.which("ffprobe")
    if not executable:
        ffmpeg = Path(ffmpeg_path())
        sibling = ffmpeg.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if sibling.is_file():
            executable = str(sibling)
    if executable:
        result = subprocess.run(
            [executable, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", source],
            capture_output=True, text=True, timeout=20, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode == 0:
            try:
                return float(result.stdout.strip())
            except ValueError:
                pass
    # FFmpeg ships inside imageio_ffmpeg on Windows but may lack ffprobe.
    result = subprocess.run([ffmpeg_path(), "-hide_banner", "-i", source],
                            capture_output=True, text=True, timeout=20, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if match:
        h, m, seconds = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(seconds)
    raise RuntimeError("Nie można ustalić długości nagrania (ffprobe/FFmpeg).")


def _segment_regions(wav_path: Path, *, target_seconds: float = 16.0) -> list[tuple[float, float]]:
    """Detect low-energy breaks and split speech into bounded, useful references.

    Uses a light-weight 20ms RMS envelope; does not infer linguistic boundaries
    when music/SFX prevent actual silence. Then it uses the least energetic
    available boundary, with a predictable fallback. Originals never change.
    """
    with wave.open(str(wav_path), "rb") as wav:
        rate = wav.getframerate()
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Do segmentacji wymagany jest WAV mono PCM16.")
        total_frames = wav.getnframes()
        hop = max(1, round(rate * .02))
        levels = []
        while True:
            block = wav.readframes(hop)
            if not block:
                break
            arr = np.frombuffer(block, dtype='<i2').astype(np.float32) / 32768.0
            levels.append(float(np.sqrt(np.mean(arr * arr))) if len(arr) else 0.)
    length = total_frames / rate
    if length < MIN_SEGMENT_SECONDS:
        return []
    if length <= target_seconds + 0.25:
        return [(0., length)]
    envelope = np.asarray(levels, dtype=np.float32)
    # A silence gap has lower energy than ordinary speech in the same file.
    # For a continuously loud music track, choose an energy minimum instead.
    low = float(np.percentile(envelope, 30)) if len(envelope) else 0.0
    threshold = max(.0028, min(.023, low * .65))
    max_seconds = min(30., max(target_seconds + 2., target_seconds * 1.2))
    min_seconds = 4.0
    segments = []
    cursor = 0.
    while length - cursor > max_seconds:
        ideal = cursor + target_seconds
        left = cursor + max(min_seconds, target_seconds - 4.)
        right = min(cursor + max_seconds, length - MIN_SEGMENT_SECONDS)
        if right < left:
            break
        # Prefer silence, but never put the cut earlier than the minimum length.
        lo_i = max(0, min(len(envelope)-1, int(left / .02)))
        hi_i = max(lo_i + 1, min(len(envelope), int(right / .02) + 1))
        options = np.arange(lo_i, hi_i)
        if options.size == 0:
            cut = min(ideal, right)
        else:
            # Smooth a 120ms interval around each candidate; reward real pauses.
            spread = 3
            padded = np.pad(envelope, (spread, spread), mode='edge')
            smooth = np.convolve(padded, np.ones(2*spread+1)/(2*spread+1), mode='valid')
            quiet = options[smooth[options] <= threshold]
            if len(quiet):
                chosen = int(quiet[np.argmin(np.abs(quiet * .02 - ideal))])
            else:
                # Avoid blindly splitting at an exact timestamp inside a syllable.
                scores = smooth[options] + .00045 * np.abs(options * .02 - ideal)
                chosen = int(options[np.argmin(scores)])
            cut = min(right, max(left, chosen * .02))
        if cut <= cursor + min_seconds - .01:
            cut = min(ideal, right)
        segments.append((cursor, cut))
        cursor = cut
        if len(segments) >= MAX_IMPORTED_SEGMENTS:
            raise ValueError(f"Nagranie przekracza limit {MAX_IMPORTED_SEGMENTS} fragmentów.")
    if length - cursor >= MIN_SEGMENT_SECONDS:
        segments.append((cursor, length))
    elif segments:
        prev_start, prev_end = segments[-1]
        if length - prev_start <= 30.:
            segments[-1] = (prev_start, length)
        else:
            # Short tail is attached to final segment up to the 30-second TTS cap.
            segments.append((cursor, length))
    return segments


def _extract_segment_wav(source_wav: Path, dest_wav: Path,
                         start_seconds: float, stop_seconds: float) -> None:
    """Copy aligned PCM frames; avoids lossy re-encoding between split clips."""
    with wave.open(str(source_wav), 'rb') as reader:
        rate = reader.getframerate()
        begin = max(0, int(round(start_seconds * rate)))
        count = max(0, int(round(stop_seconds * rate)) - begin)
        reader.setpos(min(begin, reader.getnframes()))
        payload = reader.readframes(count)
        with wave.open(str(dest_wav), 'wb') as writer:
            writer.setnchannels(reader.getnchannels())
            writer.setsampwidth(reader.getsampwidth())
            writer.setframerate(rate)
            writer.writeframes(payload)


def prepare_reference_set(sources: list[str], *, start: float = 0, duration: float = 16,
                          append: bool = True, progress=None, cleanup_mode: str = "off",
                          auto_split: bool = True, segment_progress=None) -> dict:
    """Import clips; optionally split long sources into pause-aware short WAVs.

    No weights are trained. Pre-existing libraries remain intact on failure.
    Missing/corrupt clips are reported. Original recordings are untouched.
    """
    if cleanup_mode not in CLEANUP_MODES:
        raise ValueError("Nieznany tryb czyszczenia.")
    if cleanup_mode == "vocals":
        _demucs_python()
    if not (0 <= start <= 36000 and 3 <= duration <= 30):
        raise ValueError("Początek ≥ 0 s; długość od 3 do 30 sekund.")
    if len(sources) > MAX_IMPORT_FILES:
        raise ValueError(f"Maksymalnie {MAX_IMPORT_FILES} nagrań na jeden import.")
    if not sources:
        raise ValueError("Wybierz co najmniej jeden plik.")
    dest = voices_dir()
    dest.mkdir(parents=True, exist_ok=True)
    manifest = _manifest_path()
    previous_entries = _read_manifest(str(manifest)).get("clips", []) if manifest.is_file() else []
    entries = previous_entries.copy() if append else []
    existing = {str(item['fingerprint']) for item in entries if 'fingerprint' in item}
    errors = []
    imported = reused = processed = 0
    split_sources = 0
    created_files = []
    for index, source in enumerate(sources, 1):
        try:
            path = Path(source)
            if not path.is_file() or path.is_symlink() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError("Nieobsługiwany format lub brak pliku")
            stat = path.stat()
            if stat.st_size > 2_000_000_000:
                raise ValueError("Plik większy niż 2 GB")
            source_id = hashlib.sha256(
                f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}::{start}::{duration}::"
                f"{cleanup_mode}::{auto_split}".encode('utf-8')
            ).hexdigest()[:24]
            if append and any(e.get('source_id') == source_id for e in entries):
                reused += sum(e.get('source_id') == source_id for e in entries)
                continue
            audio_duration = _probe_source_seconds(str(path))
            if not math.isfinite(audio_duration) or audio_duration <= start + MIN_SEGMENT_SECONDS:
                raise ValueError("Nagranie krótsze niż 3 sekundy po wskazanym początku")
            if audio_duration - start > MAX_SOURCE_SECONDS:
                raise ValueError("Nagranie ma ponad 30 minut; wybierz krótszy plik.")
            # When auto-cut is disabled, honour the manual time range.
            # Earlier builds imported full multi-minute WAVs which Fish cannot
            # reliably use as reference clips (max 30 s by design).
            segment_span = min(audio_duration - start,
                               MAX_SOURCE_SECONDS if auto_split else duration)
            with tempfile.TemporaryDirectory(prefix='capri_voice_source_') as tempdir:
                prepared = Path(tempdir) / 'prepared.wav'
                _extract_clean_voice(str(path), str(prepared), start=start,
                                     duration=segment_span, cleanup_mode=cleanup_mode)
                available, _, _ = _clip_stats(prepared)
                if available < MIN_SEGMENT_SECONDS:
                    raise ValueError("Mniej niż 3 sekundy nagrania po konwersji")
                intervals = (_segment_regions(prepared, target_seconds=duration)
                             if auto_split else [(0., available)])
                if len(intervals) > 1:
                    split_sources += 1
                if segment_progress:
                    segment_progress(0, len(intervals), path.name)
                if len(intervals) + len(entries) > MAX_IMPORTED_SEGMENTS:
                    raise ValueError(f"Import przekracza limit {MAX_IMPORTED_SEGMENTS} klipów; wybierz mniej plików.")
                for segment_index, (a, b) in enumerate(intervals, 1):
                    fingerprint = hashlib.sha256(
                        f"{source_id}:{segment_index}:{a:.3f}:{b:.3f}".encode('utf-8')
                    ).hexdigest()[:24]
                    if fingerprint in existing:
                        reused += 1
                        continue
                    target = dest / f"clip_{fingerprint}.wav"
                    fd, tmp = tempfile.mkstemp(suffix='.wav', prefix='capri_extract_', dir=str(dest))
                    os.close(fd)
                    try:
                        _extract_segment_wav(prepared, Path(tmp), a, b)
                        seconds, rms, peak = _clip_stats(Path(tmp))
                        if seconds < MIN_SEGMENT_SECONDS or rms < .002:
                            continue
                        os.replace(tmp, target)
                        created_files.append(target)
                    finally:
                        if os.path.isfile(tmp):
                            os.unlink(tmp)
                    entries.append({
                        'fingerprint': fingerprint, 'file': target.name,
                        'source_id': source_id, 'source_name': path.name,
                        'source_start': round(start + a, 3),
                        'source_end': round(start + b, 3),
                        'segment_index': segment_index,
                        'duration': round(seconds, 2), 'rms': round(rms, 5),
                        'peak': round(peak, 4), 'cleanup_mode': cleanup_mode,
                        'enabled': True, 'role': 'auto',
                    })
                    existing.add(fingerprint)
                    imported += 1
                    if segment_progress:
                        segment_progress(segment_index, len(intervals), path.name)
            processed += 1
        except Exception as exc:
            errors.append(f"{Path(source).name}: {str(exc)[:160]}")
        finally:
            if progress:
                progress(index, len(sources))
    valid = [e for e in entries if (dest / e.get('file', '')).is_file()]
    if not valid or (errors and not append):
        # A replacement must be all-or-nothing: do not discard the existing
        # corpus if even one of the selected sources fails.
        old_names = {str(e.get('file', '')) for e in previous_entries}
        for target in created_files:
            if target.is_file() and target.name not in old_names:
                target.unlink()
        reason = '; '.join(errors[:4]) or 'brak poprawnych klipów'
        raise RuntimeError('Nie ukończono importu. Stara biblioteka została zachowana. ' + reason)
    payload = {'format': 'capri-voice-corpus-v1', 'clips': valid}
    temporary_manifest = manifest.with_suffix('.tmp')
    temporary_manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary_manifest, manifest)
    if not append:
        _unlink_unused_derived(previous_entries, valid, dest)
    active = sum(e.get('enabled', True) for e in valid)
    return {
        'path': str(manifest), 'total': len(valid), 'active': active,
        'imported': imported, 'reused': reused, 'failed': len(errors),
        'split_sources': split_sources, 'processed_files': processed,
        'errors': errors[:7], 'used': len(set(resolve_references(str(manifest)))),
        'cleanup_mode': cleanup_mode,
    }

def _safe_managed_file(directory: Path, filename: str) -> Path | None:
    """Allow deletion ONLY of imported clip_<hash>.wav inside app-owned voices dir."""
    if not re.fullmatch(r"clip_[a-f0-9]{24}\.wav", filename or ""):
        return None
    target = directory / filename
    if target.is_symlink() or not target.is_file():
        return None
    if target.parent.resolve() != directory.resolve():
        return None
    return target


def _unlink_unused_derived(old_entries: list[dict], new_entries: list[dict], directory: Path):
    retained = {item.get("file") for item in new_entries}
    for entry in old_entries:
        filename = entry.get("file")
        if filename in retained:
            continue
        path = _safe_managed_file(directory, filename)
        if path is not None:
            try:
                path.unlink()
            except OSError:
                # A Windows AV / file lock may temporarily prevent deletion.
                # The manifest has already dropped the clip, so XTTS won't use it.
                pass


def list_reference_entries(reference_path: str) -> list[dict]:
    """Return display-safe information about every recorded clip and enabled state."""
    path = Path(reference_path) if reference_path else None
    if not path or not path.is_file():
        return []
    if path.suffix.lower() != ".json":
        return [{"fingerprint": "legacy", "file": path.name,
                 "source_name": path.name, "duration": 0,
                 "enabled": True, "exists": True}]
    items = _read_manifest(str(path)).get("clips", [])
    return [dict(e, enabled=bool(e.get("enabled", True)),
                 role=e.get("role", "auto") if e.get("role", "auto") in VOICE_ROLES else "auto",
                 exists=(path.parent / e.get("file", "")).is_file())
            for e in items if isinstance(e, dict)]


def manage_reference_entries(reference_path: str, *, ids: list[str],
                             action: str) -> dict:
    """Set active state or remove selected imported clips, atomically.

    Never touches the user's original source videos/audio. For safety, this
    function may only modify the app-owned corpus path, not arbitrary JSON.
    """
    if action not in ("enable", "disable", "delete", "primary", "support", "auto"):
        raise ValueError("Nieznana akcja zarządzania głosem.")
    path = Path(reference_path)
    if not is_managed_corpus_path(str(path)):
        raise ValueError("Zarządzanie jest dostępne tylko dla biblioteki Capri.")
    if not path.is_file():
        raise FileNotFoundError("Nie znaleziono biblioteki głosu.")
    entries = _read_manifest(str(path)).get("clips", [])
    if action == "primary" and len(set(ids)) != 1:
        raise ValueError("Jako bazę możesz ustawić tylko jedną próbkę.")
    selections = set(ids)
    old_entries = entries.copy()
    found = set()
    updated = []
    for e in entries:
        fingerprint = str(e.get("fingerprint", ""))
        if fingerprint in selections:
            found.add(fingerprint)
            if action == "delete":
                continue
            if action in ("enable", "disable"):
                e = {**e, "enabled": (action == "enable")}
            elif action in VOICE_ROLES:
                e = {**e, "role": action, "enabled": True}
        elif action == "primary" and e.get("role") == "primary":
            # One base at any time; the old base becomes auto, not support.
            e = {**e, "role": "auto"}
        updated.append(e)
    if not found:
        raise ValueError("Nie wybrano żadnej istniejącej próbki.")
    # Keep the corpus metadata even if it has no active clips. Other features
    # can detect this and allow immediate import of a replacement.
    content = {"format": "capri-voice-corpus-v1", "clips": updated}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    if action == "delete":
        _unlink_unused_derived(old_entries, updated, path.parent)
    active = sum(bool(e.get("enabled", True)) for e in updated
                 if (path.parent / e.get("file", "")).is_file())
    return {"path": str(path), "total": len(updated), "active": active,
            "used": len(set(resolve_references(str(path)))),
            "changed": len(found)}


def reference_info(reference_path: str) -> dict:
    path = Path(reference_path) if reference_path else None
    if not path or not path.is_file():
        return {"total": 0, "active": 0, "used": 0}
    if path.suffix.lower() != ".json":
        return {"total": 1, "active": 1, "used": 1}
    try:
        clips = _read_manifest(str(path))["clips"]
        valid = [c for c in clips if (path.parent / c["file"]).is_file()]
        active = sum(c.get("enabled", True) for c in valid)
        base = sum(c.get("role") == "primary" and c.get("enabled", True) for c in valid)
        supports = sum(c.get("role") == "support" and c.get("enabled", True) for c in valid)
        return {"total": len(valid), "active": active,
                "used": len(set(resolve_references(str(path)))),
                "primary": bool(base), "supports": supports}
    except (OSError, ValueError, KeyError, TypeError):
        return {"total": 0, "active": 0, "used": 0}


def resolve_references(reference_path: str) -> list[str]:
    """Return ordered speaker references, optionally weighting the user-picked base.

    In XTTS-v2 the speaker embeddings for supplied files are averaged. If a
    primary clip exists, it is repeated twice, then followed by ONE supporting
    clip. This produces ~2:1 weight for the voice embedding (not a promised
    acoustic similarity ratio). GPT style conditioning typically uses the
    first part of the concatenated reference audio, so keeping the base first
    also makes its delivery more influential.

    Old libraries without roles keep the previous automatic 1-3 clip behavior.
    Merely marking a base does not automatically blend other 'auto' clips;
    the user must explicitly mark a supporting clip to prevent stale samples.
    """
    path = Path(reference_path)
    if path.suffix.lower() != ".json":
        return [str(path)] if path.is_file() else []
    data = _read_manifest(str(path))
    def usable_duration(entry):
        # Old libraries may not record duration; don't break those references.
        # New imports always store their exact duration.
        try:
            seconds = float(entry.get("duration", 0) or 0)
        except (TypeError, ValueError):
            return True
        return seconds == 0 or 3 <= seconds <= 30

    clips = [c for c in data["clips"] if c.get("enabled", True)
             and (path.parent / c["file"]).is_file()
             and usable_duration(c)]
    def rank(c):
        rms = c.get("rms", 0.04)
        length = c.get("duration", 8)
        peak = c.get("peak", 0.7)
        # Coarse technical ranking, NOT detection of unwanted music or voices.
        return (abs(rms - .07) * 3 + abs(length - 10) * .01
                + max(0., peak-.9)*2, c.get("file", ""))
    base = sorted((c for c in clips if c.get("role", "auto") == "primary"), key=rank)
    if base:
        base_path = str(path.parent / base[0]["file"])
        supports = sorted((c for c in clips if c.get("role", "auto") == "support"), key=rank)
        supports = [c for c in supports if c["file"] != base[0]["file"]]
        if not supports:
            return [base_path]
        support_path = str(path.parent / supports[0]["file"])
        return [base_path, base_path, support_path]
    good = [c for c in clips if 0.008 <= c.get("rms", 0) <= 0.25
            and c.get("peak", 0) < 0.99 and 4 <= c.get("duration", 0) <= 26]
    # If supports were marked but the base was disabled, do not silently
    # blend unrelated automatic clips.
    explicit = [c for c in clips if c.get("role") == "support"]
    candidates = explicit if explicit else (good or clips)
    return [str(path.parent / c["file"]) for c in sorted(candidates, key=rank)[:MAX_REFERENCE_FILES_PER_REPLY]]


def clean_speech_text(text: str) -> str:
    """Remove markup/emoji tags before TTS, retain Polish diacritics and prosody."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[[^\]\n]{1,50}\]", "", text)
    text = re.sub(r"(?m)^\s*[-*]\s+", "", text)
    text = re.sub(r"(?i)\b(?:haha){3,}\b", "ha, ha, ha", text)
    text = re.sub(r"([!?.,])\1{2,}", r"\1\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_tts_text(text: str, max_len: int = 170) -> list[str]:
    """Bound one XTTS generation to a short chunk without splitting short words."""
    text = clean_speech_text(text)
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?;])\s+", text)
    pieces = []
    for sentence in sentences:
        while len(sentence) > max_len:
            boundary = max(sentence.rfind(", ", 40, max_len),
                           sentence.rfind(" ", 40, max_len))
            if boundary < 30:
                boundary = max_len
            segment = sentence[:boundary].strip()
            if segment:
                pieces.append(segment)
            sentence = sentence[boundary:].lstrip(' ,')
        if sentence.strip():
            if pieces and len(pieces[-1]) + len(sentence) + 1 < max_len * .70:
                pieces[-1] += ' ' + sentence.strip()
            else:
                pieces.append(sentence.strip())
    return pieces  # Never silently drop the end of a long reply.


def _silence_compact(samples: np.ndarray, sample_rate: int = 24000) -> np.ndarray:
    """Shorten only implausibly long silent gaps, keep ordinary pauses intact."""
    if len(samples) < sample_rate // 2:
        return samples
    abs_max = float(np.max(np.abs(samples)))
    threshold = max(0.0007, min(0.006, abs_max * 0.012))
    win = max(1, sample_rate // 100)  # 10ms frames
    limit = (len(samples)//win) * win
    levels = np.max(np.abs(samples[:limit].reshape(-1,win)),axis=1)
    quiet = levels < threshold
    # Reduce only runs of silence longer than 0.75s to a natural 0.28s.
    runs=[];left=None
    for idx,v in enumerate(quiet):
        if v and left is None: left=idx
        if not v and left is not None:
            if idx-left > 75: runs.append((left*win,idx*win))
            left=None
    if left is not None and len(quiet)-left > 75:
        runs.append((left*win,len(quiet)*win))
    if not runs: return samples
    sections=[];pos=0
    keep=int(.28*sample_rate)
    for a,b in runs:
        sections.extend([samples[pos:a],samples[a:a+keep]])
        pos=b
    sections.append(samples[pos:])
    return np.concatenate(sections)


def _assemble_segments(files: list[str], out_path: str):
    """Join WAV chunks with 65 ms pause and short fades; gently limit peaks."""
    chunks=[]
    for path in files:
        with wave.open(path, "rb") as fh:
            if fh.getframerate()!=24000 or fh.getnchannels()!=1 or fh.getsampwidth()!=2:
                raise RuntimeError("Unexpected XTTS WAV format (expected PCM 24kHz mono)")
            raw=fh.readframes(fh.getnframes())
        data=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
        # Never trim or fade away quiet consonants at chunk boundaries.
        chunks.append(data)
    if not chunks:
        raise RuntimeError("No TTS WAV chunks produced")
    pause=np.zeros(round(.065*24000),dtype=np.float32)
    audio=np.concatenate([part for i, chunk in enumerate(chunks)
                          for part in ((pause,chunk) if i else (chunk,))] +
                         [np.zeros(round(.18*24000),dtype=np.float32)])
    if not np.all(np.isfinite(audio)):
        raise RuntimeError("XTTS produced invalid audio samples")
    # Gentle normalization only. No aggressive noise gate or pitch shift.
    peak=float(np.max(np.abs(audio))) if len(audio) else 0
    if .005 < peak < .8:
        audio*=min(1.8,.85/peak)
    pcm=(np.clip(audio,-.95,.95)*32767).astype('<i2')
    with wave.open(out_path,'wb') as fh:
        fh.setnchannels(1);fh.setsampwidth(2);fh.setframerate(24000)
        fh.writeframes(pcm.tobytes())


def detect_delivery(text: str) -> str:
    """Text emotion is only a hint; not a model-controlled emotion guarantee."""
    low=text.lower()
    if any(w in low for w in ('szep', 'cicho ', 'whisper')):
        return 'soft'
    if ('!' in text or '?!' in text or any(w in low for w in ('serio?!','no nie','haha','świetnie!'))):
        return 'excited'
    if any(w in low for w in ('przykro', 'spokojnie', 'dobranoc', 'sorry')):
        return 'soft'
    return 'neutral'


def render_settings(profile='clear', delivery='neutral') -> dict:
    # XTTS supports these knobs, but emotion imitation remains approximate.
    clear = {'temperature': .58, 'repetition_penalty': 6.0,
             'top_k': 36, 'top_p': .76, 'speed': 1.0}
    if profile != 'expressive':
        return clear
    values = dict(clear)
    if delivery == 'excited':
        values.update(temperature=.69, speed=1.045, top_p=.82)
    elif delivery == 'soft':
        values.update(temperature=.60, speed=.965)
    else:
        values.update(temperature=.63, speed=1.0)
    return values


def _load_model(progress=None):
    global _MODEL, _DEVICE
    if _MODEL is not None:
        return _MODEL
    if not (voices_dir().parent / "xtts_license_accepted.txt").is_file():
        raise RuntimeError(
            "XTTS-v2 requires non-commercial CPML license acceptance. "
            "XTTS is not included in the base Capri package; install the optional TTS dependencies first."
        )
    os.environ["COQUI_TOS_AGREED"] = "1"
    try:
        import torch
        from TTS.api import TTS
    except Exception as exc:
        raise RuntimeError(
            "Silnik XTTS nie jest zainstalowany (opcjonalny, spoza instalatora podstawowego). "
            "(XTTS is not installed.)"
        ) from exc

    # Some Windows AMD/ROCm installations expose HIP through torch.cuda.
    # Never assume GPU support merely because the user's machine has a Radeon.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if progress:
        progress("xtts_load")
    try:
        model = TTS(MODEL_NAME).to(device)
    except Exception:
        if device != "cuda":
            raise
        # Device fallback if torch advertises a GPU but its drivers are unusable.
        model = TTS(MODEL_NAME).to("cpu")
        device = "cpu"
    _DEVICE = device
    _MODEL = model
    return model


def synthesize_voice(text: str, lang: str, reference_path: str, progress=None,
                     profile: str = "clear") -> str:
    """Stable XTTS with curated references, chunked phrases and gentle postprocessing."""
    reference=Path(reference_path)
    if not reference.is_file():
        raise FileNotFoundError("Brak próbki. Ustawienia → Import głosu.")
    if lang not in ("pl", "en"):
        raise ValueError("Choose Polish or English.")
    refs=resolve_references(str(reference))
    if not refs:
        raise ValueError("Biblioteka głosu jest pusta.")
    chunks=split_tts_text(text)
    if not chunks:
        raise ValueError("Brak tekstu do syntezy")
    delivery=detect_delivery(text)
    settings=render_settings(profile,delivery)
    fd,output=tempfile.mkstemp(prefix='capri_xtts_',suffix='.wav')
    os.close(fd)
    try:
        with _MODEL_LOCK:
            model=_load_model(progress)
            with tempfile.TemporaryDirectory(prefix='capri_xtts_chunks_') as directory:
                paths=[]
                for index,segment in enumerate(chunks,1):
                    if progress:
                        progress(f"tts_chunk:{index}/{len(chunks)}")
                    path=str(Path(directory)/f'segment_{index:02d}.wav')
                    # With short chunks, Coqui's extra sentence splitting is unnecessary.
                    model.tts_to_file(text=segment, speaker_wav=refs,
                        language=lang,file_path=path,split_sentences=False,**settings)
                    paths.append(path)
                if progress: progress('tts_post')
                _assemble_segments(paths,output)
        if Path(output).stat().st_size < 44:
            raise RuntimeError("XTTS did not generate a valid WAV")
        return output
    except Exception:
        try: os.unlink(output)
        except OSError: pass
        raise


def engine_device() -> str:
    return _DEVICE or "not loaded"
