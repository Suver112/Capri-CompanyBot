"""Opt-in safe lifecycle management of Capri's own Windows s2.cpp server.

Never kills a process by port alone; only the exact installed engine binary,
with the expected --server --port arguments, may be stopped.
"""
from __future__ import annotations

from capri_paths import local_root
from capri_acceleration import normalize_fish_backend
import os
from pathlib import Path
import subprocess
import threading
import time

_START_LOCK = threading.Lock()
_LAST_START = 0.0


def _engine_binary(script_dir: Path) -> str:
    index = script_dir / 's2_cpp_engine' / 's2-executable.txt'
    if not index.is_file():
        return ''
    raw = index.read_text(encoding='utf-8-sig').strip()
    if not raw:
        return ''
    path = Path(raw)
    return str(path if path.is_absolute() else index.parent / path)


def _engine_binaries(script_dir: Path) -> list[str]:
    result = []
    for filename in ('s2-executable.txt', 's2-executable-cuda.txt'):
        index = script_dir / 's2_cpp_engine' / filename
        if index.is_file():
            exe = index.read_text(encoding='utf-8-sig').strip()
            if exe:
                path = Path(exe)
                result.append(str(path if path.is_absolute() else index.parent / path))
    return result


def stop_fish_server(script_dir: Path) -> None:
    global _LAST_START
    if os.name != 'nt':
        return
    binaries = _engine_binaries(script_dir)
    if not binaries:
        return
    # Use PowerShell CIM to avoid terminating other applications using port 3030.
    # Process::Kill occurs only when ExecutablePath matches Capri's installed binary.
    escaped = [p.replace("'", "''") for p in binaries]
    ps = ("$wanted=@(" + ','.join("[IO.Path]::GetFullPath('"+p+"')" for p in escaped) + "); "
          "Get-CimInstance Win32_Process | Where-Object { "
          "  $_.ExecutablePath -and $_.CommandLine -match '--server' "
          "  -and $_.CommandLine -match '--port\\s+3030' "
          "  -and ($wanted -icontains [IO.Path]::GetFullPath($_.ExecutablePath)) "
          "} | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }")
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps],
                   timeout=20, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    with _START_LOCK:
        _LAST_START = 0.0


def start_fish_server(script_dir: Path, backend: str = "vulkan") -> None:
    if os.name != 'nt':
        return
    from s2cpp_bridge import s2_port_ready
    global _LAST_START
    with _START_LOCK:
        if s2_port_ready(timeout=0.4):
            return
        # The backend takes time to initialize: don't spawn a second copy
        # while the readiness worker is polling the same port.
        if time.monotonic() - _LAST_START < 90:
            return
        if _launch_fish_server(script_dir, backend):
            _LAST_START = time.monotonic()


def _launch_fish_server(script_dir: Path, backend: str = "vulkan") -> bool:
    script = script_dir / 'start_s2_vulkan_windows.ps1'
    if not script.is_file() or not _engine_binary(script_dir):
        return False
    # A detached console is NOT desirable for the desktop overlay. Persist errors
    # to a log instead of hiding them permanently in a new CMD window.
    selected = normalize_fish_backend(backend, script_dir)
    folder = local_root()
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'fish_vulkan.log').open('ab') as log:
        env = os.environ.copy()
        env['CAPRI_FISH_BACKEND'] = selected
        subprocess.Popen(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive',
                          '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden',
                          '-File', str(script)], cwd=str(script_dir),
                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                         env=env,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                         close_fds=True)
    return True


def restart_fish_server(script_dir: Path, backend: str = 'vulkan') -> bool:
    """Restart only Capri's own Fish binary, never kill an arbitrary port owner."""
    global _LAST_START
    stop_fish_server(script_dir)
    from s2cpp_bridge import s2_port_ready
    for _ in range(25):
        if not s2_port_ready(timeout=0.1):
            break
        time.sleep(0.2)
    if s2_port_ready(timeout=0.1):
        return False  # Another process owns the port: do not claim backend change
    with _START_LOCK:
        _LAST_START = 0.0
    start_fish_server(script_dir, backend=backend)
    return True
