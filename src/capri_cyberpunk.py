"""Original Cyberpunk 2077 launch banter; triggered only AFTER agent tool result.

Never treats mentions or factual questions as permission to start a program.
A launcher acknowledgment is not proof the game process started.
"""
from __future__ import annotations
from collections import deque
import random
import re
import unicodedata

_RECENT = deque(maxlen=14)
_FIRST_DIRECT = True

# Short dialogue-only lines; no stage directions, fake launch confirmations or voice tags.
DIRECT = (
    'Hehe, robi się! Rozjebmy Arasakę!!',
    'Night City? To trzymaj nerwy na wodzy.',
    'Okej. Tylko tym razem nie ufaj pierwszemu fixerowi.',
    'Dobra, wracamy do miasta, które nigdy nie śpi.',
    'Arasaka chyba jeszcze nie wie, co ją czeka.',
    'Jestem. Co dziś popsujemy w Night City?',
    'Neon, chrom i same złe decyzje. Uwielbiam to.',
    'Tylko nie mów, że znowu zaufasz Dexowi.',
    'Zacznijmy od czegoś prostego. Przeżyjmy pierwszą godzinę.',
    'Oby Johnny miał dziś mniej do powiedzenia ode mnie.',
    'Miasto marzeń. Głównie cudzych koszmarów.',
    'Night City ma jedną zasadę: żadnych darmowych przysług.',
    'Korporacje już zacierają ręce. Jak zawsze.',
    'Nie każdy problem załatwia się spluwą. Ale spróbować można.',
    'Słyszałeś? To chyba kolejny plan skazany na porażkę.',
    'Ciekawe, ile dziś kosztuje cudze sumienie.',
    'Dobra, V. Czas sprawdzić, komu można nie ufać.',
    'Piękne miasto. Szkoda, że zbudowane na trupach.',
    'W Night City nawet cisza ma sponsora.',
    'Jeśli zobaczysz logo Arasaki, wiesz, w którą stronę nie iść.',
    'Nie ma tu dobrych zakończeń. Są tylko mniej bolesne.',
    'Chrom nie naprawi charakteru. Ale wygląda nieźle.',
    'Dobra. Sprawdźmy, czy jeszcze pamiętasz, jak się strzela.',
    'Mam złe przeczucia. Czyli standardowy wtorek w Night City.',
    'Każda legenda kiedyś była czyimś głupim pomysłem.',
    'Nie szukaj świętych w tym mieście. Szkoda czasu.',
    'No to jazda. Byle nie skończyć jako czyjaś wiadomość w shardzie.',
    'Znowu Night City? Dobra, uznaję to za dobry gust.',
    'Pamiętaj: eddie to nie wszystko. Chociaż spróbuj powiedzieć to fixerom.',
    'Będzie głośno. A potem pewnie bardzo cicho.',
    'W mieście pełnym implantów najbardziej brakuje mózgów.',
    'Nie oddawaj swojego życia korporacjom za parę eddies.',
    'Jak zacznie pachnieć zdradą, to pewnie właśnie zaczęła się misja.',
    'Miej oczy otwarte. Night City uwielbia naiwnych.',
    'Zastanawiam się, ilu ludziom dziś coś obiecano. I ilu to przeżyje.',
    'Dobra. Zobaczmy, jak długo potrwa ten spokój.',
    'Dex ma nowy plan? To ja już szykuję kondolencje.',
    'Johnny, przesuń się. Dzisiaj ja komentuję tę katastrofę.',
    'V, odłóż spluwę. Dobra, żartowałam, weź dwie.',
    'Nie ufam ludziom z Konpeki Plaza. Mają za drogie uśmiechy.',
    'Arasaka znowu rozdaje obietnice. Sprawdź datę ważności.',
    'Najpierw robota, potem rachunek. Nikt tu nie płaci za sumienie.',
    'Netrunnerzy mają sekrety. Fixerzy mają cenniki.',
    'Uważaj na Pacificę. Tam nawet cisza robi cię w konia.',
    'Znowu naprawiamy cudze życie? Naszego przecież nie ruszamy.',
    'W Dogtown uśmiech to zwykle ostrzeżenie.',
    'Adam Smasher. Nawet nazwisko brzmi jak zła diagnoza.',
    'Znasz Night City. Kiedy robi się spokojnie, ktoś kłamie.',
    'Nie szukaj bohaterów. Poszukaj najpierw wyjścia.',
    'Hej, Jackie. Oby tym razem los był dla ciebie łaskawszy.',
    'Ulice pamiętają więcej niż ludzie. I mniej wybaczają.',
    'Rozwalmy korpo plan, zanim korpo rozwali nasz.',
    'Za dużo chromu, za mało rozsądku. W sam raz.',
    'Tak, wiem. Znowu jedziemy ratować świat, którego nie stać na ratunek.',
    'Wyłącz radio. Chcę usłyszeć, jak Arasaka panikuje.',
    'Braindance? Dziękuję, własnych traum mam wystarczająco.',
    'Jeśli fixer mówi „prosta robota”, od razu licz amunicję.',
    'Jestem ciekawa, kto pierwszy dzisiaj wbije nam nóż w plecy.',
    'Night City sprzedaje marzenia. Drobny druk zawiera pogrzeb.',
    'Okej, V. Tym razem nie daj się wrobić w cudzy dramat.',
    'Hej! Nie mów mi, że znów zignorujesz Takemurę.',
    'Są miejsca, do których nie wraca się po zmroku. Tu to całe miasto.',
    'Nie każda legenda zasługuje na pomnik. Niektóre na ostrzeżenie.',
    'Kiedyś też wierzyłam w szczęśliwe zakończenia. Przeszło mi.',
    'No dalej. Zróbmy coś, czego korporacje będą żałować.',
)

