# Capri 0.1.3 — aktualizacja źródeł (w przygotowaniu)

Ta gałąź służy do synchronizacji **pełnego kodu 0.1.3** z paczki
`Capri_0.1.3_PELNE_ZRODLA_POPRAWKA_SSL_GITHUB.zip`.

**Uwaga:** dopóki pełne pliki `src/` nie zostaną dodane i przejdą testów,
nie należy scalać tej gałęzi z `main`. Sam numer 0.1.3 w metadanych
nie świadczy o aktualności całego programu.

## Zasady od teraz

1. Wszystkie zmiany kodu najpierw przechodzą przez gałąź TEST.
2. Uruchamianie testowe odbywa się przez `URUCHOM_CAPRI_TEST.bat`,
   bez PyInstaller i bez instalatora.
3. Przed scaleniem: kontrola diff, testy regresji, testy Windows.
4. EXE, instalator i publiczny GitHub Release wyłącznie na wyraźne życzenie
   po zaakceptowaniu testów.

## Źródła 0.1.3

Paczka zawiera już `CAPRI_URUCHOM_ZRODLA.ps1`,
`URUCHOM_CAPRI_BEZ_INSTALATORA.bat` i `capri_exe.py`.
Pliki należy umieścić razem w `src/`, zachowując strukturę zasobów,
skryptów PowerShell i zależności. Nie przesyłać prywatnych logów, tokenów
ani modeli pobranych przez użytkownika.
