# Mikrofon i STT — Capri CompanyBot

## Konfiguracja

Otwórz ustawienia **Nasłuch (STT)**. Wybierz źródło audio i silnik Parakeet lub Whisper. Udziel systemowi Windows dostępu do mikrofonu. Spróbuj krótkiego nagrania w cichym pomieszczeniu.

`Ctrl+Alt+V` przełącza mikrofon, jeśli skrót został poprawnie zarejestrowany. Przycisk w aplikacji działa niezależnie od globalnej kombinacji. Funkcja wykrywania słów aktywujących może być włączana oddzielnie i nie wymaga osobnego silnika KWS.

## Gdy mikrofon nie reaguje

1. Sprawdź **Ustawienia Windows → Prywatność i zabezpieczenia → Mikrofon**.
2. Sprawdź w Capri wybrane urządzenie (w razie problemu wybierz jawnie, nie „domyślne”).
3. Upewnij się, że inne narzędzie nie zablokowało wejścia w trybie wyłącznym.
4. Zatrzymaj trwające przetwarzanie, odczekaj na koniec zadania i spróbuj ponownie.
5. Przełącz z Parakeet na Whisper lub odwrotnie, by odróżnić problem modelu od problemu nagrywania.
6. Jeśli mikrofon działa dopiero po **Wyczyść**, opisz to w Issues — to objaw blokady stanu rozmowy, nie poprawne zachowanie.

## Rozpoznawanie gier i nazw własnych

Funkcje kontekstowe pomagają przy typowych odmianach i literówkach nazw programów, gier czy poleceń. STT wciąż może źle rozpoznać słowa, dlatego w zgłoszeniu podaj *faktyczny tekst transkrypcji*, nie tylko to, co powiedziałeś do mikrofonu.

## Uwaga dotycząca prywatności

Nie dołączaj nagrań mikrofonu do publicznych Issues bez własnej decyzji. Logi z testów mogą zawierać lokalne ścieżki i fragmenty wypowiedzi; usuń je przed udostępnieniem.