WISH = (
    'Zagrałbyś w Cyberpunka? No to chyba znam plan na wieczór.',
    'Tęsknisz za Night City? Nie dziwię się. Trochę.',
    'Znów cię ciągnie do neonów i złych decyzji? Rozumiem.',
    'Mówisz Cyberpunk, a ja już słyszę kłopoty.',
    'Długo cię nie było w Night City. Miasto raczej nie zatęskniło.',
    'Och, chcesz wrócić do V.? Cóż, są gorsze pomysły.',
    'Jeśli masz ochotę na Cyberpunka, to nie będę cię powstrzymywać.',
    'Dobra. Zobaczmy, czy Night City jeszcze nas pamięta.',
    'Wrócić do miasta, które zżera własnych bohaterów? Brzmi jak plan.',
    'Niektórzy marzą o wakacjach. Ty o Dogtown. Ciekawe.',
    'Miałeś spokojny dzień? To pora go sobie zepsuć w Night City.',
    'Przyznaj, po prostu brakowało ci Johnny’ego. No, może nie.',
    'Chcesz wrócić? Nawet nie pytam, ile niedokończonych misji zostawiłeś.',
    'Zagrałbyś? To sprawdź, czy V jeszcze umie wyjść z kłopotów.',
    'Tęsknisz za Jackie? Czasem też mi go brakuje.',
    'Wrócimy do Night City. Tylko nie obiecuj, że będzie spokojnie.',
    'Masz ochotę na chaos i dobre radio? Rozsądny wybór.',
    'Już cię ciągnie do Dogtown? Odważnie. Albo nierozsądnie.',
    'No tak, jeden spokojny wieczór to najwyraźniej za dużo.',
)



def _fold(text: str) -> str:
    s = unicodedata.normalize('NFKD', str(text or '').casefold().replace('ł', 'l'))
    return re.sub(r'\s+', ' ', ''.join(c for c in s if not unicodedata.combining(c))).strip()


def is_cyberpunk_title(name: str) -> bool:
    s = _fold(name)
    # Recognized installed game must match a distinctive title, not just 'punk'.
    return bool(re.search(r'\b(?:cyber\s?punk|cyberpank|cyberpanka|cyberpunka)\b', s))


def launch_context(request: str) -> str | None:
    s = _fold(request)
    if not re.search(r'\b(?:cyber\s?punk(?:a)?|cyberpank(?:a)?|cp\s?2077)\b', s):
        return None
    if re.search(r'\b(?:nie|nigdy|zamiast|bez)\s+(?:odpal|wlacz|uruchom|zagraj|pogram|chce)\w*', s):
        return None
    if re.search(r'\b(?:zagr[a-z]*bym|pogr[a-z]*bym|chcialbym|mam ochote|chce sobie pograc|zagra[l]?bym)\b', s):
        return 'wish'
    return 'direct'


def launch_quip(request: str, actual_title: str, *, rng=None) -> str:
    """Only a confirmed tool ACTION may call this function, never a plain mention."""
    if not is_cyberpunk_title(actual_title):
        return ''
    context = launch_context(request)
    if context is None:
        return ''
    pool = WISH if context == 'wish' else DIRECT
    global _FIRST_DIRECT
    if context == 'direct' and _FIRST_DIRECT:
        selected = DIRECT[0]
        _FIRST_DIRECT = False
    else:
        candidates = [v for v in pool if v not in _RECENT] or list(pool)
        selected = (rng or random).choice(candidates)
    _RECENT.append(selected)
    return selected
