"""Separate profile for Capri beta while keeping legacy production paths intact."""
from pathlib import Path
import os


def data_root() -> Path:
    home = Path(os.getenv('APPDATA') or Path.home())
    folder = 'CapriOverlay_Beta' if os.environ.get('CAPRI_PROFILE') == 'beta' else 'CapriOverlay'
    return home / folder


def local_root() -> Path:
    home = Path(os.getenv('LOCALAPPDATA') or Path.home())
    folder = 'CapriOverlay_Beta' if os.environ.get('CAPRI_PROFILE') == 'beta' else 'CapriOverlay'
    return home / folder


def shared_model_root() -> Path:
    """Reuse immutable Whisper weights across beta/stable without copying GBs."""
    base = Path(os.getenv('APPDATA') or Path.home())
    return base / 'CapriOverlay' / 'models'
