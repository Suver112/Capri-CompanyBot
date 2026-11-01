"""UI localization shared by settings, overlay, controls.

Translate only known UI chrome, never generated chat/user data or file paths.
"""
from __future__ import annotations

EN_UI = {'Ogólne': 'General', 'Mózg': 'Brain', 'Osobowość i pamięć': 'Personality & Memory', 'Nasłuch (STT)': 'Listening (STT)', 'Głos': 'Voice', 'Wygląd': 'Appearance', 'Agent i pulpit': 'PC Agent & Desktop', 'Wydajność • eksperymentalne': 'Performance • Experimental', 'WERSJA APLIKACJI': 'APP VERSION', 'LICENCJE I PRAWA AUTORSKIE': 'LICENSES & COPYRIGHT', 'INFORMACJE PRAWNE': 'LEGAL INFORMATION', 'PLIKI PROGRAMU': 'APP FILES', 'OTWÓRZ FOLDER CAPRI': 'OPEN CAPRI FOLDER', 'MODELE • INSTALACJA': 'MODEL DOWNLOAD', 'POBIERZ WYBRANY MODEL (OLLAMA)': 'DOWNLOAD SELECTED MODEL (OLLAMA)', 'ŹRÓDŁO MODELU': 'MODEL PROVIDER', 'Ollama • lokalnie (bez API)': 'Ollama • local (no API)', 'Zewnętrzne API': 'External API', 'API • DOSTAWCA': 'API • PROVIDER', 'API • WYBIERZ MODEL': 'API • SELECT MODEL', 'API • ENDPOINT ROZMOWY': 'API • CHAT ENDPOINT', 'API • WŁASNY MODEL': 'API • CUSTOM MODEL', 'API • KLUCZ ROZMOWY': 'API • CHAT KEY', 'API • ZAPIS': 'API • SAVE', 'API • BEZPIECZEŃSTWO': 'API • SECURITY', 'API • STATUS': 'API • STATUS', 'API • TEST': 'API • TEST', 'ZAPISZ API ROZMOWY I KLUCZ': 'SAVE CHAT API SETTINGS & KEY', 'USUŃ KLUCZ ROZMOWY': 'DELETE CHAT API KEY', 'TESTUJ POŁĄCZENIE API': 'TEST API CONNECTION', 'BETA: STRUMIENIOWANIE OLLAMA': 'BETA: OLLAMA STREAMING', 'BETA • ROZMOWA': 'BETA • CHAT', 'WYCZYŚĆ ROZMOWĘ / RESET': 'CLEAR CHAT / RESET', 'HISTORIA CZATU': 'CHAT HISTORY', 'PAMIĘĆ POPRZEDNICH ROZMÓW / LOCAL MEMORY': 'REMEMBER PAST CONVERSATIONS / LOCAL MEMORY', 'PAMIĘĆ CAPRI': 'CAPRI MEMORY', 'JAK MAM CI MÓWIĆ?': 'WHAT SHOULD I CALL YOU?', 'NAZWA KONTA': 'ACCOUNT NAME', 'WYKRYWAJ IMIĘ Z KONTA WINDOWS': 'DETECT NAME FROM WINDOWS ACCOUNT', 'PRZYWITAJ MNIE PRZY STARCIE (TAKŻE GŁOSEM)': 'GREET ME AT STARTUP (INCLUDING VOICE)', 'POWITANIE': 'STARTUP GREETING', 'ZEZWÓL NA IMIĘ W ZEWNĘTRZNYM API (AI / GŁOS)': 'ALLOW USER NAME IN EXTERNAL API (AI / VOICE)', 'PRYWATNOŚĆ API': 'API PRIVACY', 'ROZPOZNANA NAZWA': 'DETECTED NAME', 'ROZUMIENIE PODTEKSTU / KONTEKSTOWE EMOCJE': 'UNDERSTAND SUBTEXT / CONTEXTUAL EMOTIONS', 'CHARAKTER CAPRI': 'CAPRI PERSONALITY', 'PROAKTYWNE ZACZEPKI • PO 20 MIN BEZCZYNNOŚCI': 'PROACTIVE CHAT • AFTER 20 MIN IDLE', 'CAPRI • ZACHOWANIE': 'CAPRI • BEHAVIOR', 'BETA: PAMIĘĆ SEMANTYCZNA / EMBEDDINGGEMMA': 'BETA: SEMANTIC MEMORY / EMBEDDINGGEMMA', 'BETA • PAMIĘĆ': 'BETA • MEMORY', 'USUWANIE DANYCH': 'DELETE DATA', 'TRYB TESTOWY': 'TEST MODE', 'LLM • KONTEKST': 'LLM • CONTEXT', 'OLLAMA • VRAM': 'OLLAMA • VRAM', 'UI • BEZCZYNNOŚĆ': 'UI • IDLE', 'BEZPIECZNY POWRÓT': 'SAFE REVERT', 'ADAPTACYJNY KONTEKST • 4096 / 8192': 'ADAPTIVE CONTEXT • 4096 / 8192', 'ZWALNIAJ MODEL OLLAMA WCZEŚNIEJ • 3 MIN': 'UNLOAD OLLAMA EARLIER • 3 MIN', 'OSZCZĘDNE ANIMACJE W BEZCZYNNOŚCI': 'LOW-POWER IDLE ANIMATIONS', 'PRZYWRÓĆ SPRAWDZONĄ KONFIGURACJĘ • 1 KLIK': 'RESTORE TESTED SETTINGS • 1 CLICK', 'AGENT PC • DOSTĘP': 'PC AGENT • ACCESS', 'AGENT • VISION OLLAMA': 'AGENT • OLLAMA VISION', 'INTERNET • WYSZUKIWANIE': 'WEB • SEARCH', 'INTERNET • DIAGNOSTYKA': 'WEB • DIAGNOSTICS', 'DOSTĘP DO WYSZUKIWANIA W SIECI • TYLKO TA SESJA': 'ENABLE WEB SEARCH • THIS SESSION ONLY', 'SPRAWDŹ WYSZUKIWANIE HTTPS': 'TEST HTTPS SEARCH', 'UPRAWNIENIA FOLDERÓW': 'FOLDER PERMISSIONS', 'MUZYKA • SPOTIFY': 'MUSIC • SPOTIFY', 'POŁĄCZ SPOTIFY API • KONKRETNE UTWORY': 'CONNECT SPOTIFY API • TRACK PLAYBACK', 'SPOTIFY • STATUS': 'SPOTIFY • STATUS', 'DZIENNIK LOKALNY': 'LOCAL LOG', 'ŹRÓDŁO MIKROFONU': 'MICROPHONE SOURCE', 'ODŚWIEŻ': 'REFRESH', 'STAN URZĄDZENIA': 'DEVICE STATUS', 'TESTUJ WYBRANY MIKROFON': 'TEST SELECTED MICROPHONE', 'TEST WEJŚCIA': 'INPUT TEST', 'BETA • MIKROFON': 'BETA • MICROPHONE', 'BETA: NAZWY GIER STEAM/EPIC W STT': 'BETA: STEAM/EPIC GAME NAMES IN STT', 'AUTO STOP MIKROFONU • CISZA 1,15 S': 'AUTO STOP MICROPHONE • 1.15 S SILENCE', 'ROZMOWA BEZ KLIKANIA • PARAKEET (WŁĄCZ RĘCZNIE)': 'HANDS-FREE CHAT • PARAKEET (OPT IN)', 'PARAKEET • LIVE': 'PARAKEET • LIVE', 'HEJ CAPRI • AKTYWUJ PRZECHWYTYWANIE GŁOSU': 'HEY CAPRI • ACTIVATE LISTENING', 'FRAZA WYBUDZAJĄCA': 'WAKE PHRASE', 'CZUŁOŚĆ • HEJ CAPRI': 'SENSITIVITY • HEY CAPRI', 'FISH • DOSTĘPNOŚĆ': 'FISH • AVAILABILITY', 'BANK GŁOSU': 'VOICE LIBRARY', '◈  MENEDŻER GŁOSU ↗': '◈  VOICE MANAGER ↗', 'SILNIK V3': 'V3 ENGINE', 'FISH • TEKST PRÓBKI': 'FISH • SAMPLE TRANSCRIPT', 'WHISPER • BIBLIOTEKA': 'WHISPER • LIBRARY', 'AUTO STT CAŁEJ BIBLIOTEKI': 'TRANSCRIBE ENTIRE LIBRARY', 'IMPORT PRÓBEK': 'IMPORT SAMPLES', 'FRAGMENT / CLIP': 'FRAGMENT / CLIP', 'AUTO-CIĘCIE DŁUGICH NAGRAŃ / AUTO SPLIT': 'AUTO SPLIT LONG RECORDINGS', 'AUTOMATYCZNE CIĘCIE': 'AUTO SPLITTING', 'ŹRÓDŁO GŁOSU • PRÓBKA REFERENCYJNA': 'VOICE SOURCE • REFERENCE SAMPLE', 'Domyślne · próbka WAV z Fish S2.cpp': 'Default · Fish S2.cpp WAV sample', 'Dodaj plik dźwiękowy… (Eksplorator Windows)': 'Add an audio file… (Windows File Explorer)', 'FISH S2.CPP • BACKEND': 'FISH S2.CPP • BACKEND', 'ZAPISZ KLUCZ': 'SAVE KEY', 'USUŃ KLUCZ': 'DELETE KEY', 'PARAMETRY API ↗': 'API SETTINGS ↗', 'Pokaż': 'Show', 'Motyw interfejsu': 'Interface theme', 'CAPRI • PULPIT (MINI)': 'CAPRI • DESKTOP (MINI)', 'Wyczyść': 'Clear', 'Wybierz kategorię po lewej. Zmiany zapisują się automatycznie.': 'Choose a category on the left. Changes are saved automatically.', 'Wydajność / testy': 'Performance / Tests', 'Tryb lokalny': 'Local mode', '● Gotowa': '● Ready', 'Pokaż rozmowę': 'Show conversation', 'Mikrofon': 'Microphone', 'Przełącz na nakładkę': 'Switch to overlay', 'Ukryj': 'Hide', 'Zamknij': 'Close', 'Otwórz pełne okno': 'Open full window', 'Włącz lub wyłącz głos': 'Toggle voice', 'Ładowanie': 'Loading', 'Dostawca modelu rozmowy': 'Chat model provider', 'WŁASNE MODELE': 'CUSTOM MODELS'}

