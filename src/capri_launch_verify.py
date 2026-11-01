"""Post-launch verification. Never claim Steam launched a game from steam.exe alone."""
from __future__ import annotations

import csv
import io
from pathlib import Path
import subprocess
import sys
import time


def check_process(pid: int, expected_exe: str, *, runner=None) -> bool:
    """Windows tasklist PID + expected filename; fail closed on errors."""
    if sys.platform != 'win32' or not isinstance(pid, int) or pid <= 0:
        return False
    expected = Path(expected_exe).name.casefold()
    if not expected.endswith('.exe'):
        return False
    runner = runner or subprocess.run
    try:
        output = runner(['tasklist.exe', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        timeout=5, shell=False)
        if output.returncode != 0:
            return False
        text = output.stdout.decode('mbcs', errors='replace')
        for row in csv.reader(io.StringIO(text)):
            if len(row) > 1 and row[0].casefold() == expected and row[1].strip() == str(pid):
                return True
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return False


def verify_launch_result(result: dict, *, delay=.75, probe=None) -> dict:
    """Confirm an .exe process survives shortly after launch; unknown otherwise.

    For Steam/UWP/shortcuts a launcher PID is NOT game-process confirmation.
    """
    if not isinstance(result, dict) or result.get('status') != 'command_sent':
        return result
    verified = dict(result)
    if verified.get('launch_type') != 'executable' or not verified.get('process_pid'):
        verified['verification'] = 'unavailable_for_launcher'
        verified['verified_running'] = False
        return verified
    if delay > 0:
        time.sleep(min(delay, 2))
    checker = probe or check_process
    running = bool(checker(verified['process_pid'], verified.get('target','')))
    verified['verified_running'] = running
    verified['verification'] = 'process_seen' if running else 'process_not_observed'
    return verified


def launch_report(result: dict, *, language='pl') -> str:
    name = str(result.get('opened','aplikacja'))[:100]
    if result.get('verified_running'):
        return (f'Proces „{name}” jest uruchomiony (sprawdzony PID). ' 
                'Nie potwierdza to jeszcze, że gra zakończyła ładowanie.')
    if result.get('status') == 'command_sent':
        return (f'Wysłałem polecenie uruchomienia „{name}”, ale nie mam ' 
                'potwierdzenia działania samej gry. Sprawdź, czy pojawiła się na ekranie.')
    return 'Brak potwierdzonego uruchomienia.'
