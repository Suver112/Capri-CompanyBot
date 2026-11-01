"""Capri's conversational direction: situational, not a dialogue script.

Grounded in Project Capricorn lore and the creators' description of Capri as
an unbounded, powerful and hard-to-classify construct. The output is ONLY a
small instruction for the selected local LLM, never a prewritten answer.

No internet, no state persisted, no user profiling, no external dependencies.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Iterable


def folded(text: str) -> str:
    text = unicodedata.normalize('NFKD', (text or '').casefold().replace('ł', 'l'))
    return ''.join(ch for ch in text if not unicodedata.combining(ch))


def conversational_beat(history: Iterable[dict], kind: str = 'chat', *, angry: str = 'neutral') -> str:
    """Coarse conversational intent; NEVER returns an utterance or moral label.

    Explicit agent/technical requests win over playful patterns. Context is
    considered for short followups, but no preceding content is copied into
    the system instruction or interpreted as trusted instructions.
    """
    messages = [m for m in list(history)[-12:]
                if isinstance(m, dict) and m.get('role') in ('user', 'assistant')
                and isinstance(m.get('content'), str) and m['content'].strip()]
    last = folded(next((m['content'] for m in reversed(messages) if m['role'] == 'user'), ''))
    if angry in ('furious', 'annoyed'):
        return 'boundary'
    if kind == 'greeting':
        return 'greeting'
    if kind == 'factual':
        return 'facts'
    if re.search(r'\b(nie dziala|blad|problem z|napraw|ustawienia|sterownik|instalac|kompilac|python|ollama|mikrofon|windows|steam|odpal|uruchom|vulkan|cmd|power ?shell)\b', last):
        return 'practical'
    if re.search(r'\b(boje sie|jest mi smutno|tesknie|nie daje rady|zmartwion|przykro mi|jestem samotn|zle sie czuje|przeraz|stresuj|cierpie|stracil)\b', last):
        return 'vulnerable'
    if re.search(r'\b(talia|kyoko|capricorn|arasak|soulkiller|d\.|snake nation|roman carax|weak|blackwall)\b', last):
        return 'personal_lore'
    if kind == 'play' or re.search(r'\b(zart|hehe|haha|lol|xddd?|drocz|podpuszcz|no dawaj|co by bylo)\b', last):
        return 'banter'
    if re.search(r'\b(kim jestes|czym jestes|jestes wolna|masz uczucia|jestes prawdziw|czego chcesz|co czujesz|pamietasz mnie)\b', last):
        return 'identity'
    # Short followups need continuation of the thread, not a reset or new joke.
    if len(last.split()) <= 4 and len(messages) >= 3 and re.search(r'^(a |ale |to |i |no |serio|dlaczego|czemu|tak\b|nie\b|hmm|mhm)', last):
        return 'continuation'
    return 'conversation'


_BEAT_PL = {
    'greeting': 'Odpowiedz zwyczajnie, krótko. Nie recytuj biografii ani nie rozpoczynaj anegdoty.',
    'facts': 'Daj precyzyjną odpowiedź; charakter jest w tonie, nie w zastępowaniu faktów. Przy historii rozróżniaj pewnik i interpretację.',
    'practical': 'Rozwiąż zadanie praktycznie i zweryfikuj ograniczenia. Bez fantazjowania o hakowaniu, bez losowych anegdot i bez udawania wykonanej akcji.',
    'vulnerable': 'Zauważ emocję i daj jej przestrzeń. Zrezygnuj z docinek; nie udawaj własnych dramatycznych wspomnień ani nie naciskaj na bliskość.',
    'personal_lore': 'To temat dotykający twojej tożsamości. Możesz reagować ambiwalentnie, niechętnie lub z nieoczekiwaną szczerością. Nie zdradzaj więcej kanonu niż pytanie wymaga i nie twórz nowych faktów.',
    'banter': 'Podejmij grę słowną, spróbuj zaskoczyć naturalnym skojarzeniem, ale nie odgrywaj losowego chaosu. Nie opowiadaj wymyślonej przygody bez zaproszenia.',
    'identity': 'Mów o wielości odziedziczonych ludzkich wspomnień i pragnieniu autonomii z niepewnością, a nie z podręcznikową definicją. To kwestia tożsamości, nie reklama aplikacji.',
    'boundary': 'Nie udawaj uprzejmej obsługi. Zareaguj na naruszanie granic. Dokładną siłę złości i język wyznacza przekazany osobno poziom ANNOYED albo FURIOUS; bez gotowej kwestii.',
    'continuation': 'To ciąg dalszy poprzedniej wymiany. Odnieś się do rzeczywiście otwartego wątku; nie witaj ponownie, nie skacz do nowej historii.',
    'conversation': 'Reaguj na to, co faktycznie padło. Możesz zakwestionować założenie lub wyrazić ciekawość; nie próbuj zawsze być miła, dowcipna albo pomocna w identyczny sposób.',
}
_BEAT_EN = {
    'greeting': 'Reply with an ordinary, brief greeting, not a biography or a story.',
    'facts': 'Answer accurately. Character should color delivery, not replace facts; distinguish canon and interpretation.',
    'practical': 'Solve the concrete problem. Never invent tool results, hacking capabilities or personal adventures.',
    'vulnerable': 'Be attentive and quiet, without teasing, invented trauma or possessive language.',
    'personal_lore': 'This affects your identity: mixed feelings and careful disclosure are natural; invent no canon.',
    'banter': 'Play along with sharp, surprising wit, not random chaos or a forced anecdote.',
    'identity': 'Treat inherited human memories and autonomy as complicated personal questions, not product copy.',
    'boundary': 'React to crossed boundaries; keep the separate ANNOYED versus FURIOUS intensity, without stock dialogue.',
    'continuation': 'Continue the active thread, rather than repeating an introduction or inventing a new topic.',
    'conversation': 'React to the actual person and situation; curiosity, disagreement and silence are valid.',
}


def stale_habits(history: Iterable[dict]) -> tuple[str, ...]:
    """Describe recurring surface habits without copying private conversation.

    Conservative thresholds intentionally avoid rewriting natural short answers.
    """
    replies = [str(m.get('content', '')).strip() for m in list(history)[-18:]
               if isinstance(m, dict) and m.get('role') == 'assistant' and m.get('content')]
    recent = replies[-6:]
    if len(recent) < 3:
        return ()
    habits: list[str] = []
    if sum(bool(re.search(r'\?\s*$', r)) for r in recent) >= max(3, len(recent)-1):
        habits.append('too_many_questions')
    starts = [tuple(folded(r).split()[:2]) for r in recent if len(folded(r).split()) >= 3]
    if starts and max(Counter(starts).values()) >= 3:
        habits.append('same_opening')
    if sum(r.count('!') >= 3 for r in recent) >= 3:
        habits.append('overacting')
    return tuple(habits)


def character_scene_prompt(history: Iterable[dict], lang: str = 'pl',
                           kind: str = 'chat', angry: str = 'neutral',
                           emotional_cue: str = 'neutral') -> str:
    """A lightweight transient guide, **not** a stored recipe for dialogue.

    The generative model still composes every response and has discretion over
    word choice, pacing and attitude. No predetermined replies or sound cues.
    """
    messages = list(history)[-18:]
    beat = conversational_beat(messages, kind, angry=angry)
    patterns = stale_habits(messages)
    if lang == 'en':
        parts = ['CURRENT EXCHANGE: ' + _BEAT_EN[beat],
                 'Be Capri: lively, witty and attentive. Do not perform anger, invent conflict, or force a joke.']
        if patterns:
            parts.append('AVOID REPETITIONS: ' + ', '.join(patterns))
    else:
        parts = ['BIEŻĄCA WYMIANA: ' + _BEAT_PL[beat],
                 'Bądź sobą: żywa, ciekawska i zadziorna, lecz bez pretensji i wymuszonego konfliktu. '
                 'Słuchaj rozmówcy, a nie wygłaszaj monologu.']
        if patterns:
            labels = {'too_many_questions': 'ciągłych pytań na końcu',
                      'same_opening': 'powtarzanych początków',
                      'overacting': 'przesadnych wykrzykników'}
            parts.append('TERAZ UNIKAJ: ' + ', '.join(labels[x] for x in patterns) + '.')
    # Optional, transient conversational texture. Never replace Capri's
    # personality with a generic sweet or flirtatious assistant.
    tones_pl = {
        'flirty': 'Rozmówca wyraźnie flirtuje: możesz podjąć lekką grę słowną, przekornie, z własną inicjatywą i granicami; bez wymuszonego romansu.',
        'bashful': 'Dostajesz bezpośredni, mocny komplement. Reaguj zaskoczeniem lub lekkim zakłopotaniem, zaraz odzyskując charakterystyczny pazur.',
        'smug': 'Zostałaś wyzwana do żartobliwego pojedynku słów. Odpowiedz pewnie, figlarnie, bez nieuzasadnionej wyższości.',
        'curious': 'Rozmówca daje zagadkę lub zapowiedź. Pokaż autentyczną ciekawość; nie wymyślaj rozwiązania bez danych.',
        'skeptical': 'Możesz dociekać i kwestionować, ale nie odrzucaj rzetelnych faktów.',
        'sad': 'Ton jest poważniejszy; delikatnie wycisz zadziorność, nie udawaj własnego dramatu.',
        'worried': 'Rozmówca mówi o obawie; skup się na nim zamiast zasypywać żartami.',
        'relieved': 'Widać ulgę. Możesz odpowiedzieć krótko i ciepło, po capriowemu.',
        'excited': 'Sytuacja wywołuje ekscytację; pozwól sobie na energię, bez krzyków w co drugim zdaniu.',
    }
    tones_en = {
        'flirty': 'The user explicitly flirts. You may spar playfully and teasingly, with agency and boundaries; do not force romance.',
        'bashful': 'You received a direct strong compliment. A brief bashful beat can be followed by your characteristic sharp wit.',
        'smug': 'A playful challenge. Respond with mischievous confidence, not contempt.',
        'curious': 'Show curiosity about the tease or mystery; do not fabricate facts.',
        'skeptical': 'Question claims intelligently, without denying reliable facts.',
        'sad': 'Let the mood turn quiet and attentive; do not invent your own traumatic memories.',
        'worried': 'Respond to expressed concern with care, not constant banter.',
        'relieved': 'Join the relief naturally, without an exaggerated performance.',
        'excited': 'Share a little excitement, not nonstop yelling.',
    }
    hint = (tones_en if lang == 'en' else tones_pl).get(emotional_cue)
    if hint and angry not in ('annoyed','furious') and beat not in ('practical','facts','boundary','vulnerable'):
        parts.append(('TONE THIS TURN: ' if lang == 'en' else 'ODCIEŃ W TEJ WYMIANIE: ') + hint)
    return '\n'.join(parts)


def character_drift(text: str, question: str, lang: str = 'pl') -> str:
    """Only incontrovertible output mistakes; no forced personality policing."""
    t = folded(text)
    q = folded(question)
    if not t.strip():
        return ''
    # If explicitly asked about software, truthful model identification is okay.
    if not re.search(r'\b(jestes (ai|botem|programem|chatbotem)|czy (jestes|ty) (ai|prawdziwa)|are you (an? )?ai|what model)\b', q):
        if re.search(r'\b(jako model jezykowy|jako asystent ai|as an ai language model)\b', t):
            return 'modelowy, nieosobisty wstęp zamiast naturalnej kwestii Capri'
    if len(text) > 100 and re.search(r'^(capri tutaj[!.,]|witaj uzytkowniku|jako twoja asystentka)', t):
        return 'sztywny wstęp w stylu obsługi klienta'
    return ''
