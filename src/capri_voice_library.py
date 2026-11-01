"""User-approved voice takes. Exact text -> local audio; never used to pick AI text.

Separate from auto-generated Fish cache. Imported audio remains available after
Capri restarts, even when the automatic cache trims itself.
"""
from __future__ import annotations

from capri_paths import data_root

import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
import threading
from datetime import datetime, timezone
import unicodedata
import uuid
import wave

ROOT = data_root() / 'manual_voice'
INDEX = ROOT / 'index.json'
_LOCK = threading.RLock()
MAX_AUDIO_BYTES = 120 * 1024 * 1024
MAX_TEXT = 1200
MAX_TRIGGERS = 25
MAX_INTENT = 650
MAX_TRIGGER_LENGTH = 160
MATCH_MODES = ('exact', 'contains')
EXTENSIONS = {'.wav', '.mp3'}


def normalized_text(text: str) -> str:
    """Whitespace/NFC only, no paraphrase, punctuation or case substitutions."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', str(text or ''))).strip()


def normalized_question(text: str) -> str:
    """Insensitive to case, punctuation and extra spaces, but not different words."""
    value = unicodedata.normalize('NFC', str(text or '')).casefold()
    value = re.sub(r'[^\w\s]', ' ', value, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', value).strip()


def _intent_ok(intent: str = '') -> str:
    if not isinstance(intent, str):
        raise ValueError('Instrukcja użycia musi być tekstem.')
    value = normalized_text(intent)
    if len(value) > MAX_INTENT:
        raise ValueError(f'Instrukcja może mieć maksymalnie {MAX_INTENT} znaków.')
    return value


def _rules_ok(triggers=None, match_mode='exact') -> tuple[list[str], str]:
    if match_mode not in MATCH_MODES:
        raise ValueError('Nieprawidłowy sposób dopasowywania pytania.')
    if triggers is None:
        return [], match_mode
    if isinstance(triggers, str):
        triggers = triggers.splitlines()
    if not isinstance(triggers, (list, tuple)):
        raise ValueError('Pytania muszą być listą lub osobnymi liniami tekstu.')
    clean = []
    seen = set()
    for item in triggers:
        if not isinstance(item, str):
            raise ValueError('Pytanie musi być tekstem.')
        phrase = normalized_text(item)
        if not phrase:
            continue
        if len(phrase) > MAX_TRIGGER_LENGTH:
            raise ValueError(f'Jedno pytanie może mieć maksymalnie {MAX_TRIGGER_LENGTH} znaków.')
        needle = normalized_question(phrase)
        if not needle:
            raise ValueError('Pytanie musi zawierać słowa, nie tylko znaki interpunkcyjne.')
        if needle not in seen:
            clean.append(phrase)
            seen.add(needle)
    if len(clean) > MAX_TRIGGERS:
        raise ValueError(f'Najwyżej {MAX_TRIGGERS} pytań dla jednego nagrania.')
    if match_mode == 'contains' and any(len(normalized_question(x)) < 5 for x in clean):
        raise ValueError('Fraza „zawiera” musi mieć przynajmniej 5 znaków.')
    return clean, match_mode


def validate_rules(triggers=None, match_mode: str = 'exact') -> tuple[list[str], str]:
    """Public validator for the independent voice manager before expensive rendering."""
    return _rules_ok(triggers, match_mode)


def _check_question_conflicts(items: list[dict], triggers: list[str], mode: str,
                              language: str, *, excluding: str = ''):
    if not triggers or mode != 'exact':
        return
    needles = {normalized_question(item) for item in triggers}
    for item in items:
        if item.get('id') == excluding or item.get('language') != language:
            continue
        if item.get('match_mode', 'exact') != 'exact':
            continue
        other = {normalized_question(x) for x in (item.get('triggers') or []) if isinstance(x, str)}
        if needles & other:
            raise ValueError('To pytanie jest już przypisane do innego nagrania w tym języku.')


def find_for_question(question: str, language: str) -> dict | None:
    """User-authored question -> preapproved response and audio. Never invent an answer.

    Exact beats contains; longer contains phrases take priority over shorter ones.
    Legacy v15.11 entries without triggers do not intercept questions.
    """
    normalized = normalized_question(question)
    if not normalized or language not in ('pl', 'en'):
        return None
    candidates = []
    try:
        with _LOCK:
            for index, item in enumerate(_load_unlocked()):
                if item.get('enabled', True) is not True or item.get('language') != language:
                    continue
                mode = item.get('match_mode', 'exact')
                if mode not in MATCH_MODES or not isinstance(item.get('triggers'), list):
                    continue
                for trigger in item['triggers']:
                    if not isinstance(trigger, str):
                        continue
                    rule = normalized_question(trigger)
                    if not rule:
                        continue
                    if mode == 'exact' and normalized == rule:
                        priority = (2, len(rule), index)
                    elif mode == 'contains' and len(rule) >= 5 and (' ' + rule + ' ') in (' ' + normalized + ' '):
                        priority = (1, len(rule), index)
                    else:
                        continue
                    path = entry_audio(item)
                    if path and normalized_text(item.get('text', '')):
                        candidates.append((priority, item, path))
        if candidates:
            _, found, path = max(candidates, key=lambda x: x[0])
            return {'id': found['id'], 'text': found['text'], 'path': path,
                    'trigger': question, 'mode': found['match_mode']}
    except (OSError, ValueError, TypeError):
        # Malformed library should never break regular LLM chat.
        return None
    return None


def _text_ok(text: str) -> str:
    value = normalized_text(text)
    if not value or len(value) > MAX_TEXT:
        raise ValueError(f'Tekst musi mieć od 1 do {MAX_TEXT} znaków.')
    return value


def _lang_ok(language: str):
    if language not in ('pl', 'en'):
        raise ValueError('Wybierz język PL albo EN.')


def _load_unlocked() -> list[dict]:
    if not INDEX.exists():
        return []
    try:
        data = json.loads(INDEX.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('items'), list):
            raise ValueError('Nieprawidłowy format biblioteki głosu.')
        return [x for x in data['items'] if isinstance(x, dict)]
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError('Nie można odczytać biblioteki głosu: ' + str(exc)) from exc


def _save_unlocked(items: list[dict]):
    ROOT.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix='.index-', suffix='.tmp', dir=ROOT)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump({'version': 1, 'items': items}, output, indent=2, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, INDEX)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def _stored_path(filename: str) -> Path | None:
    if not isinstance(filename, str) or not re.fullmatch(r'[a-f0-9]{32}\.(?:wav|mp3)', filename):
        return None
    return ROOT / filename


def _usable_audio(path: Path) -> bool:
    """Basic header checks; QtMultimedia handles MP3 playback on Windows."""
    try:
        if not path.is_file() or not 256 <= path.stat().st_size <= MAX_AUDIO_BYTES:
            return False
        if path.suffix.lower() == '.wav':
            # Also accept the IEEE float32 WAVs used by some Fish exporters.
            # Python's wave.open() supports only PCM in older Python versions.
            with path.open('rb') as handle:
                if handle.read(4) != b'RIFF':
                    return False
                handle.read(4)  # RIFF length
                if handle.read(4) != b'WAVE':
                    return False
                fmt, data_size = None, 0
                while handle.tell() + 8 <= path.stat().st_size:
                    tag = handle.read(4)
                    length_raw = handle.read(4)
                    if len(length_raw) != 4:
                        break
                    length = struct.unpack('<I', length_raw)[0]
                    position = handle.tell()
                    if position + length > path.stat().st_size:
                        return False
                    if tag == b'fmt ' and length >= 16:
                        fmt = struct.unpack('<HHIIHH', handle.read(16))
                    elif tag == b'data':
                        data_size = length
                    handle.seek(position + length + (length & 1))
                if not fmt:
                    return False
                code, channels, rate, _, _, bits = fmt
                return (code in (1, 3) and channels in (1, 2) and
                        8000 <= rate <= 192000 and bits in (8, 16, 24, 32) and data_size > 0)
        if path.suffix.lower() == '.mp3':
            with path.open('rb') as fd:
                header = fd.read(10240)
            return header.startswith(b'ID3') or any(header[i] == 0xff and (header[i+1] & 0xe0) == 0xe0
                                                    for i in range(len(header)-1))
    except (OSError, EOFError, wave.Error):
        return False
    return False


def list_entries() -> list[dict]:
    with _LOCK:
        return [dict(entry) for entry in _load_unlocked()]


def find_audio(text: str, language: str) -> str | None:
    """Exact AI-wording match, punctuation-tolerant only for very short replies."""
    phrase = normalized_text(text)
    short = len(phrase) <= 75 and len(phrase.split()) <= 8
    if not phrase or language not in ('pl', 'en'):
        return None
    try:
        with _LOCK:
            for item in reversed(_load_unlocked()):
                if item.get('enabled', True) is not True or item.get('language') != language:
                    continue
                saved = normalized_text(item.get('text', ''))
                if saved != phrase:
                    if not (short and len(saved) <= 75 and len(saved.split()) <= 8
                            and normalized_question(saved) == normalized_question(phrase)):
                        continue
                file_path = _stored_path(item.get('filename', ''))
                if file_path is not None and _usable_audio(file_path):
                    return str(file_path)
    except (OSError, ValueError):
        # Broken index never prevents regular Fish from speaking.
        pass
    return None


def _unique(items: list[dict], text: str, language: str, *, excluding: str = ''):
    for item in items:
        if (item.get('id') != excluding and item.get('language') == language and
                normalized_text(item.get('text', '')) == text):
            raise ValueError('Nagranie z identycznym tekstem i językiem już istnieje. Zmień istniejący wpis.')


def add_audio(source: str | Path, text: str, language: str, *, origin: str = 'import',
              triggers=None, match_mode: str = 'exact', intent: str = '') -> dict:
    phrase = _text_ok(text)
    _lang_ok(language)
    triggers, match_mode = _rules_ok(triggers, match_mode)
    intent = _intent_ok(intent)
    source = Path(source).expanduser().resolve()
    suffix = source.suffix.lower()
    if suffix not in EXTENSIONS or not _usable_audio(source):
        raise ValueError('Wybierz prawidłowy WAV lub MP3 (maks. 120 MB).')
    with _LOCK:
        items = _load_unlocked()
        _unique(items, phrase, language)
        _check_question_conflicts(items, triggers, match_mode, language)
        ROOT.mkdir(parents=True, exist_ok=True)
        item_id = uuid.uuid4().hex
        filename = item_id + suffix
        target = ROOT / filename
        staging = ROOT / ('.copy-' + uuid.uuid4().hex + suffix)
        try:
            shutil.copyfile(source, staging)
            if not _usable_audio(staging):
                raise ValueError('Kopia pliku audio jest nieprawidłowa.')
            os.replace(staging, target)
            item = {'id': item_id, 'text': phrase, 'language': language,
                    'filename': filename, 'origin': origin, 'enabled': True,
                    'triggers': triggers, 'match_mode': match_mode, 'intent': intent,
                    'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
            try:
                _save_unlocked([*items, item])
            except Exception:
                target.unlink(missing_ok=True)
                raise
            return dict(item)
        finally:
            staging.unlink(missing_ok=True)


def update_entry(item_id: str, text: str, language: str, *, enabled: bool = True,
                 triggers=None, match_mode: str | None = None, intent: str | None = None) -> dict:
    phrase = _text_ok(text)
    _lang_ok(language)
    with _LOCK:
        items = _load_unlocked()
        _unique(items, phrase, language, excluding=item_id)
        for item in items:
            if item.get('id') == item_id:
                validated_triggers, validated_mode = _rules_ok(
                    item.get('triggers', []) if triggers is None else triggers,
                    item.get('match_mode', 'exact') if match_mode is None else match_mode)
                _check_question_conflicts(items, validated_triggers, validated_mode, language, excluding=item_id)
                item.update(text=phrase, language=language, enabled=bool(enabled),
                            triggers=validated_triggers, match_mode=validated_mode,
                            intent=_intent_ok(item.get('intent', '') if intent is None else intent))
                _save_unlocked(items)
                return dict(item)
    raise ValueError('Nie znaleziono nagrania w bibliotece.')


def remove_entry(item_id: str):
    with _LOCK:
        items = _load_unlocked()
        chosen = next((x for x in items if x.get('id') == item_id), None)
        if chosen is None:
            raise ValueError('Nie znaleziono nagrania w bibliotece.')
        # Index first: Capri immediately stops selecting a deleted track.
        _save_unlocked([x for x in items if x.get('id') != item_id])
        file_path = _stored_path(chosen.get('filename', ''))
        if file_path:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass


def entry_audio(item: dict) -> str | None:
    path = _stored_path(item.get('filename', ''))
    return str(path) if path and _usable_audio(path) else None
