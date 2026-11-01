"""Safe last-word playback protection shared by every generated WAV voice engine.

This adds silence AFTER existing audio (does not remove or fade speech samples).
It cannot restore phonemes already omitted by a remote TTS provider.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import wave


def add_safe_tail(source: str | Path, *, tail_ms: int = 260) -> str:
    """Return a temporary PCM WAV with an extra trailing buffer.

    No audio samples are edited. Unsupported files are left untouched for Qt
    to decode. Caller owns the temporary result and should remove it later.
    """
    path = Path(source)
    if path.suffix.lower() != '.wav':
        return str(path)
    tail_ms = max(0, min(int(tail_ms), 700))
    if not tail_ms:
        return str(path)
    try:
        with wave.open(str(path), 'rb') as src:
            params = src.getparams()
            # PCM, one to eight channels, with sane frame properties.
            if src.getcomptype() != 'NONE' or not 8000 <= src.getframerate() <= 192000:
                return str(path)
            if not 1 <= src.getnchannels() <= 8 or not 1 <= src.getsampwidth() <= 4:
                return str(path)
            # Limit input size to avoid pathological memory/disk use.
            if path.stat().st_size > 100 * 1024 * 1024:
                return str(path)
            fd, target = tempfile.mkstemp(prefix='capri_playback_tail_', suffix='.wav')
            os.close(fd)
            try:
                with wave.open(target, 'wb') as out:
                    out.setparams(params)
                    while True:
                        frames = src.readframes(65536)
                        if not frames:
                            break
                        out.writeframes(frames)
                    silence = int(src.getframerate() * tail_ms / 1000) * src.getnchannels() * src.getsampwidth()
                    # 8-bit PCM uses midpoint 128 for silence; all other PCM uses zero.
                    out.writeframes((b'\x80' if src.getsampwidth() == 1 else b'\x00') * silence)
                return target
            except BaseException:
                Path(target).unlink(missing_ok=True)
                raise
    except (OSError, EOFError, wave.Error, ValueError):
        return str(path)
