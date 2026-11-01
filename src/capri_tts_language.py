"""Local mixed-language pronunciation preparation for Fish s2.cpp.

The Fish s2.cpp HTTP /generate API has no documented per-span language selector.
For PL conversations, pronounce a small set of high-confidence foreign names via
Polish phonetic spellings. Leave full English sentences in their original form.
The screen text and reference transcript are never altered.

Overrides: %APPDATA%/CapriOverlay/pronunciation_overrides.json (Windows).
Set an entry to an empty string to disable its built-in replacement.
"""
from __future__ import annotations
from capri_paths import data_root

import json
import os
from pathlib import Path
import re
from functools import lru_cache

from capri_tts_numbers import normalize_for_speech

# Deliberately conservative. These are Polish approximate phonetic spellings,
# not true phoneme-level language switching. Users can override any entry.
DEFAULT_PRONUNCIATIONS: dict[str, str] = {
    "Night City": "Najt Siti",
    "Johnny Silverhand": "Dżoni Silwerhend",
    "Johnny'ego": "Dżoniego",
    "Johnny": "Dżoni",
    "Silverhanda": "Silwerhenda",
    "Silverhand": "Silwerhend",
    "Edgerunners": "Edżraners",
    "Soulkiller": "Sołlkiler",
    "Blackwall": "Blekłol",
    "Afterlife": "Afterlajf",
    "Braindance": "Brejndens",
    "Dogtown": "Dogtaun",
    "NetWatch": "Net Łocz",
    "Steam": "Stim",
    "Steama": "Stima",
    "Discord": "Diskord",
    "Discorda": "Diskorda",
    "Windows": "Łindołs",
    "YouTube": "Jutub",
    "Google": "Gugl",
    "Chrome": "Kroum",
    "Game Pass": "Gejm Pas",
    "PlayStation": "Plejstejszyn",
    "Xbox": "Eksboks",
    "Microsoft": "Majkrosoft",
    "Fish": "Fisz",
    "Wi-Fi": "Łaj Faj",
    "AI": "ej aj",
    "NPC": "en pi si",
    "GPU": "dżi pi ju",
    "CPU": "si pi ju",
    "USB": "ju es bi",
    "FPS": "ef pi es",
    "No way": "Noł łej",
    "Come on": "Kam on",
    "Oh my God": "Oł maj gad",
    "Game over": "Gejm ołwer",
}

# Do not mistake proper nouns such as "Night City" for English prose.
EN_CUES = frozenset({
    "you", "your", "my", "me", "we", "they", "their", "the", "a", "an",
    "am", "are", "is", "was", "were", "have", "has", "will", "would", "can",
    "could", "should", "why", "what", "where", "when", "how", "this", "that",
    "with", "without", "because", "don't", "did", "do", "does", "not", "from",
    "for", "and", "but", "it's", "i'm", "let's", "going", "want", "know",
    "hello", "thanks", "thank", "please", "good", "morning",
})
PL_CUES = frozenset({
    "ja", "ty", "on", "ona", "my", "wy", "jest", "jesteś", "jesteśmy", "są", "i", "w",
    "co", "jak", "czy", "kiedy", "gdzie", "dlaczego", "przez", "dla",
    "się", "nie", "tak", "to", "tego", "ta", "ten", "jestem", "mam",
    "masz", "mnie", "mój", "twój", "ale", "oraz", "więc", "będzie", "będę",
    "chcę", "chcesz", "może", "możesz", "jest", "bym", "było", "zrobić",
    "idziemy", "zobacz", "dobra", "okej", "bardzo", "teraz", "potem",
})
EN_OPENERS = re.compile(
    r"^\s*(?:hello\b|hi\b|hey\b|thank\s+you\b|good\s+(?:morning|evening|night)\b|"
    r"how\s+are\s+you\b|i\s+(?:am|have|love|like|know|see|think|want|need|don't|can't|will)\b|"
    r"no\s+way\b|come\s+on\b|oh\s+my\s+god\b|see\s+you\b|"
    r"what\s+(?:is|are|do|does)\b|let'?s\b|welcome\s+to\b)",
    flags=re.IGNORECASE,
)
SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+|\n+")
QUOTED_EN = re.compile(r'["“„]([^"“„”]{2,180})["”]')
WORD = re.compile(r"[A-Za-zÀ-ž]+(?:['’][A-Za-z]+)?", flags=re.UNICODE)
POLISH_DIACRITICS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


# Character names (NOT the general letters D and V). Only the exact dotted
# uppercase spellings are rewritten. This is a speech-only transformation.
CHARACTER_INITIALS = re.compile(r"(?<![\w.])([DV])\.(?!\w)")


