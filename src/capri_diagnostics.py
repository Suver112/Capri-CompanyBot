"""Read-only local diagnostics for the beta install. No model downloads."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
from urllib import request as urlrequest

from capri_paths import data_root, local_root

ROOT=Path(__file__).resolve().parent


def tcp_ready(port, host='127.0.0.1', timeout=.5):
    try:
        with socket.create_connection((host,port), timeout=timeout):
            return True
    except OSError:
        return False


def check_ollama(timeout=2):
    try:
        with urlrequest.urlopen('http://127.0.0.1:11434/api/tags',timeout=timeout) as resp:
            data=json.load(resp)
        return [x.get('name','') for x in data.get('models', []) if isinstance(x,dict)]
    except (OSError,ValueError,KeyError):
        return None


def check(*, network=True):
    names=['main.py','capri_agent.py','capri_memory.py','capri_streaming.py',
           'capri_semantic_memory.py','capri_stt_context.py',
           'lore/core_pl.txt','lore/lore_cards.json']
    files={n:(ROOT/n).is_file() for n in names}
    libs={name:importlib.util.find_spec(name) is not None for name in
          ('PySide6','numpy','sounddevice','faster_whisper')}
    ollama = check_ollama() if network else None
    fish = tcp_ready(3030) if network else False
    binary=Path.home()/'cs2b'/'capri168'/'Release'/'s2.exe'
    from capri_acceleration import diagnose as gpu_diagnose
    return {'gpu_acceleration': gpu_diagnose(),
            'version':'0.1.1',
            'release_channel':'Wczesny dostęp',
            'profile':os.environ.get('CAPRI_PROFILE','stable'),
            'python':platform.python_version(),
            'python_path':sys.executable,
            'os':platform.platform(),
            'program_files':files,
            'libs_installed':libs,
            'settings_folder':str(data_root()),
            'startup_log':str(local_root()/'capri_startup.log'),
            'ollama_models':ollama,
            'embedding_model_installed':bool(ollama and any(x.startswith('embeddinggemma:300m') for x in ollama)),
            'fish_port_3030_open':fish,
            'fish_binary_known_path':str(binary),
            'fish_binary_exists':binary.is_file(),
            'note':('Dostepnosc portu nie dowodzi, ze TTS poprawnie generuje dzwiek. '
                    'Bez obecnosci GPU nie mozna przetestowac Vulkan/CUDA.')}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-network',action='store_true')
    args=parser.parse_args()
    result=check(network=not args.no_network)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not all(result['program_files'].values()):
        return 1
    if not all(result['libs_installed'].values()):
        print('Brakuje biblioteki Python. Zainstaluj .venv dla builda beta.')
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
