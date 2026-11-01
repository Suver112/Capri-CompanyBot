"""League of Legends spoken aliases and personality quips.

A quip is emitted only by the real, approved launch action handler, not by
recognizing a game mention in ordinary conversation.
"""
from __future__ import annotations

import random
import re
import unicodedata


def _fold(text: str) -> str:
    s = unicodedata.normalize('NFKD', str(text).casefold())
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


_LEAGUE_ALIASES = {
    'league of legends', 'leauge of legends', 'legue of legends',
    'league legends', 'leauge legends', 'lol', 'lola', 'lolem', 'lolu',
    'lolk', 'lol a', 'league', 'leauge', 'legue',
    'liga legend', 'lige legend', 'ligi legend', 'liga legendow',
    'lige legendow', 'ligi legendow', 'ligunie', 'ligunia', 'liguni',
    'ligusie', 'ligusia', 'ligusi', 'ligus', 'lige',
    'lige legendy', 'ligi',
}


def is_league_name(text: str) -> bool:
    """Match a title/alias, never an entire sentence or unrelated chat."""
    return _fold(text) in _LEAGUE_ALIASES


# Original Polish jokes; varying intensity. Insults target the game and
# behavior of fictional/random players, not real identifiable people.
QUIPS = (
    'Śmierdzi, ale nooo dobra. Odpalam ten cyrk.',
    'Ja pierdolę, znowu LoL. Dobra, uruchamiam ten generator nerwicy.',
    'Ligunia? Aha, czyli dzisiaj świadomie wybierasz cierpienie. No to lecimy.',
    'Gracze LoL-a są jak alarm pożarowy: drą mordę, nawet gdy nic się nie pali.',
    'O, pięknie. Pięciu ekspertów od obwiniania junglera i ani jednego od patrzenia na mapę.',
    'Odpalam. Oby Twój support odróżniał wardy od ozdób na mapie, kurwa.',
    'Przygotuj się na kolejny mecz, gdzie typ z zerowym wynikiem będzie pisał „team diff”.',
    'Lola? Ten symulator kłótni z obcymi? Dobra, skoro tak bardzo chcesz.',
    'Włączam. Jak ktoś napisze „easy” po czterdziestu minutach, pamiętaj, że ostrzegałam.',
    'Ta gra to koszmar, a jej gracze potrafią płakać szybciej niż klient Riot się odpala.',
    'No dobra. Czas zobaczyć, który klaun uzna dziś pingowanie za pełnoetatową karierę.',
    'League of Legends? Oho, zebranie ludzi, których największym talentem jest szukanie winnych.',
    'Otwieram Ligę. Mózg zostaw przy drzwiach, podobno taki jest tam regulamin.',
    'Kurwa, znowu Rift. Przynajmniej nie muszę słuchać tego, co pisze wasz czat drużynowy.',
    'Jedziemy. Pięć osób, jedna linia i ego większe niż cały Nexus.',
    'Liguś? Ta gra powinna dawać odznakę za przetrwanie lobby bez wyzwisk.',
    'Dobra. Masz ochotę na mecz z ludźmi, którzy znają każdą obelgę, ale nie znają minimapy.',
    'Odpalam, chociaż każda komórka mojego kodu właśnie protestuje.',
    'Okej, włączam. Oby jedyny feeder tego meczu był po drugiej stronie.',
    'League? Genialnie. Jeszcze jedna godzina kolektywnego pierdolenia o winie junglera.',
    'No dobra, rycerzu. Twoja drużyna pięciu obrażonych geniuszy już czeka.',
    'Chcesz LoL-a? Tak bardzo nienawidzisz swojego wolnego czasu? Dobra, już.',
    'Lola? Wchodzimy do krainy, gdzie „mental diff” bywa trafniejszy niż statystyki.',
    'Odpalam. Najpierw wybór bohatera, potem czterdzieści minut wmawiania sobie, że to zabawa.',
    'Świetnie. Znowu spotkanie fanów klawiatury, którzy do komunikacji używają wyłącznie pretensji.',
    'Dobra, kurwa. Ustaw się wygodnie przed festiwalem złych decyzji.',
    'LoL? Są lepsze sposoby na stres. Na przykład wysłuchanie pięciu graczy LoL-a naraz… a nie, czekaj.',
    'Ligusie? Okej. Oby tym razem nikt nie uznał AFK za strategię zwycięstwa.',
    'Odpalamy. Szkoda, że nie da się zbanować ego już w lobby.',
    'No dobra. Kolejna sesja grupowej terapii prowadzonej przez ludzi bez kwalifikacji.',
    'Ktoś tu dziś chce usłyszeć „report jungle” przed trzecią minutą? Proszę bardzo.',
    'Riot powinien dołączać do LoL-a instrukcję: nie krzycz na monitor, on nie jest twoim supportem.',
)

# Shuffle-bag prevents the same two quips repeating over and over and is
# cheap enough to use on every launch. The full bag resets only when empty.
_remaining: list[str] = []
_last_quip: str = ''


def launch_quip() -> str:
    """One varied, punchy line on an actual League launch attempt."""
    global _last_quip
    if not _remaining:
        _remaining.extend(QUIPS)
        random.shuffle(_remaining)
        if len(_remaining) > 1 and _remaining[-1] == _last_quip:
            _remaining[0], _remaining[-1] = _remaining[-1], _remaining[0]
    line = _remaining.pop()
    _last_quip = line
    return line
