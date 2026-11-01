"""Local, opt-in wake phrase recognition for Capri.

Only the speech transcription of a short utterance is compared with the wake
phrase; no LLM/network is used and unrelated speech is discarded immediately.
The UI must explicitly enable microphone listening in its settings.
"""
from __future__ import annotations

import re
import unicodedata

# STT commonly writes the fictional name phonetically or adds punctuation.
# The wake phrase must BEGIN an utterance: a quoted phrase inside a question
# or ordinary discussion is not a command to start the microphone.
_WAKE = re.compile(
    r'^(?:hej|hey|ej|hejka|heja|haj)\s*[,!?.-]?\s*'
    r'(?:capri|kapri|kapry|kaprii|caperi|kaperi|kapi|capry|cabri)\b', re.I)
# A near miss only triggers an extra local STT pass, never a wake action.
# Keep this deliberately narrow so ordinary background talk stays ignored.
_NEAR = re.compile(
    r'^(?:hej|hey|ej|hejka|haj)\s*[,!?.-]?\s*'
    r'(?:kap\w{0,5}|cap\w{0,5}|kab\w{0,5}|gab\w{0,5})\b', re.I)



def _normalize(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', str(text or '').strip().lower())
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    # Commas between words are common in Parakeet/Whisper output.
    return re.sub(r'\s+', ' ', normalized).strip()


def wake_suffix(transcript: str) -> str | None:
    """Return remainder after a real wake phrase; None for unrelated speech.

    Empty string means the user only said the wake phrase and must be given
    an opportunity to dictate the next utterance.
    """
    original = str(transcript or "").strip()
    text = _normalize(original)
    match = _WAKE.match(text)
    if not match:
        return None
    # Ignore interjections or filler before an actual command after waking.
    tail = original[match.end():].lstrip(' ,.!?:;—-')
    return tail


def uncertain_wake_candidate(transcript: str) -> bool:
    """A likely mistranscription that MAY merit one Whisper verification.

    This never starts voice capture. The caller must validate a fresh
    transcription using wake_suffix() before activation.
    """
    text = _normalize(transcript)
    return bool(text and len(text) <= 90 and not _WAKE.match(text)
                and (text in ('hej', 'hey', 'ej', 'hejka') or _NEAR.match(text)))