# Additional release-candidate translations: full descriptions, dialogs and voice controls.
# Only fixed interface text is translated; model names, user content and paths are not.
EN_UI.update({
    'Dane rozmów będą wysyłane do wybranej usługi tylko po przełączeniu na API.':
        'Conversation content is sent to the selected service only when External API is enabled.',
    'USUŃ ZAPISANE ROZMOWY': 'DELETE SAVED CONVERSATIONS',
    'TESTY OPTYMALIZACJI • Każdą opcję możesz wyłączyć jednym kliknięciem.\nDomyślnie zachowujemy stare działanie. Nie zmieniamy jakości Fish, Spotify ani pamięci.':
        'OPTIMIZATION TESTS • Disable any option with one click.\nExisting behavior is preserved by default. Voice, Spotify and memory are unaffected.',
    'Połącz Spotify API, aby uruchamiać konkretne piosenki; zwykłe play/pause działa przez Windows Media.':
        'Connect Spotify API to play specific songs. Basic play/pause uses Windows Media.',
    'HISTORIA DZIAŁAŃ AGENTA': 'AGENT ACTIVITY HISTORY',
    's2.cpp • Windows • 127.0.0.1:3030 • backend w ustawieniach głosu':
        's2.cpp • Windows • 127.0.0.1:3030 • backend under Voice settings',
    'WSL/CPU • lokalny serwer 127.0.0.1:8080 • sprawdź Napraw Capri (menu Start)':
        'WSL/CPU • local server 127.0.0.1:8080 • see Napraw Capri (menu Start)',
    'Automatycznie zwiń Morph Mini po rozmowie': 'Automatically collapse Morph Mini after a conversation',
    'Przyciągaj Edge Sprite do krawędzi ekranu': 'Snap Edge Sprite to screen edges',
    'NIEOFICJALNY PROJEKT FANOWSKI — nie jest autoryzowany ani wspierany przez CD PROJEKT RED. CD PROJEKT RED dopuszcza niekomercyjne programy typu overlay. Nie oznacza to pozwolenia na komercyjną dystrybucję postaci, grafik, głosów lub muzyki. Materiały osób trzecich i modele TTS mają osobne warunki licencyjne. Autor projektu odpowiada za uzyskanie wymaganych praw; licencja na własny kod nie została w tej paczce określona.':
        'UNOFFICIAL FAN PROJECT — not approved or endorsed by CD PROJEKT RED. Non-commercial overlays may fall under their fan content guidelines. This does not grant rights to commercially distribute characters, artwork, voices or music. Third-party content and TTS models have separate terms. The project owner must obtain all necessary rights; no license for the Capri source code has been selected.',
    'IVONA to zamknięty silnik SAPI. Działa tylko z zainstalowanymi głosami; nie trenuje się go w Capri.':
        'IVONA is a proprietary SAPI engine. It requires installed voices and cannot be trained in Capri.',
    'ODŚWIEŻ ZAINSTALOWANE GŁOSY IVONA': 'REFRESH INSTALLED IVONA VOICES',
    'ODŚWIEŻ GŁOSY WINDOWS': 'REFRESH WINDOWS VOICES',
    'Piper: odtwarzanie zainstalowanego lokalnie modelu ONNX. Tutaj konfigurujesz tylko gotowość i silnik odtwarzania.':
        'Piper plays an existing local ONNX model. Configure availability and playback here.',
    'ODŚWIEŻ STATUS MODELU': 'REFRESH MODEL STATUS',
    'FISH S2.1 PRO FREE • ONLINE\nWymaga internetu i klucza API. Domyślnie używa próbki z Fish S2.cpp; możesz też wskazać własny plik audio. Do Fish Audio trafia krótka próbka WAV, jej transkrypcja i tekst odpowiedzi. Lokalny Fish S2.cpp nie wysyła plików do chmury. Brak automatycznego przełączania na płatne API.':
        'FISH S2.1 PRO FREE • ONLINE\nRequires internet and an API key. Uses the Fish S2.cpp sample by default; you can choose your own audio file. A short WAV reference, its transcript and response text are uploaded to Fish Audio. Local Fish S2.cpp does not send files to the cloud. No automatic switch to a paid API.',
    'Domyślnie używana jest rzeczywista próbka główna Fish S2. Wymaga poprawnej transkrypcji.':
        'By default, Fish uses the actual primary S2 reference sample. A matching transcript is required.',
    'ZEWNĘTRZNE TTS • OpenAI-compatible /v1/audio/speech (WAV).\nDziała wyłącznie po wybraniu tego silnika. Przesyła tekst wypowiedzi do wskazanego API. Dostawca może naliczać opłaty. Klucz nie jest zapisywany w config.json.':
        'EXTERNAL TTS • OpenAI-compatible /v1/audio/speech (WAV).\nOnly active when this engine is selected. Speech text is sent to the configured API. The provider may charge usage fees. Keys are never stored in config.json.',
    'ZAPISZ API GŁOSU I KLUCZ': 'SAVE VOICE API SETTINGS & KEY',
    'USUŃ KLUCZ TTS': 'DELETE TTS API KEY',
    '◈  FISH S2 // BIBLIOTEKA PRÓBEK': '◈  FISH S2 // SAMPLE LIBRARY',
    'Wybierz nagranie, edytuj jego transkrypcję i zdecyduj, czy jest bazą głosu, dodatkową próbką czy ma zostać pominięte. Możesz zaznaczyć wiele pozycji.':
        'Select recordings, edit their transcripts and choose which are primary, supporting or disabled references. Multiple selection is supported.',
    '▣  OTWÓRZ FOLDER PRÓBEK': '▣  OPEN SAMPLE FOLDER',
    '▶  ODSŁUCHAJ ZAZNACZONĄ': '▶  PLAY SELECTED',
    '▣  POKAŻ PLIK W FOLDERZE': '▣  SHOW FILE IN FOLDER',
    'CAPRI // ZEZWOLIĆ NA JEDNĄ OPERACJĘ?': 'CAPRI // ALLOW THIS ONE ACTION?',
    'Sprawdź parametry. Odmowa niczego nie wykonuje. Capri nie dostaje automatycznej zgody na kolejne operacje.':
        'Review the details. Denying does nothing. Capri does not receive blanket permission for future actions.',
    '● MÓW': '● SPEAK',
    'TRYB MINI / UKŁAD': 'MINI MODE / LAYOUT',
    'ŹRÓDŁO': 'SOURCE',
    'Wybierz głos systemowy Windows (bez treningu).': 'Select a Windows system voice (no training).',
    'PEŁNY ENDPOINT /v1/audio/speech': 'FULL /v1/audio/speech ENDPOINT',
    'NAZWA / ID GŁOSU': 'VOICE NAME / ID',
    'KLUCZ API • przechowywany poza konfiguracją': 'API KEY • stored separately from configuration',
    'TRANSKRYPCJA ZAZNACZONEJ PRÓBKI:': 'TRANSCRIPT OF SELECTED SAMPLE:',
})


