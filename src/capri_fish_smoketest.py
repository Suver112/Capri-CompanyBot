"""End-to-end Fish S2.cpp synthesis self-test after Windows installation."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import time
from urllib import request
import wave
import io

def smoke_test(port: int = 3030, timeout: int = 210, reference: Path | None = None):
    from capri_default_voice import ASSETS, SEEDS
    from s2cpp_bridge import _multipart, _check_wav
    ref = reference or ASSETS / SEEDS[0][0]
    if not ref.is_file():
        raise FileNotFoundError('Brak referencji WAV: ' + str(ref))
    text = SEEDS[0][1]
    body, content_type = _multipart({
        'text': 'Cześć.',
        'reference_text': text,
        'params': json.dumps({'max_new_tokens': 200, 'temperature': .6,
                              'top_p': .85, 'top_k': 35, 'stream': False, 'chunked': False})
    }, ref)
    req = request.Request(f'http://127.0.0.1:{port}/generate', data=body,
                          headers={'Content-Type': content_type,
                                   'Accept': 'audio/wav'}, method='POST')
    with request.urlopen(req, timeout=timeout) as response:
        wave_bytes = response.read(25 * 1024 * 1024)
    channels, width, rate, frames = _check_wav(wave_bytes)
    if len(frames) / (channels * width * rate) < .2:
        raise ValueError('Fish nie wygenerował mowy')
    return {'sample_rate': rate, 'seconds': len(frames) / (channels*width*rate)}

def main():
    from capri_paths import local_root
    log = local_root() / 'fish_smoketest.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        info = smoke_test()
        log.write_text('Sukces: ' + repr(info), encoding='utf-8')
        return 0
    except Exception as exc:
        log.write_text(f'Fish generacja nieudana: {type(exc).__name__}: {exc}',
                       encoding='utf-8')
        return 12

if __name__ == '__main__':
    raise SystemExit(main())
