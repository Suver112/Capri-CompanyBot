"""Local per-clip Whisper transcript library for Capri voice corpus.

Every transcript stays attached to its own generated WAV in capri_voice_corpus.json.
No audio is uploaded, and source media are never modified.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Callable

from voice_clone import MANIFEST_NAME, _read_manifest, _safe_managed_file, voices_dir, is_managed_corpus_path

_LOCK = threading.RLock()


def _corpus_path(reference_path: str) -> Path:
    path = Path(reference_path).resolve()
    if not is_managed_corpus_path(str(path)):
        raise ValueError("Transkrypcje można edytować tylko w bibliotece Capri.")
    if not path.is_file():
        raise FileNotFoundError("Brak biblioteki nagrań Capri.")
    return path


def _save(path: Path, data: dict) -> None:
    """Atomically replace only the manifest, even if the process is interrupted."""
    fd, temporary = tempfile.mkstemp(prefix="capri_transcripts_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) > 2500:
        raise ValueError("Transkrypcja pojedynczej próbki jest za długa (limit 2500 znaków).")
    return text


def get_transcript_for_audio(reference_path: str, wav_path: str, lang: str = "pl") -> str:
    """Return cached text ONLY if attached to the precise active clip and language."""
    if not reference_path or Path(reference_path).suffix.lower() != ".json":
        return ""
    try:
        with _LOCK:
            path = _corpus_path(reference_path)
            for entry in _read_manifest(str(path))["clips"]:
                if (path.parent / entry.get("file", "")).resolve() == Path(wav_path).resolve():
                    translations = entry.get("transcripts", {})
                    if isinstance(translations, dict) and isinstance(translations.get(lang), dict):
                        return str(translations[lang].get("text", ""))
                    return str(entry.get("transcript", "")) if entry.get("transcript_lang") == lang else ""
    except (OSError, ValueError, KeyError):
        return ""
    return ""


def update_transcript(reference_path: str, fingerprint: str, text: str,
                      *, lang: str = "pl", model: str = "manual") -> None:
    if lang not in ("pl", "en"):
        raise ValueError("Dostępne języki: pl, en")
    cleaned = _clean_text(text)
    with _LOCK:
        path = _corpus_path(reference_path)
        data = _read_manifest(str(path))
        for entry in data["clips"]:
            if entry.get("fingerprint") != fingerprint:
                continue
            if _safe_managed_file(path.parent, entry.get("file", "")) is None:
                raise FileNotFoundError("Nagranie nie istnieje w bibliotece Capri.")
            translations = entry.get("transcripts", {})
            if not isinstance(translations, dict):
                translations = {}
            # Preserve older language records and existing v10.2 metadata.
            if entry.get("transcript", "") and entry.get("transcript_lang") in ("pl", "en"):
                prior_lang = entry["transcript_lang"]
                translations.setdefault(prior_lang, {"text": entry["transcript"],
                                                      "model": entry.get("transcript_model", "legacy")})
            if cleaned:
                translations[lang] = {"text": cleaned, "model": model}
                entry.update(transcript=cleaned, transcript_lang=lang, transcript_model=model)
            else:
                translations.pop(lang, None)
                if entry.get("transcript_lang") == lang:
                    for key in ("transcript", "transcript_lang", "transcript_model"):
                        entry.pop(key, None)
            entry["transcripts"] = translations
            _save(path, data)
            return
        raise ValueError("Nie znaleziono wybranej próbki.")


def update_transcript_for_audio(reference_path: str, wav_path: str, text: str,
                                *, lang: str = "pl", model: str = "manual") -> bool:
    """Update exact current clip, never accidentally save against an old primary."""
    if not reference_path or Path(reference_path).suffix.lower() != ".json":
        return False
    with _LOCK:
        path = _corpus_path(reference_path)
        for entry in _read_manifest(str(path))["clips"]:
            if (path.parent / entry.get("file", "")).resolve() == Path(wav_path).resolve():
                update_transcript(reference_path, entry["fingerprint"], text, lang=lang, model=model)
                return True
    return False


def transcribe_corpus(reference_path: str, transcribe_wav: Callable[[bytes], str],
                      *, lang: str = "pl", model: str = "small", force: bool = False,
                      progress: Callable[[int, int, str], None] | None = None,
                      selected_ids: list[str] | None = None) -> dict:
    """Sequential offline transcription; saves each result so work survives interruption.

    The supplied callable does speech recognition; this module deliberately does
    not load Whisper, GUI or network dependencies. No duplicate transcription
    for matching-language cached texts unless force=True.
    """
    if lang not in ("pl", "en"):
        raise ValueError("Dostępne języki: pl, en")
    with _LOCK:
        path = _corpus_path(reference_path)
        snapshots = [dict(x) for x in _read_manifest(str(path)).get("clips", [])]
    wanted = set(selected_ids) if selected_ids is not None else None
    clips = [x for x in snapshots if wanted is None or x.get("fingerprint") in wanted]
    if selected_ids is not None and not clips:
        raise ValueError("Nie znaleziono wybranych klipów.")
    if not clips:
        raise ValueError("Biblioteka próbek jest pusta.")
    result = {"total": len(clips), "processed": 0, "skipped": 0, "failed": 0,
              "empty": 0, "errors": []}
    for number, entry in enumerate(clips, 1):
        name = str(entry.get("source_name", entry.get("file", "klip")))
        if progress:
            progress(number - 1, len(clips), name)
        cached = entry.get("transcripts", {})
        previous = cached.get(lang, {}).get("text", "") if isinstance(cached, dict) and isinstance(cached.get(lang), dict) else ""
        existing = bool(str(previous or (entry.get("transcript", "") if entry.get("transcript_lang") == lang else "")).strip())
        if existing and not force:
            result["skipped"] += 1
        else:
            try:
                clip = _safe_managed_file(path.parent, entry.get("file", ""))
                if clip is None:
                    raise FileNotFoundError("Brak pliku WAV")
                words = _clean_text(transcribe_wav(clip.read_bytes()))
                if not words:
                    result["empty"] += 1
                else:
                    # Save immediately; each clip has its own immutable fingerprint.
                    update_transcript(reference_path, entry["fingerprint"], words,
                                      lang=lang, model=model)
                    result["processed"] += 1
            except Exception as exc:
                result["failed"] += 1
                if len(result["errors"]) < 12:
                    result["errors"].append(f"{name} (#{number}): {str(exc)[:150]}")
        if progress:
            progress(number, len(clips), name)
    return result
