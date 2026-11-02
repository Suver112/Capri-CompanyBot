# Capri CompanyBot 0.1.1 — Early Access / Wczesny dostęp

[**🇵🇱 Przejdź do wersji polskiej**](#polski) · [**🇬🇧 Read in English**](#english)

<a id="english"></a>

## 🇬🇧 English

**Release date:** November 1, 2026  
**Platform:** Windows 10 / 11  
**Release channel:** Early Access (pre-release)

### Overview

Capri CompanyBot 0.1.1 is an early-access release of a voice-enabled desktop AI companion. It combines conversational AI, speech recognition and synthesis, configurable local models, and selected desktop interactions.

This build is intended for early adopters and testers. Some features may require additional configuration, and compatibility is not yet assured across all supported hardware.

### Changes in this release

- **Installer reliability:** Several issues affecting the installation process have been addressed.
- **Processor compatibility:** Changes intended to improve operation on processors without AVX2 or AVX-512 have been introduced. **Compatibility on these CPUs has not yet been confirmed through testing.**

### Known issues and limitations

- **Long conversations:** Extended chat sessions may cause instability or prevent further messages from being processed. Clearing the conversation history can sometimes restore operation, but it is not a guaranteed fix.
- **Voice output quality:** The default synthesized voice may sound unnatural or inconsistent on some configurations. Voice and reference-sample settings can be adjusted in the application.
- **AI response quality:** Responses may be inaccurate, inconsistent, or out of character. Performance depends on the selected language model, configuration, and conversation context.
- **Misleading status messages:** The application may occasionally report an error even when an operation has completed. Verify the outcome before retrying; do not assume every error notification is harmless.
- **GPU backend support:** **This release does not include a ready-to-use CUDA backend.** Other acceleration paths depend on the installed components, drivers, and hardware.
- **Installation and security software:** Antivirus tools or Windows security protections may interfere with installation. Only download the installer from the official release page and verify its provenance before taking action on a warning.

### Download and setup

1. Download [**Capri_Setup.exe**](https://github.com/Suver112/Capri-CompanyBot/releases/download/Pre-Release/Capri_Setup.exe) from the [official 0.1.1 release](https://github.com/Suver112/Capri-CompanyBot/releases/tag/Pre-Release).
2. Run the installer on Windows and follow its configuration steps.
3. Select and configure the desired local AI model and speech engines. Availability of individual backends may vary by system.

**Installer SHA-256:** `45a8b8119a7ce35fa4de8ce716567fc485b0f4d58de3392b9de1fb4f2705f2ac`

**Optional online speech:** If using the Fish Audio API, obtain a key from [Fish Audio](https://fish.audio/) and configure the relevant Fish voice option in Capri. This requires an internet connection; access, free-tier availability, limits, and pricing are determined by Fish Audio and may change.

**Source code:** The current repository includes the application source in [`src/`](../src/). Source code and the published installer are distributed separately; the `main` branch may contain changes not included in this release.

### Feedback and legal notice

Please report reproducible problems through [GitHub Issues](https://github.com/Suver112/Capri-CompanyBot/issues). Include system details, the selected AI/STT/TTS backends, reproduction steps, and redacted logs. **Do not share private conversations or API credentials.**

Capri CompanyBot is an **independent, unofficial Cyberpunk-inspired fan project**. It is not developed, endorsed, or supported by CD PROJEKT RED. According to the creator, the included Capri voice is fully synthetic and was generated without recordings of a real person's voice. Third-party software and model weights remain subject to their own licenses; see [third-party notices](../THIRD_PARTY_NOTICES.md).

---

<a id="polski"></a>

## 🇵🇱 Polski

**Data wydania:** 1 listopada 2026 r.  
**Platforma:** Windows 10 / 11  
**Kanał wydania:** Wczesny dostęp (pre-release)

### Informacje o wydaniu

Capri CompanyBot 0.1.1 to wczesna wersja aplikacji AI do komunikacji głosowej i tekstowej na komputerze. Łączy rozmowy z modelami językowymi, rozpoznawanie i syntezę mowy, konfigurowalne modele lokalne oraz wybrane funkcje sterowania komputerem.

Wydanie jest przeznaczone dla wczesnych użytkowników i testerów. Niektóre funkcje wymagają dodatkowej konfiguracji, a zgodność ze wszystkimi konfiguracjami sprzętowymi nie została jeszcze potwierdzona.

### Zmiany w tej wersji

- **Stabilność instalatora:** Poprawiono kilka błędów związanych z instalacją aplikacji.
- **Zgodność z procesorami:** Wprowadzono zmiany mające umożliwić działanie na procesorach bez AVX2 lub AVX-512. **Skuteczność tych zmian na takich procesorach nie została jeszcze potwierdzona testami.**

### Znane problemy i ograniczenia

- **Długie rozmowy:** Po dłuższej konwersacji aplikacja może działać niestabilnie lub przestać przetwarzać wiadomości. Wyczyszczenie historii czatu czasami pomaga, ale nie gwarantuje rozwiązania problemu.
- **Jakość syntezy głosu:** Domyślny głos może brzmieć nienaturalnie lub niejednolicie. Ustawienia głosu i próbek referencyjnych można zmienić w aplikacji.
- **Jakość odpowiedzi AI:** Odpowiedzi mogą być błędne, niespójne lub niezgodne z charakterem postaci. Jakość zależy od modelu językowego, konfiguracji i kontekstu rozmowy.
- **Nieprawidłowe komunikaty:** Sporadycznie może pojawić się komunikat o błędzie mimo wykonania operacji. Przed ponowną próbą sprawdź rezultat działania; nie należy zakładać, że każdy komunikat jest fałszywy.
- **Obsługa GPU:** **Ta wersja nie zawiera gotowego backendu CUDA.** Działanie pozostałych metod przyspieszania zależy od zainstalowanych komponentów, sterowników i sprzętu.
- **Instalacja i zabezpieczenia:** Programy antywirusowe lub zabezpieczenia Windows mogą utrudniać instalację. Pobieraj plik wyłącznie z oficjalnej strony wydania i zweryfikuj jego pochodzenie, zanim podejmiesz działania związane z ostrzeżeniem.

### Pobieranie i konfiguracja

1. Pobierz [**Capri_Setup.exe**](https://github.com/Suver112/Capri-CompanyBot/releases/download/Pre-Release/Capri_Setup.exe) z [oficjalnego wydania 0.1.1](https://github.com/Suver112/Capri-CompanyBot/releases/tag/Pre-Release).
2. Uruchom instalator w systemie Windows i wykonaj instrukcje konfiguracji.
3. Wybierz model AI oraz silniki rozpoznawania i syntezy mowy. Dostępność poszczególnych backendów zależy od konfiguracji.

**Suma SHA-256 instalatora:** `45a8b8119a7ce35fa4de8ce716567fc485b0f4d58de3392b9de1fb4f2705f2ac`

**Opcjonalna synteza online:** Jeśli chcesz korzystać z API Fish Audio, uzyskaj klucz na stronie [Fish Audio](https://fish.audio/) i ustaw odpowiednią opcję głosową Fish w Capri. Wymagany jest internet. Dostępność darmowego planu, limity i ceny zależą od Fish Audio i mogą się zmieniać.

**Kod źródłowy:** Repozytorium zawiera kod aplikacji w katalogu [`src/`](../src/). Kod i instalator są publikowane osobno; gałąź `main` może zawierać zmiany, których nie ma w tym wydaniu.

### Zgłaszanie problemów i informacje prawne

Błędy można zgłaszać przez [GitHub Issues](https://github.com/Suver112/Capri-CompanyBot/issues). Podaj konfigurację sprzętową, wybrane silniki AI/STT/TTS, kroki odtworzenia problemu i zanonimizowane logi. **Nie publikuj prywatnych rozmów ani kluczy API.**

Capri CompanyBot to **niezależny, nieoficjalny projekt fanowski inspirowany uniwersum Cyberpunk**. Nie jest tworzony, autoryzowany ani wspierany przez CD PROJEKT RED. Zgodnie z oświadczeniem twórcy dołączony głos Capri jest w pełni syntetyczny i powstał bez wykorzystania nagrań głosu prawdziwej osoby. Oprogramowanie i wagi modeli innych twórców podlegają osobnym licencjom. Szczegóły: [informacje o komponentach zewnętrznych](../THIRD_PARTY_NOTICES.md).
