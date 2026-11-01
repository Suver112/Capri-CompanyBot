"""Persistent, exact-text audio cache for local Fish Vulkan.

The conversational model ALWAYS generates the text. Only the audio is reused.
A voice/profile/reference change invalidates the key, not the user's chat.
No network, no external dependencies; files live under %APPDATA%/CapriOverlay.
"""
from __future__ import annotations

from capri_paths import data_root

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import threading
import unicodedata
import uuid
import wave

CACHE_REVISION = 1
CACHE_MAX_FILES = 350
CACHE_MAX_BYTES = 650 * 1024 * 1024
CACHE_DIR = data_root() / 'voice_cache'
_LOCK = threading.RLock()


def exact_spoken_text(text: str) -> str:
    """Only collapse whitespace. Do NOT do fuzzy/synonym matching or change case."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', str(text or ''))).strip()


def audio_key(text: str, language: str, reference: str, transcript: str, *,
              profile: str = 'clear', whisper: bool = False,
              emotion_intensity: int = 65, auto_emotions: bool = True,
              transcript_reference_path: str = '',
              forced_emotion: str | None = None, cache_scope: str = 'chunk') -> str:
    phrase = exact_spoken_text(text)
    if not phrase or language not in ('pl', 'en'):
        raise ValueError('Nieprawidłowy tekst lub język pamięci audio')
    ref = Path(reference).expanduser().resolve()
    stat = ref.stat()
    # Cache is keyed by the reference file metadata + transcript, not the
    # Windows user's username or the GPU port. A changed voice gets a new key.
    spec = {
        'revision': CACHE_REVISION,
        'engine': 'fish_s2cpp_vulkan',
        'text': phrase,
        'lang': language,
        'ref': str(ref).casefold(),
        'ref_size': stat.st_size,
        'ref_mtime_ns': stat.st_mtime_ns,
        'ref_transcript': str(transcript or '').strip(),
        'transcript_reference_path': str(Path(transcript_reference_path).expanduser().resolve()).casefold() if transcript_reference_path else '',
        'profile': profile,
        'whisper': bool(whisper),
        'emotion_intensity': int(emotion_intensity),
        'auto_emotions': bool(auto_emotions),
    }
    # Preserve historic neutral/angry chunk keys; distinguish all other moods
    # and full utterances, so a different delivery never plays a stale WAV.
    if forced_emotion:
        spec['forced_emotion'] = forced_emotion
    if cache_scope != 'chunk':
        spec['cache_scope'] = cache_scope
    raw = json.dumps(spec, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _valid_wav(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < 256:
            return False
        with wave.open(str(path), 'rb') as stream:
            return (stream.getnchannels() in (1, 2) and
                    stream.getframerate() >= 8000 and
                    stream.getnframes() >= stream.getframerate() // 5)
    except (OSError, EOFError, wave.Error):
        return False


def cached_audio(key: str) -> str | None:
    """Return persistent WAV or None. Touch for LRU. Never return corrupt audio."""
    if not re.fullmatch(r'[0-9a-f]{64}', str(key)):
        return None
    candidate = CACHE_DIR / (key + '.wav')
    with _LOCK:
        if _valid_wav(candidate):
            try:
                os.utime(candidate, None)
            except OSError:
                pass
            return str(candidate)
        if candidate.exists():
            try:
                candidate.unlink()
            except OSError:
                pass
    return None


def save_audio(key: str, generated_path: str) -> str:
    """Atomic copy: never expose partially written or invalid WAVs."""
    if not re.fullmatch(r'[0-9a-f]{64}', str(key)):
        raise ValueError('Nieprawidłowy identyfikator cache')
    source = Path(generated_path)
    if not _valid_wav(source):
        raise ValueError('Fish nie wygenerował poprawnego WAV')
    with _LOCK:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        target = CACHE_DIR / (key + '.wav')
        if _valid_wav(target):
            os.utime(target, None)
            return str(target)
        staging = CACHE_DIR / ('.part-' + uuid.uuid4().hex + '.wav')
        try:
            shutil.copyfile(source, staging)
            if not _valid_wav(staging):
                raise ValueError('Uszkodzona kopia WAV')
            os.replace(staging, target)
        finally:
            staging.unlink(missing_ok=True)
        _trim_cache(keep=target)
        return str(target)


def _trim_cache(*, keep: Path | None = None):
    tracks = []
    for entry in CACHE_DIR.glob('*.wav'):
        try:
            st = entry.stat()
            tracks.append((st.st_mtime_ns, st.st_size, entry))
        except OSError:
            continue
    size = sum(x[1] for x in tracks)
    count = len(tracks)
    for _, length, path in sorted(tracks):
        if count <= CACHE_MAX_FILES and size <= CACHE_MAX_BYTES:
            break
        if path == keep:
            continue
        try:
            path.unlink()
            count -= 1
            size -= length
        except OSError:
            pass


def cache_stats() -> tuple[int, int]:
    if not CACHE_DIR.is_dir():
        return (0, 0)
    files = [p for p in CACHE_DIR.glob('*.wav') if p.is_file()]
    return (len(files), sum(p.stat().st_size for p in files))


def external_audio_key(text: str, language: str, *, provider: str, model: str,
                       voice: str, reference: str = '', transcript: str = '',
                       settings: dict | None = None) -> str:
    """Persistent key for remote TTS, with no API key/credential in the digest.

    A different provider, model, voice or changed reference invalidates reuse.
    """
    if language not in ('pl', 'en') or not exact_spoken_text(text):
        raise ValueError('Nieprawidłowy tekst/język zdalnego TTS')
    spec = {'revision': CACHE_REVISION, 'scope': 'remote_utterance',
            'provider': str(provider), 'model': str(model), 'voice': str(voice),
            'text': exact_spoken_text(text), 'language': language,
            'transcript': transcript, 'settings': settings or {}}
    if reference:
        ref = Path(reference).expanduser().resolve()
        stat = ref.stat()
        spec['ref'] = str(ref).casefold()
        spec['ref_size'] = stat.st_size
        spec['ref_mtime_ns'] = stat.st_mtime_ns
    raw = json.dumps(spec, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()
