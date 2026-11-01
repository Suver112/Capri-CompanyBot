# Modele rozmowy i pamięć — Capri CompanyBot

## Lokalne LLM

Capri korzysta z usługi Ollama. W aktualnych źródłach widoczne są modele `qwen3.5:2b`, `qwen3.5:4b`, `qwen3.5:9b` oraz `SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M`. Inne tagi widoczne w kodzie mogą mieć status starszych presetów. Model musi zostać pobrany w Ollamie, zanim można go wybrać.

Domyślny nowy profil używa `qwen3.5:4b`, o ile instalator nie zapisał innego modelu. Większy model zwykle oznacza wyższe zapotrzebowanie na RAM/VRAM i dłuższe czasy odpowiedzi. Dostępność konkretnych wag i licencje modelu sprawdzaj u dostawcy.

## Ciągłość rozmowy

Aktualny kontekst składa się z ostatnich wiadomości użytkownika i Capri. Pamięć długoterminowa przechowuje odrębne zdarzenia konwersacyjne i może odzyskiwać odpowiednie informacje. Nie zastępuje to pełnej, bezbłędnej pamięci. Dłuższy kontekst zwiększa zapotrzebowanie na zasoby.

Pytanie „Chcesz usłyszeć żart?” nie jest poleceniem „Opowiedz żart”. W tej sytuacji Capri powinna poczekać na żart użytkownika i zareagować na jego puentę. Jeśli tego nie robi, podaj w zgłoszeniu trzy kolejne wiadomości, model oraz włączone optymalizacje.

## Persony i lore

Wiedza o fikcyjnym świecie nie jest tożsama z pamięcią osoby korzystającej z Capri. Imiona postaci fabularnych (np. „D.”) nie identyfikują użytkownika. Ustawienia osobowości oddziałują na styl odpowiedzi, nie powinny zmieniać tożsamości rozmówcy.

## Optymalizacje

`opt_adaptive_llm`, `opt_short_keepalive` i `opt_idle_ui` są domyślnie ustawione na `true` w nowym profilu. Nie oznacza to, że każda stara konfiguracja zostanie nadpisana. Dane ustawień przechowywane są lokalnie w `settings.json`.

## Lokalny test Ollamy

```powershell
ollama list
ollama ps
```

`ollama list` pokazuje pobrane modele, a `ollama ps` — modele nadal trzymane w pamięci. Nie usuwaj modeli współdzielonych z innymi aplikacjami bez świadomej decyzji.