def normalize_character_names_for_speech(text: str, language: str = "pl") -> str:
    """Read fictional characters D. / V. as Di / Vi, without touching UI text.

    The English spellings Dee/Vee yield the same sounds for English voices.
    This must happen *before* chunk splitting, otherwise the periods would
    cause false sentence boundaries in Fish.
    """
    if not text:
        return text
    names = {"D": "Di", "V": "Vi"} if language != "en" else {"D": "Dee", "V": "Vee"}
    return CHARACTER_INITIALS.sub(lambda match: names[match.group(1)], text)


def _override_file() -> Path:
    return data_root() / "pronunciation_overrides.json"


def ensure_override_file() -> Path:
    """Create optional user-editable dictionary, without replacing existing work."""
    path = _override_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({
                "_instrukcja": "Dodaj: nazwa angielska -> wymowa zapisana po polsku. Pusty tekst wyłącza regułę.",
                "Night City": "Najt Siti",
                "Johnny Silverhand": "Dżoni Silwerhend",
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass  # Read-only folder must never block TTS.
    return path


@lru_cache(maxsize=8)
def _load_rules_from_file(path_text: str, stamp: int) -> dict[str, str]:
    rules = DEFAULT_PRONUNCIATIONS.copy()
    try:
        content = json.loads(Path(path_text).read_text(encoding="utf-8-sig"))
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(key, str) and isinstance(value, str) and not key.startswith("_"):
                    key = key.strip()
                    if 1 <= len(key) <= 64 and len(value) <= 100 and not any(c in value for c in "\r\n"):
                        rules[key] = value.strip()
    except (OSError, UnicodeError, ValueError):
        pass
    return rules


def pronunciation_rules() -> dict[str, str]:
    path = ensure_override_file()
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        stamp = 0
    return _load_rules_from_file(str(path), stamp)


def is_english_sentence(sentence: str) -> bool:
    """High precision classifier. Ambiguous or mixed sentences remain Polish."""
    if any(char in POLISH_DIACRITICS for char in sentence):
        return False
    words = [w.lower().replace("’", "'") for w in WORD.findall(sentence)]
    if not words:
        return False
    en = sum(w in EN_CUES for w in words)
    pl = sum(w in PL_CUES for w in words)
    if EN_OPENERS.search(sentence) and pl <= 1:
        return True
    # Repeated 'the' is strong evidence in longer English passages.
    # Avoid ambiguous single-word matches such as 'Night City' or 'I w Night City'.
    return en >= 2 and en >= pl * 2 and (pl == 0 or en / len(words) >= 0.30)


def phonetic_english_names(text: str) -> str:
    """Apply longest-match *whole phrase* replacements to Polish speech text."""
    rules = pronunciation_rules()
    active = [(k, v) for k, v in rules.items() if k and v]
    if not active:
        return text
    keys = sorted((re.escape(k) for k, _ in active), key=len, reverse=True)
    reg = re.compile(r"(?<!\w)(?:" + "|".join(keys) + r")(?!\w)", re.IGNORECASE)
    folded = {k.casefold(): v for k, v in active}
    return reg.sub(lambda match: folded.get(match.group().casefold(), match.group()), text)


def _language_spans(sentence: str, default_language: str):
    """Keep quoted English as a distinct TTS span inside Polish prose."""
    if default_language != "pl":
        yield sentence, default_language
        return
    pos = 0
    found = False
    for match in QUOTED_EN.finditer(sentence):
        content = match.group(1)
        if not is_english_sentence(content):
            continue
        if match.start() > pos:
            yield sentence[pos:match.start()], "pl"
        yield content, "en"
        pos = match.end()
        found = True
    if found:
        if pos < len(sentence):
            yield sentence[pos:], "pl"
    else:
        yield sentence, "en" if is_english_sentence(sentence) else "pl"


def prepare_fish_chunks(text: str, lang: str = "pl", max_len: int = 155) -> list[tuple[str, str]]:
    """Return (speech-only-text, detected-language) without editing the displayed text.

    English sentences are kept as English; for mixed Polish text, a small
    overrideable lexicon provides Polish phonetic hints for embedded names.
    """
    from voice_clone import split_tts_text  # existing app chunker

    if lang not in ("pl", "en"):
        raise ValueError("Niewspierany język Fish")
    text = normalize_character_names_for_speech(text, lang)
    parts = []
    for sentence in SENTENCE_BREAK.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        for span, detected in _language_spans(sentence, lang):
            span = span.strip().lstrip(',;: ').strip()
            if not re.search(r'\w', span):
                continue
            spoken = normalize_for_speech(span, detected)
            if detected == "pl":
                spoken = phonetic_english_names(spoken)
            for chunk in split_tts_text(spoken, max_len=max_len):
                if chunk:
                    parts.append((chunk, detected))
    return parts
