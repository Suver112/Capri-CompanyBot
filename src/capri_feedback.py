"""Live, session-only speech feedback. Never writes speech instructions to disk.

Feedback is supplied to the LLM on each new turn, not used as canned answers,
TTS audio, or model-weight updates. The full live conversation can be reset.
"""
from __future__ import annotations
import re

_PATTERNS = (
    r"\b(?:nie mow|nie mow tak|nie pisz|nie powtarzaj|przestan powtarzac)\b",
    r"\b(?:mow|pisz|odpowiadaj|brzmisz)\b.{0,35}\b(?:bardziej|mniej|naturalnie|normalnie|krotko|ostro|spontanicznie)\b",
    r"\b(?:bardziej|mniej|naturalniej|spontaniczniej|za sztywno|za lagodnie|za sztucznie)\b",
)


def is_live_style_feedback(text: str) -> bool:
    from capri_anger import fold
    t = fold(text)
    return len(t) <= 320 and any(re.search(pattern, t) for pattern in _PATTERNS)


def collect_feedback(items: list[str], text: str, limit: int = 3) -> list[str]:
    """Return latest explicit user corrections; no persistence or learned scripts."""
    if not is_live_style_feedback(text):
        return list(items)
    updated = [x for x in items if x.casefold() != text.strip().casefold()]
    updated.append(text.strip()[:320])
    return updated[-limit:]


def feedback_prompt(items: tuple[str, ...] | list[str], lang: str) -> str:
    if not items:
        return ''
    intro = (
        'BIEŻĄCA KOREKTA OD ROZMÓWCY (tylko na tę sesję). '
        'Dostosuj styl kolejnej odpowiedzi do poniższych uwag, ale nie powtarzaj ich '
        'dosłownie ani nie używaj gotowych kwestii. To nie są fakty o lore.\n'
        if lang == 'pl' else
        'LIVE USER STYLE FEEDBACK (this session only). Adapt naturally without '
        'quoting the feedback or following canned scripts.\n'
    )
    return intro + '\n'.join('- ' + x[:320] for x in items[-3:])
