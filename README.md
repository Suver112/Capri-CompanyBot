<div align="center">

# CAPRI
### CompanyBot

**Twoja głosowa towarzyszka pulpitu. Z charakterem.**

**Wersja 0.1.1 · Wczesny dostęp · Windows**

[**Pobieranie**](https://github.com/Suver112/Capri-CompanyBot/releases) · [**Kod źródłowy**](src/) · [**Zgłoś błąd**](https://github.com/Suver112/Capri-CompanyBot/issues)

</div>

> [!IMPORTANT]
> **Nieoficjalny projekt fanowski inspirowany uniwersum Cyberpunk.** Capri CompanyBot nie jest tworzona, autoryzowana, wspierana ani powiązana z **CD PROJEKT RED**. Prawa do świata, postaci, nazw i znaków towarowych należą do odpowiednich właścicieli. [Zasady twórczości fanowskiej CD PROJEKT RED](https://www.cdprojektred.com/pl/fan-content).

---

## Czym jest Capri CompanyBot?

**Capri CompanyBot** to niezależna aplikacja desktopowa, która łączy rozmowę z AI, głos, pamięć konwersacji i cyberpunkowy interfejs. Jej celem jest bycie ekspresyjną, zadziorną towarzyszką komputera — nie tylko kolejnym oknem czatu.

Projekt stawia na lokalne modele, kontekst rozmowy oraz możliwość wykonywania wybranych działań na komputerze. Poszczególne funkcje zależą od konfiguracji i podłączonych usług.

### Możliwości

| | |
|---|---|
| **Rozmowa z AI** | Lokalne modele przez Ollamę, m.in. Qwen i Bielik; opcjonalne API |
| **Pamięć i kontekst** | Wieloturowe rozmowy, osobowość, emocje i lokalna pamięć |
| **Rozpoznawanie mowy** | Whisper / Parakeet, zależnie od konfiguracji |
| **Synteza głosu** | Fish S2.cpp i opcjonalne silniki TTS; biblioteka próbek referencyjnych |
| **Wygląd** | Motywy Basic, Holocall i Silverhand, awatar oraz tryb Mini |
| **Sterowanie komputerem** | Polecenia dotyczące programów, gier, przeglądarki i multimediów |
| **Muzyka** | Opcjonalna integracja ze Spotify i sterowanie odtwarzaniem |

> Capri jest w fazie **wczesnego dostępu**. Nie wszystkie integracje i silniki działają na każdym komputerze, a część wymaga osobnej instalacji lub konfiguracji.

## Pobierz Capri

Gotowe instalatory Windows są udostępniane osobno, w zakładce **[Releases](https://github.com/Suver112/Capri-CompanyBot/releases)**, po opublikowaniu danego wydania.

1. Otwórz **Releases** i wybierz najnowsze *opublikowane* wydanie.
2. Pobierz `Capri_Setup.exe`, jeżeli jest dołączony.
3. Uruchom instalator i skonfiguruj wybrany model oraz głos.

**Repozytorium zawiera kod źródłowy w folderze [`src/`](src/)**, a nie gotowy instalator, pliki EXE, binaria Fish czy wagi modeli. Dostępność i zawartość wydań mogą się różnić od stanu kodu na gałęzi `main`.

## Uruchomienie ze źródeł

Dla osób, które chcą samodzielnie uruchomić aplikację na Windows:

**Wymagania:** Windows 10/11, Python 3.11 oraz — dla lokalnych modeli rozmowy — [Ollama](https://ollama.com/).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/main.py
```

Modele Ollama, back-endy syntezy i rozpoznawania mowy oraz ewentualne klucze API konfiguruje się oddzielnie. Samo `pip install` nie instaluje silnika Fish S2.cpp ani jego wag.

## Najczęstsze pytania

**Czy Capri jest darmowa?**  
Projekt jest udostępniany bez opłaty za samą aplikację. Zewnętrzne API i niektóre usługi mogą mieć własne opłaty.

**Czy działa bez internetu?**  
Lokalna rozmowa może działać bez połączenia po wcześniejszym przygotowaniu modeli i silników. Pobieranie modeli, Spotify i usługi online wymagają internetu.

**Czy trzeba mieć kartę NVIDIA?**  
Nie. Dostępne możliwości przyspieszenia zależą od wybranego silnika, sterowników i sprzętu. Nie każda konfiguracja obsługuje wszystkie backendy.

**Czy Capri jest oficjalną postacią lub produktem CD PROJEKT RED?**  
Nie. To niezależny, nieoficjalny projekt fanowski.

## Dokumentacja, błędy i współpraca

- [Zgłoś błąd lub zaproponuj funkcję](https://github.com/Suver112/Capri-CompanyBot/issues)
- [Zasady współpracy](CONTRIBUTING.md)
- [Zgłaszanie problemów bezpieczeństwa](SECURITY.md)
- [English README](README.en.md)

Przy zgłaszaniu błędów nie publikuj kluczy API, prywatnych rozmów ani plików lokalnego profilu.

## Informacje prawne

**Capri CompanyBot jest niezależnym projektem fanowskim.** Nie jest autoryzowany ani wspierany przez CD PROJEKT RED lub inne podmioty będące właścicielami wykorzystanych marek i technologii.

Grafiki Capri zostały wygenerowane przy użyciu **ChatGPT**. Syntetyczna próbka referencyjna głosu Capri została wygenerowana przy użyciu **Fish Audio**; zgodnie z oświadczeniem twórcy nie opiera się na głosie ani nagraniach rzeczywistej osoby.

W repozytorium znajduje się plik [LICENSE](LICENSE) zawierający **GNU GPL v3**. Zewnętrzne biblioteki, silniki, modele, wagi i inne materiały zachowują **odrębne warunki licencyjne** — w szczególności nie należy utożsamiać licencji kodu Capri z prawami do wag Fish S2-Pro. Szczegóły: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

<div align="center">

**Capri CompanyBot · 0.1.1 — Wczesny dostęp**

*Fan-made. Independent. Not affiliated with CD PROJEKT RED.*

</div>
