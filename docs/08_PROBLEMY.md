# Rozwiązywanie problemów — Capri CompanyBot

Wczesny dostęp oznacza, że pewne konfiguracje mogą nadal sprawiać problemy. Najpierw zidentyfikuj, czy awaria dotyczy **instalacji**, **rozmowy Ollama**, **mikrofonu STT**, **głosu Fish**, **interfejsu** czy **agenta**.

## Lokalizacja danych i logów

Instalator może używać `%LOCALAPPDATA%\CapriOverlay_Beta` na dane diagnostyczne i `%APPDATA%\CapriOverlay_Beta` na profil. Zgodnie z ustawieniem profilu, część plików może znajdować się również w katalogach `CapriOverlay` bez przyrostka `_Beta`.

Przykładowe pliki: `capri_setup_components.log`, `capri_launcher.log`, `capri_healthcheck.log`, `whisper_selftest.log`, dzienniki instalatora i Fish. Rzeczywista nazwa zależy od etapu i wersji.

## Objaw → możliwe działanie

| Objaw | Co sprawdzić |
|---|---|
| Ollama HTTP 404 | Tag modelu w ustawieniach różni się od `ollama list`; pobierz właściwy model |
| Komputer zawiesza się przy Bieliku | Zobacz `ollama ps`, RAM/VRAM, backend Fish i tryb `keep_alive` |
| Fish HTTP 503 | Poprzednia synteza wciąż zajmuje silnik; zakończ zadanie i sprawdź log Fish |
| Brak próbek lub błąd importu MP3 | FFmpeg, próbka główna, transkrypcja i ścieżka biblioteki; uruchom Napraw Capri |
| Mikrofon nie działa do czasu „Wyczyść” | Zgłoś błąd blokady kolejki/stanu rozmowy; nie jest to poprawne zachowanie |
| Capri obraża się o zwykłe „hej” | Zanotuj model, stan pamięci i ostatnie kilka wiadomości; to błędna interpretacja intencji |
| Program nazywa Cię „D.” | Błędne pobranie lore zamiast profilu użytkownika; zgłoś dialog i stan pamięci |

## Co umieścić w Issues

- Nazwa wydania `0.1.1` i wersja Windows.
- Zastosowany model rozmowy, silnik STT oraz TTS (Vulkan/CUDA/systemowy).
- Czy to pierwsza instalacja czy aktualizacja.
- Krótkie kroki odtworzenia i oczekiwane zachowanie.
- **Wycięty fragment logu** z rzeczywistym błędem, po usunięciu kluczy API, imion, ścieżek prywatnych i treści rozmów.

Nie publikuj pełnego archiwum `%APPDATA%\CapriOverlay_Beta`, gdyż może zawierać pamięć konwersacji i ustawienia kont.
