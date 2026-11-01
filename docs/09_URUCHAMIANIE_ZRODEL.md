# Capri CompanyBot — uruchomienie kodu źródłowego

## Zakres repozytorium

Repozytorium zawiera kod aplikacji, nie proces budowania Windows. Nie dostarcza `Capri_Setup.exe`, definicji PyInstaller, gotowych silników głosowych ani wag modeli. To instrukcja **uruchomienia Pythona bez kompilacji EXE**.

## Wymagania

- Windows 10/11 x64 i Python 3.11.
- Lokalna Ollama (lub skonfigurowane zgodne API) oraz pobrany model rozmowy.
- Dla mikrofonu: sprawne urządzenie wejściowe i odpowiednie modele STT.
- Dla Fish S2.cpp: zewnętrznie przygotowany silnik i zgodne wagi, z poszanowaniem warunków licencji Fish.
- W niektórych funkcjach opcjonalnych niezbędne są dodatkowe biblioteki systemowe / Python.

## Kroki

W terminalu PowerShell, w katalogu repozytorium:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Zainstaluj osobno Ollamę, pobierz model (`ollama list` wyświetla zainstalowane modele) i skonfiguruj go w ustawieniach aplikacji. Następnie:

```powershell
.\.venv\Scripts\python.exe src/main.py
```

**Uwaga:** `requirements.txt` zawiera podstawowe zależności. Nie instaluje wszystkich opcjonalnych usług i modeli: Fish, Parakeet, IVONA, Spotify i agent mogą wymagać dodatkowej konfiguracji. Nie jest to zapewnienie, że wszystkie funkcje zadziałają bez przygotowania środowiska.

## Gdzie szukać pomocy

[Podręcznik](02_PODRECZNIK.md) · [Modele i pamięć](03_MODELE_I_PAMIEC.md) · [Głos Fish](04_GLOS.md) · [Problemy](08_PROBLEMY.md).
