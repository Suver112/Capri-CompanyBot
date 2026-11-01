"""Audio intake for the Piper training studio.

A 30+ second recording is routed to the word-aligned Auto STT cutter rather
than being imported as a single poorly labeled training example.
"""
from __future__ import annotations
import math
from pathlib import Path
import re
import shutil
import subprocess
import wave


def audio_duration_seconds(source: str | Path) -> float:
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(str(source))
    if source.suffix.lower() == '.wav':
        try:
            with wave.open(str(source), 'rb') as audio:
                duration = audio.getnframes() / audio.getframerate()
                if math.isfinite(duration) and duration > 0:
                    return duration
        except (wave.Error, OSError, ZeroDivisionError):
            pass
    ffprobe = shutil.which('ffprobe')
    if ffprobe:
        result = subprocess.run([ffprobe, '-v', 'error', '-show_entries',
                                 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                                 str(source)], capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            duration = float(result.stdout.strip())
            if result.returncode == 0 and math.isfinite(duration) and duration > 0:
                return duration
        except ValueError:
            pass
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        result = subprocess.run([ffmpeg, '-hide_banner', '-i', str(source)],
                                capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        found = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', result.stderr)
        if found:
            h, m, sec = found.groups()
            return int(h) * 3600 + int(m) * 60 + float(sec)
    raise RuntimeError(f'Nie można określić czasu nagrania: {source.name}. Sprawdź FFmpeg/FFprobe.')


def partition_piper_imports(sources: list[str], *, max_seconds: float = 30.0):
    """Unknown durations fail visibly instead of silently losing a long file."""
    short, long = [], []
    for source in sources:
        duration = audio_duration_seconds(source)
        if duration > max_seconds:
            long.append(source)
        else:
            short.append(source)
    return short, long
