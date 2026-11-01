# Pełny podręcznik Capri CompanyBot

## 1. Rozmowa

Wpisz wiadomość w polu czatu lub uruchom mikrofon. Capri powinna korzystać z historii bieżącego dialogu, np. rozumieć odpowiedź „tak” na poprzednie pytanie lub zareagować na żart zapowiedziany we wcześniejszej wiadomości. To zachowanie zależy od modelu i limitu kontekstu, a nie każda odpowiedź będzie idealna.

Przycisk **Stop** przerywa bieżące zadanie aplikacji w zakresie obsługiwanym przez wybrany silnik; przerwanie odtwarzania nie zawsze natychmiast kończy żądanie przetwarzane już przez serwer zewnętrzny. **Wyczyść** usuwa bieżącą historię interfejsu; nie jest to polecenie usunięcia wszystkich plików profilu ani całej pamięci zapisanej na dysku.

## 2. Mózg

Wybór modelu lokalnego (Qwen / Bielik) określa szybkość, zużycie pamięci oraz jakość wypowiedzi. Ollama musi działać, a wybrany model musi być pobrany. Jeżeli model nie odpowiada, sprawdź usługę lokalną `127.0.0.1:11434` i aktualnie wybrany tag modelu.

## 3. Głos

W zakładce **Głos** wybierz silnik, głośność, próbki referencyjne i ewentualny profil emocji. Fish S2.cpp może generować głos lokalnie, korzystając z własnej biblioteki referencyjnej. Opcjonalny głos Windows, IVONA, Piper lub API zewnętrzne mogą wymagać odrębnych zależności i konfiguracji.

**Tekst do wypowiedzenia** służy do ręcznego odsłuchu wybranego zdania. To nie jest wiadomość konwersacyjna do LLM. Auto STT próbek wymaga sprawnego rozpoznawania mowy, a nieprawidłowa transkrypcja może istotnie pogorszyć wymowę Fish.

## 4. Nasłuch

Sprawdź wybrane urządzenie nagrywania, zezwolenie Windows i model STT. Parakeet i Whisper mają różne wymagania; w przypadku błędów przetestuj drugi silnik lub wybierz mikrofon jawnie.

## 5. Osobowość i pamięć

Capri jest zadziorna i energiczna, ale zwykła rozmowa nie powinna automatycznie wywoływać złości. Funkcje pamięci przechowują kontekst i niektóre informacje między rozmowami. Informacje fabularne są odrębne od faktów o użytkowniku. Jeśli model myli osoby z fabuły z rozmówcą, zgłoś przykładowy dialog bez danych prywatnych.

## 6. Wygląd

Dostępne motywy obejmują **Basic**, **Holocall** i **Silverhand**. W trybie Mini niektóre elementy są ukrywane dla oszczędności miejsca. Domyślny awatar jest grafiką, a jego animacje reagują na stan mówienia i motyw. Możesz wybrać własne materiały w odpowiednich ustawieniach, jeśli są obsługiwane przez bieżący wygląd.

## 7. Agent PC i media

Capri może rozpoznawać polecenia otwierania aplikacji, gier, kart przeglądarki i sterowania mediami. Odmiany i typowe literówki nazw mogą być mapowane na właściwy program (np. „Cyberpanka”, „ligunię”). Agent powinien respektować mechanizm zgody i ograniczenia dostępu do plików; działa tylko po włączeniu odpowiedniej funkcji.

Spotify wymaga indywidualnego połączenia konta / autoryzacji. Samo używanie Capri nie nadaje dostępu do kont użytkownika.

## 8. Optymalizacja

Adaptacyjny kontekst, krótsze utrzymywanie Ollamy i oszczędzanie zasobów w bezczynności są domyślnie włączane w nowych profilach. Zachowanie na istniejących profilach może zależeć od wcześniejszych ręcznych ustawień. Jeśli komputer się zawiesza, sprawdź równoległe obciążenie RAM/VRAM przez Bielik/Qwen, Fish i STT.

## 9. Logi i naprawa

Logi instalacji, syntezatora i diagnostyki znajdują się w profilach Capri w `%LOCALAPPDATA%` i ustawieniach profilu. Ich podstawowe lokalizacje i kroki diagnozy opisano w [Problemach](08_PROBLEMY.md).
