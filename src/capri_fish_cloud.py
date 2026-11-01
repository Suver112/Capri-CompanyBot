"""Fish Audio S2.1 Pro Free HTTPS client for Capri.

Uses a fixed Fish endpoint, never sends API tokens to local models,
and never silently switches to paid synthesis. Secure credential storage
uses OS keyring; FISH_API_KEY environment variable is also supported.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
import wave

from fish_bridge import fish_reference_path
from fish_emotions import fish_emotional_text
from voice_clone import clean_speech_text

ENDPOINT = "https://api.fish.audio/v1/tts"
MODEL = "s2.1-pro-free"
KEYRING_SERVICE = "Capri Overlay Fish Cloud"
KEYRING_USER = "fish_api_key"
MAX_WAV_BYTES = 80 * 1024 * 1024
MAX_REFERENCE_BYTES = 25 * 1024 * 1024


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError as exc:
        raise RuntimeError('Brakuje keyring. Uruchom ustawienia Głos w Capri.') from exc


def get_fish_api_key() -> str:
    env_key = os.environ.get('FISH_API_KEY', '').strip()
    if env_key:
        return env_key
    try:
        return (_keyring().get_password(KEYRING_SERVICE, KEYRING_USER) or '').strip()
    except Exception:
        return ''


def store_fish_api_key(key: str) -> None:
    key = (key or '').strip()
    if not key:
        raise ValueError('Pusty klucz API.')
    _keyring().set_password(KEYRING_SERVICE, KEYRING_USER, key)


def delete_fish_api_key() -> None:
    keyring = _keyring()
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except keyring.errors.PasswordDeleteError:
        pass


def _validated_wav(data: bytes) -> None:
    if len(data) > MAX_WAV_BYTES or not data.startswith(b'RIFF') or data[8:12] != b'WAVE':
        raise RuntimeError('Fish ONLINE nie zwrocil poprawnego WAV.')
    try:
        with wave.open(io.BytesIO(data), 'rb') as wav:
            if wav.getnframes() < max(1, wav.getframerate() // 8):
                raise RuntimeError('Fish ONLINE zwrocil zbyt krotki WAV.')
    except (wave.Error, EOFError) as exc:
        raise RuntimeError('Fish ONLINE zwrocil nieobslugiwany WAV.') from exc


def synthesize_fish_cloud(text: str, lang: str, *,
                          reference_path: str = '', transcript: str = '',
                          transcript_reference_path: str = '', reference_id: str = '',
                          progress=None, timeout: int = 120, whisper: bool = False,
                          emotion_intensity: int = 65, auto_emotions: bool = True,
                          forced_emotion: str | None = None) -> str:
    if lang not in ('pl', 'en'):
        raise ValueError('Fish ONLINE: obslugiwany jezyk PL i EN.')
    key = get_fish_api_key()
    if not key:
        raise RuntimeError('Brak klucza API Fish Audio. Wpisz go w ustawieniach Fish ONLINE.')
    cleaned = clean_speech_text(text).strip()
    if not cleaned:
        raise ValueError('Fish ONLINE: pusta odpowiedz.')
    # S2.1 sometimes clips the last phoneme on unterminated prompts. A final
    # sentence mark encourages natural closing prosody without adding words.
    if cleaned[-1] not in '.!?…':
        cleaned = cleaned.rstrip(" \"”'") + '.'
    # Emotion tags from Fish S2 can also guide S2.1.
    speech_text = fish_emotional_text(
        cleaned, lang, intensity=emotion_intensity,
        whisper=whisper, enabled=auto_emotions,
        forced_emotion=forced_emotion)
    reference_id = (reference_id or '').strip()
    payload = {'text': speech_text, 'format': 'wav', 'streaming': False,
               'latency': 'balanced', 'chunk_length': 200}
    if reference_id:
        payload['reference_id'] = reference_id
    else:
        ref = Path(fish_reference_path(reference_path)).resolve()
        transcript = (transcript or '').strip()
        if not transcript or not transcript_reference_path or Path(transcript_reference_path).resolve() != ref:
            raise ValueError('Fish ONLINE: transkrypcja nie pasuje do probki glownej. Uzyj AUTO STT.')
        if ref.stat().st_size > MAX_REFERENCE_BYTES:
            raise ValueError('Fish ONLINE: probka WAV przekracza 25 MB.')
        payload['references'] = [{'audio': ref.read_bytes(), 'text': transcript}]
    try:
        import msgpack
    except ImportError as exc:
        raise RuntimeError('Brakuje msgpack. Uruchom ustawienia Głos w Capri.') from exc
    if progress:
        progress('cloud_load')
    body = msgpack.packb(payload, use_bin_type=True)
    req = urllib.request.Request(
        ENDPOINT, data=body, method='POST', headers={
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/msgpack',
            'Accept': 'audio/wav', 'model': MODEL})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            audio = response.read(MAX_WAV_BYTES + 1)
    except urllib.error.HTTPError as exc:
        status = exc.code
        if status == 401:
            reason = 'klucz API nieprawidlowy lub wygasl.'
        elif status == 403:
            reason = 'brak uprawnien do darmowego modelu na tym koncie.'
        elif status == 429:
            reason = 'limit zapytan. Sprobuj ponownie pozniej.'
        else:
            reason = 'API zwrocilo blad; sprawdz stan uslugi Fish Audio.'
        raise RuntimeError(f'Fish ONLINE HTTP {status}: {reason}') from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError('Fish ONLINE: brak polaczenia HTTPS lub timeout.') from exc
    _validated_wav(audio)
    fd, path = tempfile.mkstemp(prefix='capri_fish_cloud_', suffix='.wav')
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(audio)
        return path
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
