# Prywatność i dane — Capri CompanyBot

Capri działa przede wszystkim lokalnie z wykorzystaniem usług na własnym komputerze (np. Ollama i Fish S2.cpp). **Nie każda funkcja jest całkowicie offline**: pobieranie modeli, Spotify, dostęp do stron internetowych i opcjonalne zewnętrzne API wymagają połączeń sieciowych i podlegają politykom danych ich dostawców.

## Dane lokalne

Konfiguracja i pamięć konwersacji mogą być przechowywane w `%APPDATA%\CapriOverlay_Beta`, a logi i pobrane komponenty w `%LOCALAPPDATA%\CapriOverlay_Beta`. Dokładna lokalizacja zależy od ustawionego profilu. Biblioteka próbek może zawierać lokalne nagrania użytkownika oraz ich transkrypcje.

## Uprawnienia

Agent PC nie powinien wykonywać operacji z uprawnieniami, których użytkownik nie zatwierdził. Dostęp do mikrofonu nadaje Windows. Połączenie Spotify i inne integracje należy konfigurować osobno, na własnych kontach.

## Zasady publikowania logów

Zanim zgłosisz błąd publicznie, usuń klucze API, ścieżki domowe, nazwy kont, treści rozmów, tokeny Spotify, fragmenty nagrań i inne dane prywatne. Nie wrzucaj plików profilu ani bazy SQLite do repozytorium.

## Usuwanie danych

Odinstalowanie EXE i usunięcie modeli w Ollamie to odrębne działania. Przed ręcznym usunięciem profilu wykonaj kopię konfiguracji i materiałów, które chcesz zachować. Usunięcie plików lokalnych nie usuwa automatycznie danych przechowywanych przez zewnętrznych dostawców.
