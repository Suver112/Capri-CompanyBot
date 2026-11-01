"""Prepare a separate user-selected Fish Cloud voice reference; never overwrite Fish S2 primary WAV."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
import wave
from pathlib import Path
from capri_paths import data_root
from voice_clone import ffmpeg_path, SUPPORTED_EXTENSIONS


def prepare_custom_fish_sample(source: str) -> str:
    path = Path(source).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError('Wybierz plik audio/wideo w obsługiwanym formacie.')
    if path.stat().st_size > 1024 * 1024 * 1024:
        raise ValueError('Wybrany plik przekracza 1 GB.')
    # File identity includes mtime/size, avoiding stale transcripts after changing the source.
    stamp = f'{path}:{path.stat().st_size}:{path.stat().st_mtime_ns}'
    digest = hashlib.sha256(stamp.encode('utf-8')).hexdigest()[:18]
    folder = data_root() / 'voices' / 'fish_cloud_custom'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (digest + '.wav')
    if target.is_file() and target.stat().st_size > 20000:
        return str(target)
    fd, temp = tempfile.mkstemp(suffix='.wav', prefix='fish_custom_', dir=str(folder))
    os.close(fd)
    try:
        proc = subprocess.run([ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-y',
                               '-i', str(path), '-t', '16', '-map', '0:a:0', '-vn',
                               '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', temp],
                              capture_output=True, text=True, timeout=120, check=False,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if proc.returncode:
            raise RuntimeError('FFmpeg nie mógł wyodrębnić próbki: ' + proc.stderr[-300:])
        with wave.open(temp, 'rb') as handle:
            length = handle.getnframes() / max(1, handle.getframerate())
            if not 3 <= length <= 16.05:
                raise ValueError('Próbka musi zawierać 3–16 sekund mowy.')
        if Path(temp).stat().st_size > 25 * 1024 * 1024:
            raise ValueError('Próbka przekracza limit 25 MB Fish Audio.')
        os.replace(temp, target)
        return str(target)
    finally:
        Path(temp).unlink(missing_ok=True)
