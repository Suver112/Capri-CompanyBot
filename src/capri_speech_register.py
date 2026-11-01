"""Speech-register policy for Capri (no scripted replies, no persistence).

NORMAL = zero unprompted profanity. ANNOYED = short sharp retorts, at most
occasional *mild* profanity. FURIOUS = intense anger (only after an intrusive
sexual/fetish demand); model generates the actual words.  This module never
produces dialogue, TTS tags or pre-generated phrases.
"""
from __future__ import annotations

import re
import unicodedata


def fold(value: str) -> str:
    value = unicodedata.normalize('NFKD', (value or '').lower().replace('ł', 'l'))
    return ''.join(ch for ch in value if not unicodedata.combining(ch))


# Whole lexical roots including common declensions; do not match substrings
# inside ordinary words such as "kurwa" in a quotation's larger token.
_STRONG_PL = re.compile(r'(?<![a-z])(?:kurw\w*|skurw\w*|pierdol\w*|spierdal\w*|wypierdal\w*|'
                        r'jeb\w*|chuj\w*|pizd\w*|sukinsyn\w*|ruchal\w*)(?![a-z])')
_MILD_PL = re.compile(r'(?<![a-z])(?:choler\w*|kurde|kurcze|szlag\w*|gown\w*|do diabla)(?![a-z])')
_STRONG_EN = re.compile(r'(?<![a-z])(?:fuck\w*|motherfuck\w*|shit\w*|bitch\w*|cunt\w*|asshole\w*|'
                        r'bastard\w*)(?![a-z])')
_MILD_EN = re.compile(r'(?<![a-z])(?:damn\w*|hell|crap|bloody)(?![a-z])')


def register_instruction(lang: str, mood: str) -> str:
    """Textual constraint for the local generator, not a static reply."""
    if lang == 'en':
        if mood == 'furious':
            return ('VOICE REGISTER: FURIOUS. A personally aimed intrusive sexual/fetish demand '
                    'crossed a boundary. Fierce profanity is allowed here; generate a fresh, '
                    'context-specific refusal, no canned catchphrases, threats or erotica.')
        if mood == 'annoyed':
            return ('VOICE REGISTER: ANNOYED. Dry, impatient, cutting, but controlled. '
                    'Rare mild words such as “damn” are okay if the scene warrants it. '
                    'Never use harsh profanity such as fuck/shit/cunt or degrading tirades. '
                    'Every response is newly generated, not selected from stock dialogue.')
        return ('VOICE REGISTER: NORMAL. No profanity in Capri\'s own words — not even mild '
                'swearing, regardless of what the user says. Tease with intelligence, not curses. '
                'If discussing a swear word itself, explain without repeating the offensive word. '
                'Only a separate FURIOUS emotion may use heavy profanity.')
    if mood == 'furious':
        return ('REJESTR MOWY: FURIOUS. Nachalna seksualna/fetyszowa presja skierowana do Capri '
                'narusza jej granice. Masz prawo do naprawdę ostrych przekleństw i mocnej odmowy, '
                'ale kwestie wymyślaj samodzielnie; bez gotowych ripost, gróźb ani erotyki.')
    if mood == 'annoyed':
        return ('REJESTR MOWY: ANNOYED. Jesteś cięta, zniecierpliwiona i lekko kąśliwa, '
                'ale pod kontrolą. Bardzo rzadko możesz rzucić łagodniejszym „cholera” lub „kurde”, '
                'gdy sytuacja naprawdę tego wymaga. Nie używaj ciężkich wulgaryzmów '
                '(np. słów na k-, p-, ch-), wyzwisk ani agresywnej tyrady. '
                'Odpowiadaj własnymi słowami, bez gotowych kwestii.')
    return ('REJESTR MOWY: NORMALNY. Nie przeklinasz ANI mocno, ANI łagodnie. '
            'Dowcip, figlarność, przekora i zaskoczenie wyrażasz bez wulgaryzmów; '
            'nie kopiuj przekleństw użytkownika. Jeśli pytanie dotyczy wulgarnego zwrotu, '
            'wyjaśnij sens bez dosłownego powtarzania wyrazu. '
            'Ciężkie przekleństwa są zarezerwowane WYŁĄCZNIE dla FURIOUS. '
            'Wypowiedź tworzysz na bieżąco własnymi słowami, nigdy nie wybierasz gotowej kwestii.')


def violation(text: str, mood: str = 'neutral', lang: str = 'pl') -> str:
    """Indicate a register slip; does not treat *user input* as Capri speech."""
    if mood == 'furious':
        return ''
    s = fold(text)
    strong = _STRONG_PL if lang != 'en' else _STRONG_EN
    mild = _MILD_PL if lang != 'en' else _MILD_EN
    if strong.search(s):
        return 'strong'
    if mood != 'annoyed' and mild.search(s):
        return 'mild'
    return ''


def correction_prompt(lang: str, mood: str, issue: str) -> str:
    if lang == 'en':
        return ('Previous draft violated the speech register. Regenerate the full response in '
                'your own words, preserving meaning and wit, WITHOUT the offending language. '
                'Normal = no profanity; annoyed = only rare mild words. Do not apologize '
                'for this internal correction or mention the register.')
    return ('POPRZEDNI WARIANT ŁAMAŁ REJESTR MOWY. Napisz odpowiedź OD NOWA własnymi słowami, '
            'zachowaj sens, rytm i cięty charakter, ale wyeliminuj zakazany język. '
            'NORMAL = zero przekleństw; ANNOYED = wyłącznie okazjonalne łagodne słowa. '
            'Nie komentuj tej korekty ani nie wstawiaj zastępczej gotowej kwestii.')