# Complete English interface for separate studio windows, avatar editor and media workflows.
EN_UI.update({
'CAPRI // MENEDŻER GŁOSU • v16.1':'CAPRI // VOICE MANAGER',
'CAPRI // STUDIO WŁASNEGO GŁOSU — PIPER':'CAPRI // CUSTOM VOICE STUDIO — PIPER',
'CAPRI // EMOCJE I AWATARY':'CAPRI // EMOTIONS & AVATARS',
'◈  CAPRI // BANK GŁOSU':'◈  CAPRI // VOICE LIBRARY',
'Biblioteka głosu':'Voice library',
'Zaznacz nagranie z lewej, a po prawej edytuj tekst i reguły. Zmiany zapisują się dopiero po kliknięciu ZAPISZ. Nagrania pozostają dostępne między uruchomieniami.':
'Select a recording on the left; edit its text and matching rules on the right. Click SAVE to apply your changes. Recordings persist across restarts.',
'⌕  Szukaj po tekście, pytaniu lub nazwie…':'⌕  Search text, question or name…',
'01 / BIBLIOTEKA NAGRAŃ':'01 / RECORDING LIBRARY',
'02 / TEKST I REGUŁY':'02 / TEXT & MATCHING RULES',
'03 / SPRAWDŹ DOPASOWANIE':'03 / TEST MATCHING',
'ODPOWIEDŹ':'REPLY', 'PYTANIA':'QUESTIONS', 'JĘZYK':'LANGUAGE', 'ŹRÓDŁO':'SOURCE',
'＋  NOWY':'＋  NEW', '⇣  IMPORT WAV / MP3':'⇣  IMPORT WAV / MP3',
'▣  FOLDER NAGRAŃ':'▣  RECORDING FOLDER',
'Otwórz w Eksploratorze katalog importowanych nagrań Capri':'Open Capri recording folder in Windows File Explorer',
'▣  POKAŻ WYBRANY PLIK':'▣  SHOW SELECTED FILE',
'TEKST W NAGRANIU — wyświetlany na czacie:':'RECORDING TRANSCRIPT — shown in chat:',
'PYTANIA / FRAZY — jedno na linię:':'MATCH PHRASES — one per line:',
'INSTRUKCJA DLA BIELIKA (intencja nagrania):':'INSTRUCTION FOR BIELIK (recording intent):',
'JĘZYK:':'LANGUAGE:', 'AKTYWNE':'ENABLED',
'Dokładne pytanie (interpunkcja ignorowana)':'Exact question (ignore punctuation)',
'Pytanie zawiera frazę (całe słowa)':'Question contains phrase (whole words)',
'✓  ZAPISZ ZMIANY':'✓  SAVE CHANGES', '▶  ODSŁUCHAJ':'▶  PLAY', '✕  USUŃ':'✕  DELETE',
'◈  WYGENERUJ NOWE NAGRANIE • FISH VULKAN':'◈  GENERATE RECORDING • FISH VULKAN',
'Generuje lokalnie — wymaga uruchomionego serwera Fish Vulkan':'Generates locally — requires the Fish Vulkan server',
'Wpisz przykładową wiadomość do Capri':'Enter an example message to Capri',
'⌕  TESTUJ PYTANIE / INTENCJĘ':'⌕  TEST QUESTION / INTENT',
'Gotowe.':'Ready.',
'Np. Cześć! Czego dzisiaj ode mnie chcesz?':'E.g. Hi! What would you like me to do today?',
'jak masz na imię?\nkim jesteś?\njak się nazywasz?':'what is your name?\nwho are you?\nwhat should I call you?',
'Użyj tego nagrania, gdy użytkownik prosi Capri o przedstawienie się.':'Use this recording when asked to introduce Capri.',
'Capri — Menedżer Głosu':'Capri — Voice Manager',
'Wybrano nagranie. Możesz edytować tekst, odsłuchać je lub usunąć.':'Recording selected. You can edit, play or delete it.',
'Zaimportowano. Nagranie jest gotowe — nie trzeba ponownie generować głosu.':'Imported. The recording is ready; no regeneration required.',
'Zapisano tekst, pytania i aktywność. Capri odczyta zmiany automatycznie.':'Saved transcript, questions and enabled state. Capri picks up changes automatically.',
'Nagranie usunięte.':'Recording deleted.',
'Fish Vulkan generuje nagranie…':'Fish Vulkan is generating audio…',
'Wygenerowano nagranie. Może reagować na przypisane pytania oraz zgodną odpowiedź AI.':'Recording generated. It can match the assigned prompts or a compatible AI response.',
'Najpierw wpisz dokładny tekst nagrania.':'Enter the exact recording transcript first.',
'Najpierw wybierz nagranie z listy. Dla nowego tekstu użyj IMPORTUJ lub WYGENERUJ.':'Select a recording first. For new text use IMPORT or GENERATE.',
'Wpisz przykładowe pytanie, aby sprawdzić zapisane reguły.':'Enter a sample question to test saved rules.',
'Brak pewnego dopasowania. Capri użyje zwykłej rozmowy / Agenta PC.':'No reliable match. Capri will use normal chat / PC Agent.',
'Usuń nagranie':'Delete recording',
'Trwale usunąć nagranie i jego przypisany tekst?':'Permanently delete the recording and its transcript?',
'Tekst jest za długi (maks. 1200 znaków).':'Text is too long (maximum 1200 characters).',
'Najpierw ustaw próbkę głosu i jej transkrypcję w głównej Capri.':'Set up a voice reference and transcript in Capri first.',
'Nie można otworzyć folderu wybranego pliku.':'Could not open the selected file folder.',
'Nie udało się odtworzyć nagrania: ':'Could not play recording: ',
'Nie udało się otworzyć folderu: ':'Could not open folder: ',
'Nie udało się wyrenderować: ':'Could not render audio: ',
'  •  dopasowanie bezpośrednie':'  •  exact match',
'  • pewność modelu: ':'  • model confidence: ',
'STUDIO GŁOSU CAPRI  •  Piper ONNX  •  dataset + trening WSL':'CAPRI VOICE STUDIO  •  Piper ONNX  •  dataset + WSL training',
'Studio głosu':'Voice Studio',
'To trenowany głos Piper, a nie klasyczna IVONA. Dodawaj krótkie nagrania z dokładnymi tekstami. Do samego treningu wymagany jest skonfigurowany Piper w WSL (osobno od Capri).':
'This trains a Piper voice, not classic IVONA. Add short recordings with accurate transcripts. Training requires Piper configured in WSL (separate from Capri).',
'Przygotuj nagrania, popraw transkrypcje i wytrenuj własny głos Piper.':'Prepare recordings, correct transcripts and train your own Piper voice.',
'Nagrania i przygotowanie':'Recordings & Preparation', 'Trening i eksport':'Training & Export',
'NAGRANIE WAV':'WAV RECORDING', 'TEKST (POPRAW PRZED TRENINGIEM)':'TRANSCRIPT (CORRECT BEFORE TRAINING)',
'ZATWIERDŹ':'APPROVE', 'PEWNOŚĆ STT':'STT CONFIDENCE',
'Automatyczne transkrypcje to wersje robocze. Odsłuchaj, popraw tekst i zaznacz „ZATWIERDŹ” przed treningiem.':
'Automatic transcripts are drafts. Listen, correct the text and APPROVE each recording before training.',
'DODAJ NAGRANIA • AUTO-CIĘCIE >30 s':'ADD RECORDINGS • AUTO-SPLIT >30s',
'▶ ODSŁUCHAJ':'▶ PLAY', '■ ZATRZYMAJ':'■ STOP', 'USUŃ PRÓBKĘ':'DELETE SAMPLE',
'ZAPISZ TEKSTY / DATASET':'SAVE TRANSCRIPTS / DATASET',
'AUTO STT + AUTOMATYCZNE CIĘCIE • PIPER':'AUTO STT + AUTOMATIC SPLITTING • PIPER',
'Silnik STT:':'STT engine:', 'Język:':'Audio language:', 'Min (s):':'Min (s):', 'Max (s):':'Max (s):',
'Pauza do cięcia (ms):':'Split silence (ms):', 'Margines audio (ms):':'Audio padding (ms):',
'Parakeet v3: lokalny CPU ONNX; wymaga Napraw Capri (menu Start). Cięcie wg pauz, bez sztucznych word timestamps.':
'Parakeet v3: local CPU ONNX; requires Napraw Capri (menu Start). Splits by silence, without synthetic word timestamps.',
'◈ AUTO STT + PODZIEL DŁUGIE AUDIO':'◈ AUTO STT + SPLIT LONG AUDIO',
'■ ANULUJ':'■ CANCEL', '▣  OTWÓRZ FOLDER PRÓBEK':'▣  OPEN SAMPLE FOLDER',
'▣  FOLDER TRENINGOWY':'▣  TRAINING FOLDER',
'Epoki:':'Epochs:', 'Checkpoint (opcjonalnie, zalecany):':'Checkpoint (optional, recommended):',
'WYBIERZ .CKPT':'CHOOSE .CKPT',
'PIPER: UTMOS/MOS wyłączony dla stabilności; checkpointy wg val_mel + last.':
'PIPER: UTMOS/MOS disabled for stability; checkpoints use val_mel + last.',
'TRENUJ W WSL + ZAPISZ W CAPRI':'TRAIN IN WSL + SAVE TO CAPRI',
'ZAIMPORTUJ GOTOWY MODEL .ONNX':'IMPORT EXISTING .ONNX MODEL',
'Próbki głosu Capri':'Capri voice samples',
'Niska pewność STT. Koniecznie sprawdź odsłuch i tekst.':'Low STT confidence. Verify the recording and transcript.',
'Najpierw wpisz tekst próbki, potem zatwierdź.':'Enter sample transcript before approving.',
'ZAINSTALOWANY MODEL: ':'INSTALLED MODEL: ', 'TAK':'YES', 'NIE':'NO',
'Nowe próbki są niezatwierdzone. Odsłuchaj i popraw tekst przed treningiem.':
'New samples are unapproved. Listen and correct transcripts before training.',
'Dodaj i opisz przynajmniej jedną próbkę.':'Add and annotate at least one sample.',
'Nie masz żadnych próbek w projekcie.':'There are no samples in the project.',
'Próbki powinny mieć 0,4–30 sekund. Podziel dłuższy materiał na pojedyncze zdania.':
'Samples should be 0.4–30 seconds long. Split longer audio into individual sentences.',
'Do importu próbek potrzebny jest FFmpeg w PATH (ffmpeg.exe).':'FFmpeg must be in PATH (ffmpeg.exe) to import samples.',
'Każda próbka wymaga zgodnej z nagraniem transkrypcji (1–500 znaków).':
'Each sample needs an accurate matching transcript (1–500 characters).',
'Zatwierdzona próbka wymaga poprawnej transkrypcji (1–500 znaków).':
'An approved sample needs a valid transcript (1–500 characters).',
'Trening jest już uruchomiony.':'Training is already running.',
'Najpierw odsłuchaj i ZATWIERDŹ przynajmniej jedną próbkę.':'Listen to and APPROVE at least one sample first.',
'Poczekaj na zakończenie Auto STT lub anuluj ten proces.':'Wait for Auto STT to finish or cancel it.',
'Model zapisany w Capri. Przełącz silnik głosu na Piper.':'Model saved to Capri. Select Piper as the voice engine.',
'Anulowanie zlecone — aktualny etap Whisper może jeszcze chwilę potrwać.':'Cancellation requested — the current Whisper step may still need to finish.',
'MODEL GOTOWY. Automatycznie zainstalowany w Capri. Wybierz PIPER w modelach głosu.':
'MODEL READY. Automatically installed in Capri. Select PIPER under Voice.',
'Emocje i awatary':'Emotions & Avatars',
'Pliki awatarów: assets/emocje/<emocja>/, np. happy/zdjecie.gif.\nKażda zwykła nazwa GIF/PNG/WEBP/MP4 działa automatycznie.\nPodfolder idle/thinking/speaking/reaction jest opcjonalny.\nImport kopiuje pliki do folderu wybranej emocji i aktywności.':
'Avatar files: assets/emocje/<emotion>/, e.g. happy/image.gif.\nStandard GIF/PNG/WEBP/MP4 filenames work automatically.\nThe idle/thinking/speaking/reaction subfolder is optional.\nImport copies files into the selected emotion and activity folder.',
'OTWÓRZ FOLDER EMOCJI':'OPEN EMOTION FOLDER', 'ODŚWIEŻ LISTĘ':'REFRESH LIST',
'PODGLĄD WYBRANEGO AWATARA':'SELECTED AVATAR PREVIEW', 'Wybierz plik z listy':'Select a file',
'+ DODAJ PLIKI':'+ ADD FILES', '− USUŃ WYBRANY':'− REMOVE SELECTED',
'Waga wariantu (częstość):':'Variant weight (frequency):',
'Większa waga = częstsze losowanie danego pliku':'Higher weight means the file is selected more frequently',
'Czas płynnego przejścia (ms):':'Transition duration (ms):',
'Emocja':'Emotion', 'Wariant':'Variant', 'Reakcja':'Reaction', 'Powrót':'Return',
'ZAMKNIJ':'CLOSE',
'Foldery aplikacji niedostępne':'Application folders unavailable',
'Nie udało się dodać pliku':'Could not add file',
'Usuń plik avatara':'Delete avatar file',
'Usunąć plik z dysku? Tej operacji nie można cofnąć.':'Delete file from disk? This cannot be undone.',
'Folder emocji':'Emotion folder',
'Brak wybranego pliku':'No file selected', 'Nie znaleziono pliku':'File not found',
'Wideo: podgląd GIF/PNG/JPG/WEBP działa tutaj.':'Video: GIF/PNG/JPG/WEBP preview is available here.',
'Wideo odtwarzane jest w awatarze.':'Video playback is available in the avatar.',
'Nie można odczytać obrazu':'Cannot read image',
'Neutralna':'Neutral', 'Radosna':'Happy', 'Figlarna':'Playful', 'Troskliwa':'Caring',
'Poważna':'Serious', 'Zirytowana':'Annoyed', 'Wściekła':'Furious',
'Zaskoczona':'Surprised', 'Senna':'Sleepy', 'Flirtująca':'Flirty',
'Zawstydzona':'Bashful', 'Zadziorna':'Smug', 'Zaciekawiona':'Curious',
'Sceptyczna':'Skeptical', 'Smutna':'Sad', 'Zaniepokojona':'Worried',
'Z ulgą':'Relieved', 'Podekscytowana':'Excited',
'Spoczynek':'Idle', 'Myślenie':'Thinking', 'Mówienie':'Speaking',
'BRAK PLIKU':'MISSING FILE', 'waga':'weight', 'Polski':'Polish', 'Angielski':'English',
'AUTO STT':'AUTO STT', 'Filtr':'Filter', 'Folder: ':'Folder: ',
'Do importu':'For import',
})

