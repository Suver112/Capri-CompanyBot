"""Polish first-person voice consistency for the fictional Capri character.

We do not transform third-person descriptions (e.g. "Johnny zrobił") and
never modify quoted code or users' input. Model prompting remains primary.
"""
from __future__ import annotations
import re

# A first-person Polish past-tense masculine verb has an unambiguous -łem/-łem
# suffix. Feminine first-person replaces it with -łam (robiłem -> robiłam).
PAST_FIRST_MASC = re.compile(r"(?iu)\b([a-ząćęłńóśźż]+)łem\b")
CONDITIONAL_FIRST_MASC = re.compile(r"(?iu)\b([a-ząćęłńóśźż]+)łbym\b")

# 'Jestem X' uses a masculine adjective, not a masculine conjugated verb.
# The list stays deliberately conservative (avoid 'jestem wielkim fanem', etc.).
_PREDICATES = {
    'gotowy': 'gotowa', 'pewny': 'pewna', 'zadowolony': 'zadowolona',
    'zmęczony': 'zmęczona', 'wściekły': 'wściekła', 'zły': 'zła',
    'dumny': 'dumna', 'szczęśliwy': 'szczęśliwa', 'spokojny': 'spokojna',
    'zaskoczony': 'zaskoczona', 'zagubiony': 'zagubiona',
    'ciekawy': 'ciekawa', 'zdziwiony': 'zdziwiona',
    'dobry': 'dobra', 'głupi': 'głupia', 'głodny': 'głodna',
    'przygotowany': 'przygotowana', 'wycofany': 'wycofana',
}
_STATE = re.compile(r"(?iu)\b(jestem|bywam|byłam|czuję się|czuje sie|czułam się)\s+(" + '|'.join(_PREDICATES) + r")\b")

def _same_case(old: str, target: str) -> str:
    if old.isupper(): return target.upper()
    if old[:1].isupper(): return target.capitalize()
    return target

def feminine_first_person(text: str) -> str:
    """Correct an unambiguously masculine first-person self-reference."""
    if not isinstance(text, str) or not text: return text
    def past(m):
        target = m.group(1) + 'łam'
        return _same_case(m.group(0), target)
    def conditional(m):
        if m.group(0).casefold() == 'mógłbym':
            return _same_case(m.group(0), 'mogłabym')
        target = m.group(1) + 'łabym'
        return _same_case(m.group(0), target)
    def pred(m):
        return m.group(1) + ' ' + _same_case(m.group(2), _PREDICATES[m.group(2).casefold()])
    text = PAST_FIRST_MASC.sub(past, text)
    text = CONDITIONAL_FIRST_MASC.sub(conditional, text)
    return _STATE.sub(pred, text)

def needs_feminine_repair(text: str) -> bool:
    return isinstance(text, str) and feminine_first_person(text) != text
