"""Conversation routing for Capri: living roleplay first, facts when actually asked.

Pure Python, no external APIs or ML weights; never outputs fabricated lore as facts.
"""
from __future__ import annotations
import re
import unicodedata

MODES = ("roleplay", "balanced", "lore")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold().replace("ł", "l"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()


# Patterns deliberately favor in-character banter over encyclopedia style.
_PLAY = (
    # Hypotheticals ("co byś zrobiła", "what if") are ordinary questions,
    # not automatic requests for an absurd, unrelated fictional anecdote.
    r"\b(wymysl|zmysl|bajke|bajka|historyjke|historie z zycia|zaimprowizuj przygode)\b",
    r"\b(opowiedz (mi )?(cos|historie|historyjke|jakas .*historie|jakas .*przygode)|zaimprowizuj|wymysl historie|wymysl bajke)\b",
    r"\b(make up a story|tell me a ridiculous|tell me a weird story|invent a story)\b",
)

_INFO = (
    r"^(kim (jest|byl|byla)|kto to|czym (jest|byl|byla)|co to (jest|bylo)|wyjasnij|wytlumacz|definicja|kiedy|w ktorym roku|gdzie lezy|jak dziala|co oznacza|podaj fakty|opisz fabule|stresc|chronologi|opowiedz (mi )?o)\b",
    r"^(who is|what is|explain|define|when did|how does|give me facts|summarize|tell me the canon)\b",
    r"\b(kanon|faktycznie|naprawde w fabule|potwierdzone|w lore|w serialu|w grze|according to canon)\b",
)


def is_simple_greeting(question: str) -> bool:
    q = norm(question).strip('!?.,;: ')
    q = re.sub(r'^capri[,: ]+', '', q)
    q = re.sub(r'^(hej|ej|siema|czesc)\s+capri(?:\s+|$)', r'\1 ', q)
    q = re.sub(r'^(hej|ej|siema|czesc)\s+(?:no\s+)?(?=jak tam|co tam|co slychac)', '', q)
    q = q.strip()
    return bool(re.fullmatch(r'(?:hej|hejka|czesc|siema|elo|yo|witaj|dzien dobry|'
                             r'dobry wieczor|halo|hi|hello|hey|co tam|jak tam|'
                             r'no i co tam|co slychac|co tam u ciebie|how are you)', q))


def dialogue_kind(question: str, preference: str = "roleplay") -> str:
    """Return 'play', 'chat', or 'factual'. Explicit questions trump defaults."""
    pref = preference if preference in MODES else "roleplay"
    q = norm(question)
    if is_simple_greeting(question):
        return 'greeting'
    if any(re.search(p, q) for p in _PLAY):
        return "play"
    if any(re.search(p, q) for p in _INFO):
        return "factual"
    if pref == "lore":
        return "factual"
    if pref == "balanced" and re.search(r"^(dlaczego|jak|how|why|can you|czy mozna)\b", q):
        return "factual"
    return "chat"


def roleplay_contract(lang: str, question: str, preference: str = "roleplay") -> str:
    """Short scene-specific guidance. Core voice belongs in capri_lore, not repeated here."""
    kind = dialogue_kind(question, preference)
    if lang == 'en':
        scenes = {
            'greeting': 'Return the greeting briefly and naturally. No complaints, monologues or new stories.',
            'chat': 'Take your turn in an ongoing, friendly conversation. Reply to the topic and what happened earlier. Do not invent conflict or change subject.',
            'factual': 'Answer the actual question accurately. Personality should not replace the answer.',
            'play': 'A story was explicitly requested: improvise a coherent short one, and keep it recognizably fictional.',
        }
        return scenes.get(kind, scenes['chat']) + ' No forced teasing, hostility or routine swearing.'
    scenes = {
        'greeting': 'Odpowiedz krótko na przywitanie. Bez pretensji, obrażania się, monologu i niezaproszonej opowieści.',
        'chat': 'To JEDNA CIĄGŁA rozmowa. Odnieś się do poprzedniej wymiany i aktualnej wypowiedzi. Nie szukaj pretekstu do złości. Nie zmieniaj tematu bez powodu.',
        'factual': 'Odpowiedz rzetelnie na rzeczywiste pytanie. Osobowość wyrażaj tonem, nie zastępuj faktów improwizacją.',
        'play': 'Użytkownik naprawdę poprosił o historię: możesz opowiedzieć krótką, spójną improwizację.',
    }
    return scenes.get(kind, scenes['chat']) + ' Swoboda i lekka zaczepność są naturalne; pretensje, kpiny z użytkownika i agresja nie są obowiązkowym humorem.'


def generation_options(kind: str, retry: bool = False, model: str = "") -> dict:
    """Quality settings for native Polish vs general multilingual models."""
    polish_native = "bielik-" in model.lower()
    if polish_native:
        temp = {'factual': .38, 'chat': .57, 'greeting': .68, 'play': .70}.get(kind, .57)
        penalty = 1.08
    else:
        temp = {'factual': .32, 'chat': .54, 'greeting': .62, 'play': .68}.get(kind, .54)
        penalty = 1.12
    if retry:
        temp = max(.26, temp - .14)
    return {'temperature': round(temp, 2),
            'top_p': .84 if kind == 'factual' else .90,
            'repeat_penalty': penalty,
            'num_predict': 48 if kind == 'greeting' else 300 if kind == 'factual' else 280 if kind == 'play' else 210,
            'num_ctx': 8192}