# Labels for the main navigation (Brain replaces the old Appearance shortcut).
EN_UI.update({'Rozmowa':'Chat', 'Ustawienia':'Settings', 'Powiedz':'Say',
              'Wyciszony':'Muted', 'Wyłącz głos':'Mute voice', 'Włącz głos':'Enable voice',
              'Słucham…':'Listening…', 'Myślę…':'Thinking…', 'Mówię…':'Speaking…'})

def ui_language_from_profile() -> str:
    """Read the single app-level language, never language of an audio sample."""
    import json
    from capri_paths import data_root
    try:
        config = json.loads((data_root() / 'settings.json').read_text(encoding='utf-8'))
        return 'en' if config.get('lang') == 'en' else 'pl'
    except (OSError, ValueError, TypeError):
        return 'pl'

def translate_ui(s: str, lang: str) -> str:
    return EN_UI.get(s, s) if lang == 'en' else s

def apply_ui_language(window, lang: str) -> None:
    from PySide6.QtWidgets import QLabel, QPushButton, QCheckBox, QRadioButton, QGroupBox, QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QTabWidget, QWidget, QTableWidget
    title = window.property('_capri_window_title_source')
    if title is None and window.windowTitle() in EN_UI:
        title = window.windowTitle()
        window.setProperty('_capri_window_title_source', title)
    if title in EN_UI:
        window.setWindowTitle(translate_ui(title, lang))
    # Remember original static source labels so PL -> EN -> PL restores labels.
    controls = []
    for kind in (QLabel, QPushButton, QCheckBox, QRadioButton, QGroupBox):
        controls.extend(window.findChildren(kind))
    for widget in controls:
        current = widget.text() if hasattr(widget, 'text') else widget.title()
        original = widget.property('_capri_ui_source')
        if original is None and current in EN_UI:
            original = current
            widget.setProperty('_capri_ui_source', original)
        if original in EN_UI:
            if hasattr(widget, 'setText'):
                widget.setText(translate_ui(original, lang))
            else:
                widget.setTitle(translate_ui(original, lang))
    # Tooltips are static interface chrome, unlike user-entered texts.
    for widget in window.findChildren(QWidget):
        current = widget.toolTip()
        source = widget.property('_capri_tooltip_source')
        if source is None and current in EN_UI:
            source = current
            widget.setProperty('_capri_tooltip_source', source)
        if source in EN_UI:
            widget.setToolTip(translate_ui(source, lang))
    # Translate header labels without changing the data shown in cells.
    for table in window.findChildren(QTableWidget):
        if not table.property('_capri_header_sources'):
            original = [table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else ''
                        for i in range(table.columnCount())]
            table.setProperty('_capri_header_sources', original)
        for i, original in enumerate(table.property('_capri_header_sources') or []):
            if table.horizontalHeaderItem(i):
                table.horizontalHeaderItem(i).setText(translate_ui(original, lang))
    if hasattr(window, 'settings_tabs'):
        for original, page in window._settings_pages.items():
            index = window.settings_tabs.indexOf(page)
            if index >= 0:
                window.settings_tabs.setTabText(index, translate_ui(original, lang))
    if hasattr(window, 'design'):
        for i, button in enumerate(window.design.categories):
            source = next((key for key,page in window._settings_pages.items()
                           if window.settings_tabs.indexOf(page)==i), '')
            if source:
                button.setText(translate_ui(source, lang))
        for button, source in zip(window.design.nav, ('Rozmowa', 'Głos', 'Mózg', 'Ustawienia')):
            button.setText(translate_ui(source, lang))
        window.design.clear.setText(translate_ui('Wyczyść',lang))
        window.design.help.setText(translate_ui('Wybierz kategorię po lewej. Zmiany zapisują się automatycznie.',lang))
    # Translate known placeholders and tooltips as well as visible labels.
    # Store a canonical PL source so switching EN -> PL is lossless.
    for widget in window.findChildren(QLineEdit) + window.findChildren(QTextEdit) + window.findChildren(QPlainTextEdit):
        if hasattr(widget, 'placeholderText') and hasattr(widget, 'setPlaceholderText'):
            source = widget.property('_capri_placeholder_source')
            current = widget.placeholderText()
            if source is None and current in EN_UI:
                source = current
                widget.setProperty('_capri_placeholder_source', source)
            if source in EN_UI:
                widget.setPlaceholderText(translate_ui(source, lang))
    for widget in window.findChildren(QTabWidget):
        for i in range(widget.count()):
            source = widget.widget(i).property('_capri_tab_source')
            current = widget.tabText(i)
            if source is None and current in EN_UI:
                source = current
                widget.widget(i).setProperty('_capri_tab_source', source)
            if source in EN_UI:
                widget.setTabText(i, translate_ui(source, lang))
    # Only translate known selectors; never modify user-selected model IDs.
    for combo in window.findChildren(QComboBox):
        for i in range(combo.count()):
            displayed = combo.itemText(i)
            if displayed in EN_UI:
                combo.setItemText(i, translate_ui(displayed,lang))
            elif displayed in EN_UI.values() and lang=='pl':
                reverse = {v:k for k,v in EN_UI.items()}
                combo.setItemText(i, reverse.get(displayed,displayed))
