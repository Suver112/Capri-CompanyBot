"""User-configured OpenAI-compatible Chat Completions and Speech APIs.

External providers are OPT-IN, independent of Fish Audio, and never receive
agent tools, API credentials from another provider, local files or microphone
audio. Keys live in the OS credential store, not config.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from urllib import request, error, parse
import wave

SERVICE = 'Capri Overlay External APIs'
PROVIDER_KEYS = {'custom', 'nvidia', 'openai', 'anthropic', 'deepseek', 'openrouter'}
MAX_RESPONSE_BYTES = 90 * 1024 * 1024
MAX_CHAT_BYTES = 3 * 1024 * 1024


def endpoint_url(raw: str, *, kind: str = 'chat') -> str:
    """Only full HTTPS endpoints; HTTP allowed solely on loopback for local gateways."""
    raw = str(raw or '').strip()
    parsed = parse.urlsplit(raw)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname:
        raise ValueError('API: podaj pełny adres HTTPS endpointu (https://...).')
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError('API: nie wpisuj klucza, loginu ani fragmentu w adresie URL.')
    if parsed.scheme == 'http' and parsed.hostname.casefold() not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('API: zewnętrzny adres musi używać HTTPS.')
    if parsed.query:
        raise ValueError('API: podaj adres endpointu bez parametrów zapytania.')
    if len(raw) > 1024 or not parsed.path.startswith('/') or parsed.path == '/':
        raise ValueError('API: podaj pełny adres endpointu, np. /v1/chat/completions.')
    if kind not in ('chat', 'tts'):
        raise ValueError('API: nieznany typ.')
    return raw


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError as exc:
        raise RuntimeError('Brak modułu keyring. Uruchom ustawienia Głos w Capri.') from exc


def _key_kind(kind: str) -> bool:
    return kind in ('chat', 'tts') or (kind.startswith('chat:') and kind[5:] in PROVIDER_KEYS)


def read_api_key(kind: str) -> str:
    if not _key_kind(kind):
        raise ValueError('API: nieznany typ klucza.')
    env_name = kind.replace(':', '_').upper()
    variable = 'CAPRI_EXTERNAL_' + env_name + '_API_KEY'
    env_key = os.getenv(variable, '').strip()
    if env_key:
        return env_key
    # Older versions stored a single generic chat key. Keep it only for the
    # custom endpoint, never reuse it for a different provider by mistake.
    if kind == 'chat:custom':
        old = os.getenv('CAPRI_EXTERNAL_CHAT_API_KEY', '').strip()
        if old:
            return old
    try:
        key = (_keyring().get_password(SERVICE, kind) or '').strip()
        if kind == 'chat:custom' and not key:
            key = (_keyring().get_password(SERVICE, 'chat') or '').strip()
        return key
    except Exception:
        return ''


def store_api_key(kind: str, key: str) -> None:
    if not _key_kind(kind) or not isinstance(key, str) or not key.strip():
        raise ValueError('API: wpisz prawidłowy klucz.')
    _keyring().set_password(SERVICE, kind, key.strip())


def remove_api_key(kind: str) -> None:
    if not _key_kind(kind):
        raise ValueError('API: nieznany typ klucza.')
    try:
        _keyring().delete_password(SERVICE, kind)
    except _keyring().errors.PasswordDeleteError:
        pass


def _post(url: str, payload: dict, kind: str, timeout: int, *, credential_kind: str | None = None) -> bytes:
    endpoint_url(url, kind=kind)
    key = read_api_key(credential_kind or kind)
    # A localhost OpenAI-compatible gateway may be intentionally unauthenticated.
    hostname = parse.urlsplit(url).hostname.casefold()
    if not key and hostname not in ('localhost', '127.0.0.1', '::1'):
        raise RuntimeError('API: brak klucza. Zapisz klucz w ustawieniach Capri.')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json' if kind == 'chat' else 'audio/wav'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                          headers=headers, method='POST')
    try:
        # urllib uses the OS certificate store / normal TLS verification.
        with request.urlopen(req, timeout=timeout) as res:
            length_limit = MAX_CHAT_BYTES if kind == 'chat' else MAX_RESPONSE_BYTES
            data = res.read(length_limit + 1)
            if len(data) > length_limit:
                raise RuntimeError('API: odpowiedź przekracza limit rozmiaru.')
            return data
    except error.HTTPError as exc:
        # Never echo a remote error body: some gateways reflect authorization data.
        raise RuntimeError(f'API {kind.upper()}: HTTP {exc.code}. Sprawdź model, klucz i endpoint.') from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f'API {kind.upper()}: nie udało się połączyć z usługą ({type(exc).__name__}).') from exc


def chat_completion(messages: list[dict], model: str, endpoint: str, *,
                    progress=None, timeout: int = 120, temperature: float | None = None,
                    provider: str = 'custom') -> str:
    """OpenAI Chat Completions wire format; no assumptions about a particular vendor."""
    if not model or len(model) > 180:
        raise ValueError('API: wpisz identyfikator modelu rozmowy.')
    if not messages or not all(isinstance(m, dict) and m.get('role') in ('system','user','assistant')
                               and isinstance(m.get('content'), str) for m in messages):
        raise ValueError('API: nieprawidłowy kontekst rozmowy.')
    if progress:
        progress('external_chat')
    if provider == 'anthropic':
        return _anthropic_messages(messages, model, endpoint, timeout)
    if provider not in PROVIDER_KEYS:
        raise ValueError('API: nieznany dostawca.')
    payload = {'model': model, 'messages': messages, 'stream': False}
    if temperature is not None:
        payload['temperature'] = float(temperature)
    data = _post(endpoint, payload, 'chat', timeout, credential_kind='chat:' + provider)
    try:
        obj = json.loads(data.decode('utf-8'))
        content = obj['choices'][0]['message']['content']
        if isinstance(content, list):
            content = ''.join(part.get('text', '') for part in content if isinstance(part, dict)
                              and part.get('type') == 'text')
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Pusta odpowiedź modelu.')
        return content.strip()
    except (UnicodeDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError('API rozmowy: odpowiedź nie ma formatu Chat Completions lub jest pusta.') from exc


def _anthropic_messages(messages: list[dict], model: str, endpoint: str, timeout: int) -> str:
    endpoint_url(endpoint, kind='chat')
    if parse.urlsplit(endpoint).hostname != 'api.anthropic.com' or not endpoint.endswith('/v1/messages'):
        raise ValueError('Anthropic: nieprawidłowy endpoint Messages API.')
    key = read_api_key('chat:anthropic')
    if not key:
        raise RuntimeError('Anthropic: wprowadź klucz API w ustawieniach.')
    systems = [m['content'] for m in messages if m['role'] == 'system']
    turns = [{'role': m['role'], 'content': m['content']}
             for m in messages if m['role'] in ('user', 'assistant')]
    if not turns:
        raise ValueError('Anthropic: brak wiadomości użytkownika.')
    payload = {'model': model, 'max_tokens': 1024, 'messages': turns}
    if systems:
        payload['system'] = '\n\n'.join(systems)
    req = request.Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                 'x-api-key': key, 'anthropic-version': '2023-06-01'}, method='POST')
    try:
        with request.urlopen(req, timeout=timeout) as response:
            data = response.read(MAX_CHAT_BYTES + 1)
            if len(data) > MAX_CHAT_BYTES:
                raise RuntimeError('Anthropic: odpowiedź jest za duża.')
    except error.HTTPError as exc:
        raise RuntimeError(f'Anthropic: HTTP {exc.code}. Sprawdź klucz, model i limit.') from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f'Anthropic: błąd połączenia ({type(exc).__name__}).') from exc
    try:
        decoded = json.loads(data.decode('utf-8'))
        text = ''.join(b.get('text', '') for b in decoded.get('content', [])
                       if isinstance(b, dict) and b.get('type') == 'text').strip()
        if not text:
            raise ValueError('Empty Anthropic response')
        return text
    except (ValueError, TypeError, AttributeError) as exc:
        raise RuntimeError('Anthropic: odpowiedź nie zawiera tekstu.') from exc


def speech(text: str, model: str, voice: str, endpoint: str, *, timeout: int = 120,
           progress=None) -> str:
    """OpenAI-compatible audio/speech -> WAV; path is a temporary file."""
    if not text.strip() or len(text) > 4000:
        raise ValueError('TTS API: tekst musi mieć 1–4000 znaków.')
    if not model or not voice or len(model) > 180 or len(voice) > 180:
        raise ValueError('TTS API: wpisz model i nazwę głosu.')
    if progress:
        progress('external_tts')
    payload = {'model': model, 'voice': voice, 'input': text, 'response_format': 'wav'}
    data = _post(endpoint, payload, 'tts', timeout)
    try:
        import io
        with wave.open(io.BytesIO(data), 'rb') as audio:
            if audio.getnchannels() not in (1, 2) or audio.getframerate() < 8000 or audio.getnframes() < audio.getframerate() // 6:
                raise ValueError('WAV ma błędne parametry.')
    except (ValueError, wave.Error, EOFError) as exc:
        raise RuntimeError('TTS API: serwer nie zwrócił poprawnego PCM WAV.') from exc
    fd, name = tempfile.mkstemp(prefix='capri_remote_tts_', suffix='.wav')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        return name
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
