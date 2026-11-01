"""Reliable, silent Ollama startup for packaged Capri on Windows.

Never installs software on app launch; the Capri setup wizard owns installs.
This helper starts the vendor's tray application when available and uses the
standalone `ollama serve` only if there is no running tray instance.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import urlopen

API = 'http://127.0.0.1:11434/api/tags'


def find_ollama_executable() -> Path | None:
    """Works just after winget setup, before the new PATH reaches the process."""
    candidates: list[str] = []
    for command in ('ollama.exe', 'ollama'):
        found = shutil.which(command)
        if found:
            candidates.append(found)
    for variable, suffix in (
        ('LOCALAPPDATA', 'Programs/Ollama/ollama.exe'),
        ('ProgramFiles', 'Ollama/ollama.exe'),
        ('ProgramFiles(x86)', 'Ollama/ollama.exe'),
    ):
        base = os.environ.get(variable)
        if base:
            candidates.append(str(Path(base) / suffix))
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def ollama_ready(timeout: float = 1.5) -> bool:
    try:
        with urlopen(API, timeout=timeout) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def tray_running() -> bool:
    if os.name != 'nt':
        return False
    try:
        result = subprocess.run(
            ['tasklist.exe', '/NH', '/FI', 'IMAGENAME eq ollama app.exe'],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=False)
        return any('ollama app.exe' in line.casefold() for line in result.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        return False


def _spawn(binary: Path, mode: str) -> None:
    args = [str(binary)] if mode == 'tray' else [str(binary), 'serve']
    subprocess.Popen(
        args, cwd=str(binary.parent), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        close_fds=True)


def _wait_for_api(seconds: float) -> bool:
    deadline = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < deadline:
        if ollama_ready(timeout=0.8):
            return True
        time.sleep(min(0.7, max(0.0, deadline-time.monotonic())))
    return ollama_ready(timeout=0.8)


def ensure_ollama_running(*, wait_seconds: float = 18.0, log=print) -> bool:
    """Return API readiness. Never kill user's Ollama or spawn duplicates blindly."""
    if os.environ.get('CAPRI_SKIP_OLLAMA') == '1':
        log('[Ollama] Automatyczny start pominiety (CAPRI_SKIP_OLLAMA=1).')
        return ollama_ready()
    if ollama_ready():
        log('[Ollama] Lokalny serwer juz odpowiada.')
        return True
    cli = find_ollama_executable()
    if not cli:
        log('[Ollama] Nie znaleziono instalacji. Otworz Capri Setup -> Napraw.')
        return False
    # The Windows installer normally supplies the tray app. Unlike manually
    # launching `serve`, it owns server startup and updates. Some releases enter
    # a rapid restart loop if both the tray and separate serve use port 11434.
    app = cli.parent / 'ollama app.exe'
    if app.is_file():
        if not tray_running():
            try:
                _spawn(app, 'tray')
                log('[Ollama] Uruchomiono Ollama dla Windows.')
            except OSError as exc:
                log(f'[Ollama] Nie udalo sie uruchomic aplikacji: {exc}')
        else:
            log('[Ollama] Aplikacja w tle juz jest uruchomiona; czekam na API.')
        if _wait_for_api(wait_seconds):
            log('[Ollama] API gotowe na 127.0.0.1:11434.')
            return True
        # Don't launch a second server while the vendor tray app is running.
        if tray_running():
            log('[Ollama] Aplikacja dziala, ale API nie odpowiada. Zobacz %LOCALAPPDATA%\\Ollama\\server.log.')
            return False
    try:
        _spawn(cli, 'serve')
        log('[Ollama] Uruchomiono serwer CLI.')
    except OSError as exc:
        log(f'[Ollama] Nie udalo sie uruchomic serwera: {exc}')
        return False
    ready = _wait_for_api(wait_seconds)
    log('[Ollama] API gotowe.' if ready else '[Ollama] Brak odpowiedzi API. Zobacz %LOCALAPPDATA%\\Ollama\\server.log.')
    return ready
