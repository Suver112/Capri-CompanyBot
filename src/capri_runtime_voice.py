"""Choose a working TTS fallback on a clean Windows PC.

No external services are started by this preflight and user assets are never changed.
"""
from __future__ import annotations
from pathlib import Path


def fish_backend_present(program_dir: Path) -> bool:
    """Find installed Fish engine, valid binary pointer and >2.5 GB model.

    A user's portable setup without local Fish weights must not default to s2cpp.
    """
    root = Path(program_dir) / 's2_cpp_engine'
    try:
        path_file = root / 's2-executable.txt'
        model_file = root / 'selected-model.txt'
        if not path_file.is_file() or not model_file.is_file():
            return False
        binary_name = path_file.read_text(encoding='utf-8-sig').strip()
        selected_model = model_file.read_text(encoding='utf-8-sig').strip()
        if not binary_name or not selected_model:
            return False
        executable = Path(binary_name)
        if not executable.is_file():
            return False
        if Path(selected_model).name != selected_model:
            return False
        model = root / 'models' / selected_model
        return model.is_file() and model.stat().st_size > 2_500_000_000
    except (OSError, ValueError):
        return False


def selected_tts_on_start(configured: str, program_dir: Path, *, port_ready=False) -> str:
    if configured != 's2cpp':
        return configured
    if port_ready or fish_backend_present(program_dir):
        return 's2cpp'
    return 'system'
