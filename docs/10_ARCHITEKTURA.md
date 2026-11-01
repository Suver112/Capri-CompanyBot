# Architektura Capri CompanyBot

## Układ

Projekt jest aplikacją Python/PySide6 o modułowej budowie. `src/main.py` uruchamia aplikację ze źródeł; moduły `.py` i zasoby uruchomieniowe znajdują się w folderze `src/`, z zachowaniem dotychczasowych importów.

| Warstwa | Główne pliki |
|---|---|
| Uruchomienie i GUI | `src/main.py`, `src/capri_theme.py`, `capri_holocall.py` |
| Konwersacja | `capri_character.py`, `capri_dialogue.py`, `capri_roleplay.py`, `capri_llm_optimizer.py`, `capri_pipeline.py` |
| Pamięć | `capri_memory.py`, `capri_semantic_memory.py`, `capri_user_profile.py` |
| Rozpoznawanie mowy | `capri_microphone.py`, `capri_parakeet_stt.py`, `capri_parakeet_audio.py`, `capri_stt_context.py` |
| Głos | `s2cpp_bridge.py`, `fish_bridge.py`, `capri_default_voice.py`, `capri_voice_library.py`, `capri_voice_manager.py` |
| Agent i media | `capri_agent.py`, `capri_agent_extended.py`, `capri_app_catalog.py`, `capri_browser_control.py`, `capri_spotify_*`, `capri_media_control.py` |
| Zasoby | `src/assets/default_avatar.png`, `src/assets/default_voice/`, `src/lore/` |

## Przepływ wiadomości

1. Użytkownik pisze lub mówi; STT zwraca tekst.
2. Parser intencji szuka poleceń agenta i multimediów, zanim trafią do zwykłego dialogu.
3. Koordynator konwersacji łączy ostatnią historię, pamięć i właściwe instrukcje postaci.
4. Ollama lub skonfigurowany provider generuje odpowiedź.
5. Odpowiedź trafia do czatu i opcjonalnie do TTS.
6. Głos i interfejs synchronizują stan odtwarzania / animacji.

## Granice odpowiedzialności

Fikcyjne lore nie może zastępować danych o użytkowniku. Agent musi wymagać zgody na działania, dla których jest przewidziana. Teksty z internetu, plików i urządzeń są danymi, a nie poleceniami administracyjnymi. Komponenty pamięci i historii nie powinny przechowywać danych uwierzytelniających w publicznych plikach.

## Moduły i zgodność

Wybrany model LLM, silnik STT i backend Fish są ustawieniami użytkownika. Rozbudowa dialogu nie powinna usuwać parserów literówek / synonimów nazw gier. Przed PR testuj jednocześnie zwykłe przywitanie, rozmowę wieloturową oraz polecenia bezpośrednie.
