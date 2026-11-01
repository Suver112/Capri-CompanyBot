"""Optional fully local Parakeet TDT v3 speech-to-text via sherpa-onnx.

No model download at runtime. Download deliberately using Napraw Capri (menu Start).
The recognizer is cached to avoid reloading the ~640 MB model for each turn.
"""
from __future__ import annotations
import io
import threading
import wave
from pathlib import Path
import numpy as np
from capri_paths import data_root

MODEL_DIR = data_root() / 'models' / 'parakeet-v3'
MODEL_FILES = ('encoder.int8.onnx', 'decoder.int8.onnx', 'joiner.int8.onnx', 'tokens.txt')
_model = None
_model_lock = threading.Lock()


def missing_files(path: Path = MODEL_DIR) -> list[str]:
    return [name for name in MODEL_FILES if not (path / name).is_file() or (path / name).stat().st_size == 0]


def installed(path: Path = MODEL_DIR) -> bool:
    return not missing_files(path)


def _recognizer():
    global _model
    if _model is None:
        missing = missing_files()
        if missing:
            raise RuntimeError('Brak Parakeet v3 (' + ', '.join(missing) + '). Uruchom Napraw Capri (menu Start).')
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise RuntimeError('Brakuje sherpa-onnx. Uruchom: .venv\\Scripts\\python.exe -m pip install sherpa-onnx') from exc
        from capri_acceleration import onnx_preferred_provider, mark_unavailable
        provider = onnx_preferred_provider()
        def create_with_provider(selected_provider):
            return sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(MODEL_DIR / MODEL_FILES[0]),
            decoder=str(MODEL_DIR / MODEL_FILES[1]),
            joiner=str(MODEL_DIR / MODEL_FILES[2]),
            tokens=str(MODEL_DIR / MODEL_FILES[3]),
            num_threads=4,
            provider=selected_provider,
            decoding_method='greedy_search',
            model_type='nemo_transducer',
            feature_dim=128,
            debug=False,
            )
        try:
            _model = create_with_provider(provider)
        except (RuntimeError, OSError, ValueError) as exc:
            if provider != 'cuda':
                raise
            mark_unavailable('parakeet')
            _model = create_with_provider('cpu')
    return _model


def decode_wav(blob: bytes) -> str:
    """Decode PCM WAV, safely converting multi-channel audio to 16 kHz mono float32."""
    with wave.open(io.BytesIO(blob), 'rb') as wf:
        sr, channels, width = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
        if wf.getcomptype() != 'NONE' or width != 2 or sr <= 0 or channels <= 0:
            raise ValueError('Parakeet wymaga nagrania WAV PCM 16-bit.')
        samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype='<i2')
    if len(samples) < 1600:
        return ''
    samples = samples[:(len(samples)//channels)*channels].reshape(-1, channels).astype(np.float32)
    mono = samples.mean(axis=1) / 32768.0
    if sr != 16000:
        size = int(round(len(mono) * 16000 / sr))
        mono = np.interp(np.arange(size) * (sr/16000), np.arange(len(mono)), mono).astype(np.float32)
    with _model_lock:
        engine = _recognizer()
        stream = engine.create_stream()
        stream.accept_waveform(16000, mono)
        engine.decode_stream(stream)
        return str(stream.result.text).strip()
