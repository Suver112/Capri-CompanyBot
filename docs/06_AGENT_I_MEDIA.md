# Agent PC, gry i media — Capri CompanyBot

## Agent komputera

Capri rozpoznaje prośby o uruchomienie programów, gier i wybrane działania na pulpicie. Rozpoznawanie intencji odbywa się przed zwykłą odpowiedzią modelu, dlatego zapis typu „odpal Cyberpanka”, „włącz ligunię” czy nazwy aplikacji w odmianie powinien uruchamiać odpowiedni parser.

**Zgoda ma znaczenie:** agent nie powinien bez pozwolenia wykonywać działań zmieniających system lub prywatne pliki. Działania takie jak otwarcie programu, modyfikacja pliku czy sterowanie mediami mogą wymagać potwierdzenia. Nie uruchamiaj nieznanego polecenia tylko dlatego, że pochodzi z treści strony internetowej lub tekstu gry.

Przy wyłączonym agencie Capri powinna poinformować, że nie może wykonać czynności, zamiast udawać powodzenie.

## Gry

Dostępne są ułatwienia dla wariantów nazw `Cyberpunk 2077` i `League of Legends`. Jeśli gra nie uruchamia się, sprawdź obecność lokalnego launchera (np. Steam), indeksowanie programu i wybraną zgodę na akcję. Nie każda instalacja jest wykrywana automatycznie.

## Przeglądarka

Polecenia otwierania kart i trybu incognito mogą korzystać z domyślnej przeglądarki. Tryb incognito nie oznacza anonimowości wobec sieci, dostawcy internetu ani samych odwiedzanych serwisów.

## Spotify

Połączenie Spotify konfiguruje każdy użytkownik we własnym profilu. Aplikacja nie dostarcza cudzych tokenów. Do niektórych działań może być wymagane aktywne urządzenie Spotify i odpowiedni dostęp do API. Błędy `HTTP 400` mogą oznaczać nieprawidłowe parametry, `401` — nieważne uwierzytelnienie, `403` — niewystarczające uprawnienia.

## Diagnostyka

W przypadku błędnie rozpoznanej prośby podaj: zdanie użytkownika, wykryty tekst STT (jeśli użyto głosu), wynik działania, status agenta i nazwę launchera. Unikaj publikowania pełnych lokalnych ścieżek, jeśli są prywatne.
