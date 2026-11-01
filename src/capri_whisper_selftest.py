"""Validate actual Whisper STT with the bundled Capri speech sample at setup."""
from __future__ import annotations
from pathlib import Path
import traceback

def check_whisper() -> None:
    from capri_paths import data_root, local_root
    from capri_default_voice import ASSETS, SEEDS
    from faster_whisper import WhisperModel
    model_root = data_root() / 'models'
    model_root.mkdir(parents=True, exist_ok=True)
    # Download once during setup; never require a separate Python install.
    whisper = WhisperModel('small', device='cpu', compute_type='int8',
                           download_root=str(model_root))
    wav = ASSETS / SEEDS[0][0]
    if not wav.is_file():
        raise FileNotFoundError('Brak próbki głosu Capri do testu STT')
    result, _ = whisper.transcribe(str(wav), language='pl',
                                   vad_filter=True,
                                   vad_parameters={'min_silence_duration_ms': 450,
                                                   'speech_pad_ms': 250},
                                   beam_size=2)
    transcript = ' '.join(x.text.strip() for x in result).strip()
    if not transcript:
        raise RuntimeError('Whisper nie rozpoznał mowy w referencyjnym WAV')
    log = local_root() / 'whisper_selftest.log'
    log.parent.mkdir(parents=True,exist_ok=True)
    # Do not log the user's private recordings; test on bundled sample only.
    log.write_text('Whisper small + Silero VAD: OK\n',encoding='utf-8')


def main() -> int:
    try:
        check_whisper()
        return 0
    except Exception:
        from capri_paths import local_root
        log = local_root() / 'whisper_selftest.log'
        log.parent.mkdir(parents=True,exist_ok=True)
        log.write_text(traceback.format_exc(), encoding='utf-8')
        return 11

if __name__ == '__main__':
    raise SystemExit(main())
