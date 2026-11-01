"""Explicit offline one-time Fish profile preparation (run with Capri closed)."""
from __future__ import annotations

import json
from pathlib import Path

from capri_paths import data_root, local_root
from capri_fish_profiles import prepare_profile
from fish_bridge import fish_reference_path


def main() -> int:
    settings_path = data_root() / 'settings.json'
    if not settings_path.is_file():
        print('Brak konfiguracji Capri:', settings_path)
        return 2
    try:
        cfg = json.loads(settings_path.read_text(encoding='utf-8'))
        sample = Path(fish_reference_path(cfg.get('voice_ref_path', ''))).resolve()
        transcript = str(cfg.get('fish_ref_transcript', '')).strip()
        source = str(cfg.get('fish_ref_path', '')).strip()
        if not transcript or not source or Path(source).resolve() != sample:
            print('W ustawieniach Capri ustaw probke i poprawny tekst probki (AUTO STT).')
            return 3
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        print('Nie mozna odczytac probki lub ustawien:', exc)
        return 3
    root = Path(__file__).resolve().parent
    print('Kodowanie probki do .s2voice, tylko pierwsze przygotowanie moze byc dlugie.')
    print('Tryb CPU zapobiega uruchamianiu drugiego modelu na GPU obok serwera Fish.')
    profile = prepare_profile(sample, transcript, program_root=root, timeout=900,
                              force=True, progress=lambda status: print('Status:',status))
    if profile:
        print('GOTOWE:', profile.file)
        print('Od teraz przy kazdej wypowiedzi Capri wysyla identyfikator profilu, nie WAV.')
        return 0
    print('NIE POWIODLO SIE. Log:', (local_root() / 'fish_voice_profiles' / 'preparation.log'))
    print('Normalna synteza Capri nadal moze uzyc starego przesylania WAV.')
    return 4


if __name__ == '__main__':
    raise SystemExit(main())
