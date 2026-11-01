# Wygląd, avatar, tryb Mini i skróty — Capri CompanyBot

## Motywy

Capri zawiera style **Basic**, **Holocall** oraz **Silverhand**. Wygląd można zmienić w zakładce **Wygląd**. Holocall jest przewidziany jako domyślny dla nowych profili. Kolory ramki, wskaźników i animacji dopasowują się do motywu.

## Avatar

Domyślna grafika znajduje się w `src/assets/default_avatar.png` i została wygenerowana przy użyciu ChatGPT dla projektu Capri. Aplikacja renderuje ją w okrągłym obszarze z maską, tak aby włosy wypełniały przestrzeń, a dolna krawędź tułowia nie wyglądała jak odcięta naklejka. Nie należy osadzać w repozytorium przypadkowych zrzutów ekranu zamiast właściwego PNG.

## Animacje

Pierścienie i elementy HUD-u powinny reagować na realne odtwarzanie dźwięku, a nie jedynie na rozpoczęcie generowania tekstu. Intensywność i płynność mogą zależeć od motywu oraz ustawień oszczędzania zasobów.

## Mini

Tryb Mini zmniejsza przestrzeń roboczą. Po wyjściu Capri powinna przywrócić właściwy widok i zaznaczenie poprzedniej zakładki. Jeśli pokazuje czat przy zaznaczonych ustawieniach, jest to błąd do zgłoszenia.

## Skróty globalne

| Skrót | Działanie |
|---|---|
| `Alt+Q` | Pokaż lub ukryj okno |
| `Ctrl+Alt+V` | Włącz lub wyłącz mikrofon |
| `Ctrl+Alt+X` | Minimalizuj Capri |

Po reinstalacji Windows może pokazywać starą miniaturę `Capri.ico` lub `Capri.exe` przez pamięć podręczną ikon. Przed ponownym budowaniem sprawdź zasoby w gotowym EXE oraz odepnij i ponownie przypnij skrót. Ikona systemowa „C” jest odrębna od grafiki awatara wewnątrz aplikacji.
