[🇬🇧 Switch to English](README.md)

<div align="center">

# CAPRI
### CompanyBot

**Twoja głosowa towarzyszka pulpitu. Z charakterem.**

**Wersja 0.1.1 · Wczesny dostęp · Windows**

[**Pobierz Capri**](https://github.com/Suver112/Capri-CompanyBot/releases/tag/Pre-Release) · [**Kod źródłowy**](src/) · [**Zgłoś problem**](https://github.com/Suver112/Capri-CompanyBot/issues)

</div>

> [!IMPORTANT]
> **Nieoficjalny projekt fanowski inspirowany uniwersum Cyberpunk.** Capri CompanyBot nie jest produktem CD PROJEKT RED, nie jest przez tę firmę autoryzowana, wspierana ani z nią powiązana. Prawa do odpowiednich postaci, nazw i znaków towarowych należą do ich właścicieli. [Zasady twórczości fanowskiej CD PROJEKT RED](https://www.cdprojektred.com/pl/fan-content).

---

## Czym jest Capri CompanyBot?

**Capri CompanyBot** to niezależna aplikacja desktopowa łącząca konwersacyjną AI, interakcję głosową, pamięć rozmów oraz interfejs inspirowany stylistyką cyberpunkową. Projekt skupia się na ekspresyjnej osobowości, lokalnym przetwarzaniu AI i wybranych działaniach na komputerze.

Capri jest rozwijana jako projekt **wczesnego dostępu**. Obsługa poszczególnych funkcji zależy od konfiguracji, wybranego modelu, silników mowy, sprzętu i usług zewnętrznych.

## Funkcje

| Obszar | Możliwości |
| --- | --- |
| **Rozmowa z AI** | Lokalne modele przez Ollamę, w tym Qwen i Bielik; opcjonalnie zewnętrzne API |
| **Kontekst i osobowość** | Rozmowy wieloturowe, lokalna pamięć, charakter i reakcje emocjonalne |
| **Rozpoznawanie mowy (STT)** | Obsługiwane konfiguracje oparte na Whisper lub Parakeet |
| **Synteza mowy (TTS)** | Fish S2.cpp i opcjonalne silniki głosowe; próbki referencyjne |
| **Interfejs** | Motywy Basic, Holocall i Silverhand, awatar i tryb Mini |
| **Sterowanie komputerem** | Wybrane działania w programach, grach, przeglądarce i multimediach |
| **Integracje** | Opcjonalna obsługa Spotify i innych usług |

> [!NOTE]
> Niektóre funkcje wymagają pobrania modeli, instalacji dodatkowych komponentów lub samodzielnego skonfigurowania usług. Przyspieszenie sprzętowe nie jest gwarantowane na każdym komputerze. **W wydaniu 0.1.1 nie ma gotowego backendu CUDA.**

## Pobieranie i instalacja

**System:** Windows 10 lub 11. Dostępność funkcji lokalnej AI zależy od pamięci, procesora, karty graficznej i wybranego modelu.

1. Otwórz [**Capri 0.1.1 — Wczesny dostęp**](https://github.com/Suver112/Capri-CompanyBot/releases/tag/Pre-Release).
2. Pobierz plik `Capri_Setup.exe` z sekcji **Assets**.
3. Uruchom instalator i skonfiguruj modele, rozpoznawanie mowy i syntezę głosu według potrzeb.

Jeżeli Windows lub oprogramowanie zabezpieczające wyświetli ostrzeżenie, sprawdź źródło pobrania i podpis/sumę kontrolną pliku. Nie wyłączaj zabezpieczeń bez zweryfikowania pliku.

**[Informacje o wydaniu i znanych problemach — EN / PL](docs/13_WYDANIE_0_1_1.md)**

Kod źródłowy jest dostępny w katalogu [`src/`](src/). Repozytorium nie zastępuje gotowego instalatora i nie zawiera wszystkich zewnętrznych modeli ani wag Fish.

## Uruchomienie z kodu źródłowego

Dla osób samodzielnie konfigurujących środowisko Windows.

**Podstawowe wymagania:** Windows 10/11, Python 3.11 oraz [Ollama](https://ollama.com/) dla lokalnych modeli językowych.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/main.py
```

Modele Ollama, silniki STT i TTS oraz ewentualne klucze API wymagają odrębnej konfiguracji. Samo zainstalowanie zależności Pythona **nie instaluje** Fish S2.cpp ani jego wag.

## Najczęstsze pytania

**Czy Capri jest darmowa?**  
Aplikacja jest udostępniana bezpłatnie. Niektóre zewnętrzne API lub usługi mogą naliczać opłaty zgodnie z własnymi warunkami.

**Czy działa bez internetu?**  
Wybrane funkcje lokalne mogą działać offline po wcześniejszym pobraniu i skonfigurowaniu modeli. Usługi online, Spotify i pobieranie modeli wymagają połączenia z internetem.

**Czy potrzebuję karty NVIDIA?**  
Nie. Dostępne backendy zależą od sprzętu i sterowników. Wydanie 0.1.1 nie zawiera gotowej obsługi CUDA, a dostępność Vulkan i innych metod przyspieszania może się różnić.

**Gdzie zgłaszać problemy?**  
W [GitHub Issues](https://github.com/Suver112/Capri-CompanyBot/issues). Dołącz wersję Capri, opis problemu, kroki jego odtworzenia oraz niezbędne, zanonimizowane logi.

## Dokumentacja i współpraca

- [Zgłoś błąd lub zaproponuj funkcję](https://github.com/Suver112/Capri-CompanyBot/issues)
- [Zasady współpracy](CONTRIBUTING.md)
- [Zgłaszanie problemów bezpieczeństwa](SECURITY.md)
- [Informacje o komponentach zewnętrznych](THIRD_PARTY_NOTICES.md)

**Nie publikuj kluczy API, prywatnych rozmów, danych osobowych ani całych profili użytkownika w zgłoszeniach.**

## Informacje prawne i autorstwo

Capri CompanyBot jest **niezależnym, nieoficjalnym projektem fanowskim** i nie jest powiązana z CD PROJEKT RED.

Grafiki Capri zostały wygenerowane przy użyciu **ChatGPT**. Zgodnie z oświadczeniem twórcy **dołączony głos Capri jest w pełni syntetyczny**: próbkę referencyjną wygenerowano w Fish Audio bez wykorzystania nagrań ani głosu prawdziwej osoby.

Kod projektu udostępniono na warunkach [GNU GPL v3](LICENSE). Biblioteki, silniki, modele, wagi i materiały zewnętrzne podlegają własnym licencjom. W szczególności licencja kodu Capri **nie oznacza**, że wagi Fish S2-Pro są objęte GPL. Szczegóły: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

<div align="center">

**Capri CompanyBot · 0.1.1 — Wczesny dostęp**

*Projekt fanowski · Niezależny · Niepowiązany z CD PROJEKT RED*

</div>
