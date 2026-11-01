"""Optional accelerator selection. All checks are lazy and never install anything.

CAPRI_GPU_BACKEND=auto (default), cpu or cuda.  A missing/unusable CUDA
runtime must not make Capri unusable on AMD, Intel or CPU-only computers.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache


def preference() -> str:
    value = os.environ.get('CAPRI_GPU_BACKEND', 'auto').strip().casefold()
    return value if value in ('auto', 'cpu', 'cuda') else 'auto'


@lru_cache(maxsize=1)
def nvidia_driver() -> bool:
    if preference() == 'cpu' or not shutil.which('nvidia-smi'):
        return False
    try:
        result = subprocess.run(['nvidia-smi', '-L'], capture_output=True,
                                text=True, encoding='utf-8', errors='replace',
                                timeout=4, check=False)
        return result.returncode == 0 and 'GPU ' in result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


@lru_cache(maxsize=1)
def whisper_cuda_ready() -> bool:
    """Check CTranslate2's CUDA runtime, not only the name of the GPU."""
    if preference() == 'cpu' or not nvidia_driver():
        return False
    try:
        import ctranslate2
        count = ctranslate2.get_cuda_device_count()
        if count < 1:
            return False
        types = ctranslate2.get_supported_compute_types('cuda')
        return bool({'float16', 'int8_float16', 'int8'} & set(types))
    except (ImportError, RuntimeError, OSError, ValueError):
        return False


def whisper_device_kwargs() -> dict:
    if whisper_cuda_ready() and 'whisper' not in _failed_cuda:
        return {'device': 'cuda', 'compute_type': 'float16'}
    return {'device': 'cpu', 'compute_type': 'int8'}


def load_whisper(factory, model_name: str, **kwargs):
    """Attempt CUDA once and fall back to CPU without downloading a new model."""
    options = whisper_device_kwargs()
    try:
        return factory(model_name, **options, **kwargs), options['device']
    except (RuntimeError, OSError, ValueError) as exc:
        if options['device'] != 'cuda':
            raise
        _failed_cuda.add('whisper')
        return factory(model_name, device='cpu', compute_type='int8', **kwargs), 'cpu'


_failed_cuda: set[str] = set()


def onnx_preferred_provider() -> str:
    # sherpa-onnx's CPU wheel does not include the CUDA execution provider.
    # Try CUDA only when a real NVIDIA driver is present, fall back upon error.
    return 'cuda' if nvidia_driver() and 'parakeet' not in _failed_cuda else 'cpu'


def mark_unavailable(engine: str) -> None:
    _failed_cuda.add(engine)


def diagnose() -> dict:
    result = {'preference': preference(), 'nvidia_driver': nvidia_driver(),
              'whisper_device': whisper_device_kwargs()['device'],
              'parakeet_preferred_provider': onnx_preferred_provider(),
              'fish_cuda_binary': False}
    try:
        from pathlib import Path
        from capri_paths import local_root
        engine_dir = Path(__file__).resolve().parent / 's2_cpp_engine'
        index = engine_dir / 's2-executable-cuda.txt'
        result['fish_cuda_binary'] = bool(index.is_file() and
            (index.parent / index.read_text(encoding='utf-8-sig').strip()).is_file())
    except (OSError, ValueError):
        pass
    return result


@lru_cache(maxsize=1)
def fish_cuda_hardware() -> bool:
    """True only for NVIDIA GPUs with a usable CUDA compute capability.

    Do not confuse a CUDA GPU with having a compiled Fish backend installed.
    Conservative for old cards and nvidia-smi versions that cannot report CC.
    """
    if not nvidia_driver():
        return False
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=compute_cap', '--format=csv,noheader'],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=4, check=False)
        if result.returncode != 0:
            return False
        capabilities = []
        for line in result.stdout.splitlines():
            try:
                capabilities.append(float(line.strip()))
            except ValueError:
                continue
        return any(capability >= 5.0 for capability in capabilities)
    except (OSError, subprocess.TimeoutExpired):
        return False


def fish_cuda_binary(script_dir=None) -> bool:
    """CUDA backend is ready only if its indexed executable really exists."""
    from pathlib import Path
    root = Path(script_dir) if script_dir is not None else Path(__file__).resolve().parent
    index = root / 's2_cpp_engine' / 's2-executable-cuda.txt'
    try:
        binary = Path(index.read_text(encoding='utf-8-sig').strip())
        if not binary.is_absolute():
            binary = index.parent / binary
        return binary.is_file() and binary.suffix.lower() == '.exe'
    except (OSError, ValueError):
        return False


def fish_cuda_ready(script_dir=None) -> bool:
    return preference() != 'cpu' and fish_cuda_hardware() and fish_cuda_binary(script_dir)


def available_fish_backends(script_dir=None) -> tuple[str, ...]:
    """Only offer Fish CUDA when the GPU and separately built backend are ready."""
    return ('vulkan', 'cuda') if fish_cuda_ready(script_dir) else ('vulkan',)


def normalize_fish_backend(backend: str, script_dir=None) -> str:
    return 'cuda' if backend == 'cuda' and fish_cuda_ready(script_dir) else 'vulkan'
