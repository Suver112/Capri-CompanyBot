# Głos, Fish i próbki referencyjne — Capri CompanyBot

## Silniki

Domyślna instalacja może skonfigurować lokalny **Fish S2.cpp GPU**, szczególnie Vulkan (AMD, NVIDIA, Intel przy zgodnym sterowniku); CUDA to dodatkowy backend na zgodnym sprzęcie NVIDIA. Inne dostępne w kodzie tryby obejmują syntezę systemową, niektóre zewnętrzne API, opcjonalną IVONA oraz Piper. Dostępność opcji zależy od instalacji i licencji poszczególnych silników.

## Syntetyczna próbka Capri

Do projektu dołączono `src/assets/default_voice/capri-glos.mp3` oraz zestaw fragmentów WAV. Według twórcy projektu próbka jest **w pełni syntetyczna, stworzona przy użyciu Fish Audio, nieoparta na nagraniu żadnej rzeczywistej osoby**. To opis pochodzenia referencji, nie oświadczenie o licencji każdego modelu TTS. Próbki są potrzebne do odtworzenia głosu z przygotowaną transkrypcją; model nie korzysta automatycznie ze wszystkich plików naraz.

## Biblioteka próbek

W ustawieniach **Głos** można importować pliki, wiele plików albo folder. Domyślnie włączone jest auto-cięcie (`auto_split_clips`). Dłuższe nagrania mogą zostać podzielone na krótsze fragmenty; poprawność tekstu referencyjnego jest istotna dla jakości polskiej wymowy.

Warto:

1. Stosować czyste próbki bez silnego pogłosu i podkładu muzycznego.
2. Dopasować transkrypcję do tego, co faktycznie słychać.
3. Zostawić co najmniej jedną poprawną aktywną referencję.
4. Przetestować w **Tekst do wypowiedzenia** kilka krótkich zdań po polsku.
5. Zmienić próbkę główną, gdy głos jest niewyraźny lub akcent nie brzmi naturalnie.

## Gdy syntezator zwraca HTTP 503

Serwer Fish może w danym momencie obsługiwać poprzednią wypowiedź. Capri ma mechanizm ponawiania i koordynacji żądań, ale serwer nadal może pozostać zajęty lub nieodpowiadający. Nie uruchamiaj równolegle wielu instancji tego samego serwera. Sprawdź log Fish, a następnie spróbuj zakończyć odtwarzanie i ponowić próbę.

## Problemy z RAM/VRAM

LLM, Fish i STT mogą pracować jednocześnie. Gdy komputer zaczyna intensywnie używać pamięci wymiany lub się zawiesza, rozważ lżejszą kwantyzację modelu, krótszy `keep_alive`, wyłączenie niepotrzebnych komponentów albo zmianę modelu rozmowy. Nie zakładaj, że użycie GPU przez Fish całkowicie eliminuje zużycie RAM.

## Licencje

**Kod Fish Speech, wagi Fish S2-Pro i usługi Fish Audio mają odrębne warunki.** Dla wag S2-Pro projekt wskazuje Research License i wymóg akceptacji przed użyciem. Szczegóły: [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) oraz [informacje prawne](../LEGAL/INFORMACJE_PRAWNE.md).
