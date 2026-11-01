"""Offline custom Piper voice shared by Capri and the separate voice studio.

An ONNX voice is not IVONA: IVONA itself cannot be fine-tuned from audio here.
"""
from __future__ import annotations

from capri_paths import data_root

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import wave
import threading

ROOT = data_root() / 'piper_voice'
MODEL = ROOT / 'capri.onnx'
CONFIG = ROOT / 'capri.onnx.json'


def installed_model() -> bool:
    return MODEL.is_file() and CONFIG.is_file() and MODEL.stat().st_size > 100_000


def install_model(onnx: str | Path, config: str | Path) -> tuple[str, str]:
    """Atomically replace the installed voice, so Capri can pick it up next turn."""
    model = Path(onnx).resolve()
    config_path = Path(config).resolve()
    if model.suffix.casefold() != '.onnx' or not model.is_file() or model.stat().st_size < 100_000:
        raise ValueError('Wybierz wyeksportowany model Piper .onnx.')
    try:
        content = json.loads(config_path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise ValueError('Brak poprawnego pliku konfiguracyjnego modelu .onnx.json.') from exc
    if not isinstance(content, dict) or 'audio' not in content or not isinstance(content['audio'], dict):
        raise ValueError('Konfiguracja nie wygląda jak Piper .onnx.json (brak audio).')
    ROOT.mkdir(parents=True, exist_ok=True)
    staging = ROOT / ('.piper-' + str(time.time_ns()))
    staging.mkdir()
    try:
        shutil.copyfile(model, staging / MODEL.name)
        shutil.copyfile(config_path, staging / CONFIG.name)
        # Install config first, then the model. If the model fails to copy,
        # the previous valid model remains rather than an incomplete new one.
        os.replace(staging / CONFIG.name, CONFIG)
        os.replace(staging / MODEL.name, MODEL)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return str(MODEL), str(CONFIG)


def piper_command() -> list[str]:
    """Use a local executable; never download or execute an unknown binary."""
    executable_name = 'piper.exe' if os.name == 'nt' else 'piper'
    for candidate in (ROOT / executable_name, Path(sys.executable).with_name(executable_name)):
        if candidate.is_file():
            return [str(candidate)]
    binary = shutil.which('piper')
    if binary:
        return [binary]
    raise RuntimeError('Piper nie jest zainstalowany. Zainstaluj piper-tts w Pythonie Capri lub umieść piper.exe w folderze piper_voice.')


def synthesize_piper(text: str, language: str, timeout: int = 180,
                     cancel: threading.Event | None = None) -> str:
    """Worker-thread only. Produces one WAV, does not retain heavyweight models."""
    if not installed_model():
        raise RuntimeError('Brak wytrenowanego modelu Piper. Otwórz STUDIO GŁOSU i zainstaluj .onnx + .onnx.json.')
    if language not in ('pl', 'en'):
        raise ValueError('Nieznany język Piper.')
    content = text.strip()
    if not content:
        raise ValueError('Pusty tekst.')
    cmd = piper_command() + ['--model', str(MODEL), '--config', str(CONFIG), '--output_file']
    fd, path = tempfile.mkstemp(prefix='capri_piper_', suffix='.wav')
    os.close(fd)
    try:
        error_log = tempfile.TemporaryFile(mode='w+b')
        process = subprocess.Popen(cmd + [path], stdin=subprocess.PIPE,
                                   stdout=subprocess.DEVNULL, stderr=error_log,
                                   text=True, encoding='utf-8', errors='replace',
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            assert process.stdin is not None
            process.stdin.write(content+'\n')
            process.stdin.close()
            start = time.monotonic()
            while process.poll() is None:
                if cancel is not None and cancel.is_set():
                    process.kill()
                    raise RuntimeError('Synteza Piper została przerwana po wyłączeniu głosu.')
                if time.monotonic() - start > timeout:
                    process.kill()
                    raise RuntimeError('Piper: upłynął limit czasu generowania.')
                time.sleep(.1)
            error_log.seek(0)
            stderr = error_log.read()[-1000:].decode('utf-8', errors='replace')
            if process.returncode or not Path(path).is_file() or Path(path).stat().st_size < 256:
                raise RuntimeError('Piper nie wygenerował WAV: ' + stderr[-900:])
            try:
                with wave.open(path, 'rb') as output:
                    if output.getnframes() < output.getframerate() // 5:
                        raise ValueError('Próbka jest krótsza niż 0,2 s.')
            except (OSError, EOFError, wave.Error, ValueError) as exc:
                raise RuntimeError('Piper wygenerował niepoprawny lub pusty WAV.') from exc
            return path
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            error_log.close()
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
