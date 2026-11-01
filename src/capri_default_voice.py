"""Built-in Capri voice starter kit (no remote ASR or FFmpeg on first run).

The audio is distributed with the user's explicit installation request. Two
short, preprocessed reference WAVs are bundled, with their transcript from the
user-supplied script. They are NOT transcripts verified by a speech recognizer.
An automatic Whisper recheck remains available in the Voice tab.

Install is atomic/idempotent, never replaces a user's own library/selection.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid
import wave

from capri_paths import data_root
from voice_clone import MANIFEST_NAME, _read_manifest, voices_dir

ASSETS = Path(__file__).resolve().parent / 'assets' / 'default_voice'
SEEDS = (
    ('capri_seed_01.wav', 'O, no proszę, proszę, kogo my tu mamy?', 'primary'),
    ('capri_seed_02.wav', 'Tak się na mnie patrzysz, jakbyś pierwszy raz w życiu zobaczył gadający kawałek kodu.', 'support'),
)


def _audio_info(path: Path) -> tuple[float, float, float]:
    with wave.open(str(path), 'rb') as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 24000:
            raise ValueError('Domyślna próbka musi być mono PCM16/24 kHz')
        duration = wav.getnframes() / wav.getframerate()
        payload = wav.readframes(wav.getnframes())
    if not 3.0 <= duration <= 15.0:
        raise ValueError('Domyślna próbka ma nieprawidłową długość')
    if len(payload) < 10000:
        raise ValueError('Domyślna próbka jest pusta')
    from array import array
    samples = array('h')
    samples.frombytes(payload)
    if os.sys.byteorder != 'little':
        samples.byteswap()
    rms = (sum(float(x) * x for x in samples) / len(samples)) ** .5 / 32768
    peak = max(abs(x) for x in samples) / 32768
    if rms < .002:
        raise ValueError('Domyślna próbka jest za cicha')
    return duration, rms, peak


def _ready_clip(entry: dict, folder: Path) -> bool:
    """Check actual playback reference, not merely a JSON entry."""
    if not isinstance(entry, dict) or not entry.get('enabled', True):
        return False
    filename = str(entry.get('file', ''))
    if not filename.startswith('clip_') or not filename.endswith('.wav') or '/' in filename or "\\" in filename:
        return False
    target = folder / filename
    try:
        if not target.is_file() or target.is_symlink():
            return False
        with wave.open(str(target), 'rb') as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
                return False
            if not 3 <= wav.getnframes() / 24000 <= 30:
                return False
        return bool((entry.get('transcript_lang') == 'pl' and str(entry.get('transcript', '')).strip()) or
                    str(entry.get('transcripts', {}).get('pl', {}).get('text', '')).strip())
    except (OSError, EOFError, ValueError, TypeError, AttributeError, wave.Error):
        return False


def _write_manifest(path: Path, entries: list[dict]) -> None:
    payload = {'format': 'capri-voice-corpus-v1', 'clips': entries}
    fd, temporary = tempfile.mkstemp(prefix='.capri-voice-restore-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _repair_bundled_file(source: Path, target: Path, fingerprint: str) -> bool:
    if target.is_file() and not target.is_symlink():
        try:
            if hashlib.sha256(target.read_bytes()).hexdigest()[:24] == fingerprint:
                _audio_info(target)
                return False
        except (OSError, ValueError, wave.Error):
            pass
    fd, temporary = tempfile.mkstemp(prefix='.capri-voice-wav-', suffix='.wav', dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temporary)
        if hashlib.sha256(Path(temporary).read_bytes()).hexdigest()[:24] != fingerprint:
            raise IOError('Kopia próbki jest nieprawidłowa: ' + source.name)
        _audio_info(Path(temporary))
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return True


def install_default_voice() -> dict:
    """Repair broken bundled references without deleting user-provided recordings.

    An existing manifest is NOT sufficient proof that Fish has usable audio.
    A malformed manifest is backed up; user entries in a valid manifest survive.
    """
    library = voices_dir()
    library.mkdir(parents=True, exist_ok=True)
    manifest = library / MANIFEST_NAME
    records = []
    for index, (filename, transcript, role) in enumerate(SEEDS, 1):
        source = ASSETS / filename
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError('Brak próbki w paczce Capri: ' + filename)
        duration, rms, peak = _audio_info(source)
        fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()[:24]
        records.append((source, {'fingerprint': fingerprint,
                         'file': 'clip_' + fingerprint + '.wav',
                         'source_id': 'capri-default-' + str(index),
                         'source_name': 'Capri • głos domyślny ' + str(index),
                         'source_start': 0, 'source_end': duration,
                         'duration': round(duration, 3),
                         'rms': round(rms, 5), 'peak': round(peak, 4),
                         'enabled': True, 'role': role,
                         'transcript': transcript, 'transcript_lang': 'pl',
                         'transcript_model': 'bundled-user-script',
                         'transcripts': {'pl': {'text': transcript, 'model': 'bundled-user-script'}}}))

    entries = []
    broken_manifest = False
    if manifest.is_file():
        try:
            original = _read_manifest(str(manifest))
            if not isinstance(original.get('clips'), list) or not all(isinstance(e, dict) for e in original['clips']):
                raise ValueError('Nieprawidłowa lista nagrań')
            entries = original['clips']
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            # Do not destroy old voice metadata: backup so it can be recovered.
            backup = library / ('capri_voice_damaged_' + uuid.uuid4().hex[:12] + '.json.bak')
            shutil.copy2(manifest, backup)
            broken_manifest = True

    known = {str(e.get('source_id')): e for e in entries}
    any_ready = any(_ready_clip(e, library) for e in entries)
    has_old_default = any(str(e.get('source_id', '')).startswith('capri-default-') for e in entries)
    changed = not manifest.is_file() or broken_manifest
    restored_files = 0
    if has_old_default or not any_ready:
        for source, expected in records:
            previous = known.get(expected['source_id'])
            # Do not re-enable samples the user intentionally disabled.
            if previous is not None:
                replacement = dict(expected)
                replacement['enabled'] = bool(previous.get('enabled', True))
                user_text = str(previous.get('transcript', '') or '').strip()
                if previous.get('transcript_model') == 'manual' and user_text:
                    replacement['transcript'] = user_text
                    replacement['transcript_model'] = 'manual'
                    replacement['transcripts'] = {'pl': {'text': user_text, 'model': 'manual'}}
                if previous.get('role') in ('primary', 'support', 'auto'):
                    replacement['role'] = previous['role']
                # Repair WAV even when manifest points at an obsolete filename.
                idx = entries.index(previous)
                if entries[idx] != replacement:
                    entries[idx] = replacement
                    changed = True
            else:
                replacement = dict(expected)
                entries.append(replacement)
                changed = True
            restored_files += int(_repair_bundled_file(source, library / expected['file'], expected['fingerprint']))

    # Disable an invalid primary without deleting its metadata or its audio.
    # Otherwise resolve_references() might pick its corrupted WAV ahead of a seed.
    for entry in entries:
        if entry.get('role') == 'primary' and not _ready_clip(entry, library):
            entry['role'] = 'auto'
            entry['enabled'] = False
            changed = True
    primaries = [e for e in entries if e.get('role') == 'primary' and _ready_clip(e, library)]
    if not primaries:
        seeds = [e for e in entries if str(e.get('source_id', '')).startswith('capri-default-')
                 and _ready_clip(e, library)]
        if seeds:
            for e in entries:
                if e.get('role') == 'primary':
                    e['role'] = 'auto'
            seeds[0]['role'] = 'primary'
            changed = True

    if not any(_ready_clip(e, library) for e in entries):
        raise RuntimeError('Brak sprawnej próbki WAV z tekstem do Fish; sprawdź bibliotekę głosu.')
    if changed:
        _write_manifest(manifest, entries)
    return {'path': str(manifest), 'installed': changed,
            'status': 'repaired' if restored_files or broken_manifest else 'ready',
            'clips': len(entries), 'wav_repaired': restored_files}


def initialize_voice_config(settings: dict, *, new_install: bool) -> dict:
    """Set a usable primary Fish reference without overriding user preferences.

    Called only when app config has no usable voice_ref_path. New installations
    keep Windows TTS if Fish binaries/weights are not installed; cannot simulate
    a cloned voice using the OS voice. A full install with Fish selects s2cpp.
    """
    current = str(settings.get('voice_ref_path', '') or '')
    if current and Path(current).is_file():
        return settings
    result = install_default_voice()
    reference = result['path']
    from fish_bridge import fish_reference_path
    from voice_transcripts import get_transcript_for_audio
    primary = fish_reference_path(reference)
    transcript = get_transcript_for_audio(reference, primary, 'pl')
    if not transcript:
        raise RuntimeError('Domyślna próbka Capri nie ma transkrypcji')
    settings['voice_ref_path'] = reference
    settings['fish_ref_path'] = primary
    settings['fish_ref_transcript'] = transcript
    # Do not silently change a returning user's configured voice engine.
    if new_install and _fish_available():
        settings['tts_engine'] = 's2cpp'
    return settings


def _fish_available() -> bool:
    # Pointers created by the s2cpp installer; do not assume merely having a GPU
    # makes large GGUF weights or the server available.
    engine = Path(__file__).resolve().parent / 's2_cpp_engine'
    try:
        exe = Path((engine / 's2-executable.txt').read_text(encoding='utf-8').strip())
        model = (engine / 'selected-model.txt').read_text(encoding='utf-8').strip()
        return bool(exe.is_file() and model == Path(model).name and
                    (engine / 'models' / model).stat().st_size > 2_500_000_000)
    except (OSError, ValueError):
        return False


def main() -> int:
    from capri_paths import local_root
    from fish_bridge import fish_reference_path
    from voice_transcripts import get_transcript_for_audio
    import traceback
    logfile = local_root() / 'capri_voice_prepare.log'
    logfile.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = install_default_voice()
        manifest = result['path']
        sample = fish_reference_path(manifest)
        transcript = get_transcript_for_audio(manifest, sample, 'pl')
        if not transcript or not Path(sample).is_file():
            raise RuntimeError('Nie udało się przygotować próbki głównej z prawidłową transkrypcją')
        # Repair stale paths after a partial install, without replacing an existing
        # user-selected WAV / library. The manifest is the single source of truth.
        settings_file = data_root() / 'settings.json'
        if settings_file.is_file():
            try:
                settings = json.loads(settings_file.read_text(encoding='utf-8-sig'))
                if isinstance(settings, dict):
                    current = str(settings.get('voice_ref_path') or '')
                    if not current or not Path(current).is_file() or Path(current).resolve() == Path(manifest).resolve():
                        if (settings.get('voice_ref_path') != manifest or
                            settings.get('fish_ref_path') != sample or
                            settings.get('fish_ref_transcript') != transcript):
                            settings.update(voice_ref_path=manifest, fish_ref_path=sample,
                                            fish_ref_transcript=transcript)
                            _write_settings(settings_file, settings)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                # A settings error must have its own diagnostic, not silently erase data.
                with logfile.open('a', encoding='utf-8') as out:
                    out.write('Ustawienia głosu: ' + traceback.format_exc() + '\n')
        with logfile.open('a', encoding='utf-8') as out:
            out.write('OK: ' + json.dumps(result, ensure_ascii=False) + '\n')
        print('CAPRI VOICE READY:', manifest, '\n  GŁÓWNA:', sample,
              '\n  TRANSKRYPCJA:', transcript, '\n  STAN:', result['status'])
        return 0
    except Exception:
        with logfile.open('a', encoding='utf-8') as out:
            out.write('ERROR: ' + traceback.format_exc() + '\n')
        raise


def _write_settings(path: Path, settings: dict):
    fd, temp = tempfile.mkstemp(prefix='.capri-voice-config-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(settings, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
