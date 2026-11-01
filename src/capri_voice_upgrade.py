"""Optional, one-time, offline expansion of the bundled Capri voice corpus.

The user supplied a 179-second recording; previous releases exposed only two
short seed clips. This step packages pause-aware excerpts and transcribes them
locally *after* Whisper is installed. It NEVER invents reference transcripts,
never overwrites a custom corpus and never silently overwrites manual edits.

S2.cpp consumes a single selected WAV+matching transcript, not every sample in
its library. More clips improve the choice of reference, NOT automatically the
model's pronunciation. A non-Polish source does not become Polish by cutting it.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import wave

from capri_paths import data_root, local_root
from capri_default_voice import ASSETS, install_default_voice
from voice_clone import MANIFEST_NAME, _read_manifest, voices_dir

BUNDLE = tuple(f'capri_full_{i:02d}.wav' for i in range(1, 16))
DEFAULT_IDS = {'capri-default-1', 'capri-default-2'}
FULL_PREFIX = 'capri-full-'


def _safe_save(path: Path, obj: dict) -> None:
    fd, name = tempfile.mkstemp(prefix='.capri-voice-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(obj, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _validate_wav(path: Path) -> tuple[float, float, float]:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(str(path))
    from array import array
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
            raise ValueError(f'Nieobsługiwany format wbudowanej próbki: {path.name}')
        duration = wav.getnframes() / 24000.0
        data = wav.readframes(wav.getnframes())
    if not 3 <= duration <= 15 or len(data) < 10000:
        raise ValueError(f'Nieprawidłowa długość próbki: {path.name}')
    samples = array('h')
    samples.frombytes(data)
    if os.sys.byteorder != 'little':
        samples.byteswap()
    rms = (sum(float(x)*x for x in samples) / len(samples)) ** .5 / 32768
    peak = max(abs(x) for x in samples) / 32768
    return duration, rms, peak


def _recognized_reference(model, path: Path) -> tuple[str, float]:
    """Use actual speech content only. Reject non-PL or unreliable ASR results."""
    segments, info = model.transcribe(str(path), language=None,
                                      beam_size=3, vad_filter=True,
                                      condition_on_previous_text=False)
    segments = list(segments)
    language = str(getattr(info, 'language', '') or '')
    confidence = float(getattr(info, 'language_probability', 0) or 0)
    valid = [s for s in segments if (float(getattr(s, 'no_speech_prob', 0) or 0) < .65
                                    and float(getattr(s, 'avg_logprob', -9) or -9) > -1.2
                                    and float(getattr(s, 'compression_ratio', 0) or 0) < 2.5)]
    transcript = re.sub(r'\s+', ' ', ' '.join(str(s.text).strip() for s in valid)).strip()
    if (language != 'pl' or confidence < .58 or len(transcript) < 15
            or len(transcript.split()) < 3):
        return '', confidence
    return transcript[:2500], confidence


def _eligible_to_upgrade(clips: list[dict]) -> bool:
    """No added user clips; no overwrite of unrelated voice libraries."""
    folder = voices_dir()
    return bool(clips) and all(
        str(c.get('source_id', '')) in DEFAULT_IDS
        or str(c.get('source_id', '')).startswith(FULL_PREFIX)
        or (not c.get('enabled', True) and not (folder / str(c.get('file', ''))).is_file())
        for c in clips
    )


def expand_default_voice(*, transcribe=None, progress=None) -> dict:
    """Idempotent; cached per-clip ASR avoids repeating costly work on repair.

    If ASR cannot verify a Polish sample, it stays disabled; the old selected
    primary remains as-is. In particular, an English file does NOT get an
    invented Polish transcript.
    """
    initial = install_default_voice()
    manifest = Path(initial['path'])
    data = _read_manifest(str(manifest))
    entries = list(data['clips'])
    if not _eligible_to_upgrade(entries):
        return {'status': 'custom-preserved', 'total': len(entries), 'imported': 0}

    existing = {str(x.get('source_id', '')) for x in entries}
    # Transcribe only when any of our bundled clips is not already validated.
    pending = [name for idx, name in enumerate(BUNDLE, 1)
               if FULL_PREFIX + f'{idx:02d}' not in existing]
    if not pending:
        selected = next((x for x in entries if x.get('role') == 'primary' and
                         str(x.get('source_id', '')).startswith(FULL_PREFIX)), None)
        if not selected and not any(x.get('role') == 'primary' and
                      x.get('transcript_model') not in ('bundled-user-script', 'whisper-small-auto-verified')
                      for x in entries):
            candidates = [x for x in entries if str(x.get('source_id', '')).startswith(FULL_PREFIX)
                          and x.get('enabled') and x.get('transcript')]
            if candidates:
                selected = max(candidates, key=lambda x: float(x.get('language_probability', 0)))
                for x in entries:
                    if x.get('role') == 'primary':
                        x['role'] = 'auto'
                selected['role'] = 'primary'
                _safe_save(manifest, {'format': 'capri-voice-corpus-v1', 'clips': entries})
        if selected:
            _sync_settings(manifest, selected)
        return {'status': 'already-ready', 'total': len(entries), 'imported': 0}

    if transcribe is None:
        from faster_whisper import WhisperModel
        model_dir = data_root() / 'models'
        model_dir.mkdir(parents=True, exist_ok=True)
        # Reuse the Whisper small weights verified in installer selftest.
        model = WhisperModel('small', device='cpu', compute_type='int8',
                             download_root=str(model_dir), local_files_only=True)
        transcribe = lambda p: _recognized_reference(model, p)

    folder = voices_dir()
    written = []
    added = 0
    verified = 0
    try:
        for idx, filename in enumerate(BUNDLE, 1):
            identifier = FULL_PREFIX + f'{idx:02d}'
            if identifier in existing:
                continue
            source = ASSETS / filename
            duration, rms, peak = _validate_wav(source)
            fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()[:24]
            target = folder / ('clip_' + fingerprint + '.wav')
            if progress:
                progress(idx, len(BUNDLE), 'Sprawdzam mowę ' + str(idx) + '/' + str(len(BUNDLE)))
            transcript, confidence = transcribe(source)
            transcript = re.sub(r'\s+', ' ', str(transcript or '')).strip()[:2500]
            usable = bool(transcript and rms >= .002 and peak < .995)
            if not target.is_file():
                fd, temporary = tempfile.mkstemp(prefix='.capri-clip-', suffix='.wav', dir=folder)
                try:
                    with os.fdopen(fd, 'wb') as file:
                        file.write(source.read_bytes())
                        file.flush()
                        os.fsync(file.fileno())
                    os.replace(temporary, target)
                    written.append(target)
                finally:
                    Path(temporary).unlink(missing_ok=True)
            record = {'fingerprint': fingerprint, 'file': target.name,
                      'source_id': identifier, 'source_name': 'capri-glos.mp3',
                      'duration': round(duration, 3), 'rms': round(rms, 5),
                      'peak': round(peak, 4), 'enabled': usable,
                      'role': 'auto', 'transcript_lang': 'pl' if usable else '',
                      'transcript': transcript if usable else '',
                      'transcript_model': 'whisper-small-auto-verified' if usable else '',
                      'transcripts': {'pl': {'text': transcript, 'model': 'whisper-small-auto-verified'}} if usable else {},
                      'language_probability': round(float(confidence), 3)}
            entries.append(record)
            # Save after each clip, so cancel/power loss doesn't redo prior ASR.
            _safe_save(manifest, {'format': 'capri-voice-corpus-v1', 'clips': entries})
            added += 1
            verified += int(usable)
        # Select the best *verified Polish* clip. Respect a user manually
        # assigned primary or manually edited transcript.
        manual_choice = any(x.get('role') == 'primary' and
                            x.get('transcript_model') not in ('bundled-user-script', 'whisper-small-auto-verified')
                            for x in entries)
        viable = [x for x in entries if x.get('source_id', '').startswith(FULL_PREFIX)
                  and x.get('enabled') and x.get('transcript')]
        selected = None
        if viable and not manual_choice:
            viable.sort(key=lambda x: (float(x.get('language_probability', 0)),
                                       1 - abs(float(x.get('rms', 0)) - .07),
                                       len(x.get('transcript', ''))), reverse=True)
            selected = viable[0]
            for x in entries:
                if x.get('role') == 'primary':
                    x['role'] = 'auto'
            selected['role'] = 'primary'
            _safe_save(manifest, {'format': 'capri-voice-corpus-v1', 'clips': entries})
            _sync_settings(manifest, selected)
        return {'status': 'ready', 'total': len(entries), 'imported': added,
                'verified_polish': verified, 'primary': selected['source_id'] if selected else 'unchanged'}
    except BaseException:
        # Saved entries are valid; don't delete copied WAVs referenced in the manifest.
        raise


def _sync_settings(manifest: Path, choice: dict) -> None:
    config = data_root() / 'settings.json'
    if not config.is_file():
        return
    try:
        settings = json.loads(config.read_text(encoding='utf-8'))
        if not isinstance(settings, dict):
            return
        old_ref = str(settings.get('voice_ref_path', '') or '')
        # Never change a user-selected external voice file/library.
        if old_ref and Path(old_ref).resolve() != manifest.resolve():
            return
        settings['voice_ref_path'] = str(manifest)
        settings['fish_ref_path'] = str(manifest.parent / choice['file'])
        settings['fish_ref_transcript'] = str(choice['transcript'])
        _safe_save(config, settings)
    except (OSError, ValueError, TypeError):
        return


def main() -> int:
    log = local_root() / 'capri_voice_upgrade.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    def progress(i, n, msg):
        with log.open('a', encoding='utf-8') as file:
            file.write(f'{i}/{n}: {msg}\n')
    try:
        result = expand_default_voice(progress=progress)
        with log.open('a', encoding='utf-8') as file:
            file.write(json.dumps(result, ensure_ascii=False) + '\n')
        return 0
    except Exception as error:
        with log.open('a', encoding='utf-8') as file:
            file.write('ERROR: ' + repr(error) + '\n')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
