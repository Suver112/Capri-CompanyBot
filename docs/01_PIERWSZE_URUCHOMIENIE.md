# Pierwsze uruchomienie Capri CompanyBot

## Wymagania

- Windows 10 lub 11, system 64-bitowy.
- Połączenie internetowe do pierwszego pobrania zależności i modeli.
- Wolne miejsce na modele: wielkość zależy od wybranego LLM, STT i Fish; przygotuj zapas liczony w gigabajtach.
- Ilość RAM/VRAM zależna od modelu. Cięższy Bielik i Fish Vulkan mogą nakładać zużycie pamięci.
- Dostęp do mikrofonu dla funkcji STT i uprawnienia Windows do wykonywania zatwierdzonych działań agenta.

## Instalacja

1. Pobierz `Capri_Setup.exe` z Releases (jeśli jest dostępny).
2. Zamknij wcześniejszą Capri, jeżeli jest uruchomiona.
3. Wybierz model konwersacji: Qwen 3.5 2B / 4B / 9B lub Bielik 11B (zgodnie z ofertą instalatora).
4. Wybierz składniki STT. Parakeet może być preinstalowany przez instalator; Whisper small i Silero VAD mogą wymagać pierwszego pobrania.
5. Jeśli korzystasz z Fish S2.cpp GPU, zaakceptuj warunki dostawcy wag, wybierz backend (Vulkan zwykle uniwersalny, CUDA opcjonalnie dla zgodnej NVIDII), a następnie wariant wag.
6. Pozwól instalatorowi dokończyć konfigurację i testy komponentów. Komunikat „gotowe” nie gwarantuje bezbłędnej pracy wszystkich konfiguracji GPU.
7. Uruchom Capri i sprawdź wpisywanie wiadomości, mikrofon i odtwarzanie głosu.

## Pierwsze ustawienia

W menu ustawień przejdź przez **Ogólne**, **Mózg**, **Osobowość i pamięć**, **Nasłuch (STT)**, **Głos**, **Wygląd**, **Agent i pulpit**, **Wydajność / optymalizacje**. Na początku zalecane jest pozostawienie fabrycznej adaptacji kontekstu i oszczędzania zasobów.

Przy pracy na laptopie lub komputerze z niewielkim VRAM wybierz lżejszy model. Jeśli syntezator i LLM rywalizują o zasoby, możesz zmienić backend, wariant kwantyzacji albo czas utrzymywania modelu Ollama w pamięci.

## Skróty

- `Alt+Q` — pokaż / ukryj okno Capri.
- `Ctrl+Alt+V` — uruchom / zatrzymaj mikrofon.
- `Ctrl+Alt+X` — minimalizuj Capri.

Skróty globalne wymagają poprawnej rejestracji przez Windows; inna aplikacja może je przejąć.

## Aktualizacja

Uruchom nowy oficjalny instalator. Przed aktualizacją zakończ Capri i zabezpiecz ustawienia profilu, jeśli mają szczególną wartość. Modele są pobierane niezależnie, dlatego aktualizacja aplikacji nie musi ponownie pobierać wszystkich wag.

Gdy instalacja nie kończy etapu konfiguracji, otwórz logi i uruchom pozycję **Napraw Capri** z menu Start, jeśli jest dostępna. Zobacz [Rozwiązywanie problemów](08_PROBLEMY.md).
