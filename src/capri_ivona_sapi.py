"""Genuine installed Windows SAPI5 voices, including IVONA if available.

Closed IVONA voice files and training are not supplied by Capri.
"""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time


def _run_powershell(script: str, timeout: int, cancel: threading.Event | None = None) -> str:
    if os.name != 'nt':
        raise RuntimeError('IVONA / SAPI5 jest dostępna tylko na Windows.')
    payload = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    with tempfile.TemporaryFile(mode='w+b') as stdout, tempfile.TemporaryFile(mode='w+b') as stderr:
        proc = subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive',
                                 '-EncodedCommand', payload], stdout=stdout, stderr=stderr,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            start = time.monotonic()
            while proc.poll() is None:
                if cancel is not None and cancel.is_set():
                    proc.kill()
                    raise RuntimeError('Synteza IVONA została przerwana po wyłączeniu głosu.')
                if time.monotonic() - start > timeout:
                    proc.kill()
                    raise TimeoutError('Przekroczono limit czasu Windows SAPI5.')
                time.sleep(.1)
            stdout.seek(0)
            stderr.seek(0)
            message = stdout.read().decode('utf-8', errors='replace').strip()
            errors = stderr.read().decode('utf-8', errors='replace').strip()
            if proc.returncode:
                raise RuntimeError('Windows SAPI5: ' + (errors[-900:] or message[-900:]))
            return message
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()


def list_ivona_voices() -> list[str]:
    script = r'''
$ErrorActionPreference='Stop'
$voice = New-Object -ComObject SAPI.SpVoice
$result = @()
foreach($token in $voice.GetVoices()) {
  $name = $token.GetDescription()
  if($name -match '(?i)ivona') { $result += [string]$name }
}
ConvertTo-Json -InputObject @($result) -Compress
'''
    raw = _run_powershell(script, timeout=25)
    data = json.loads(raw)
    if isinstance(data, str):
        data = [data]
    return [x for x in data if isinstance(x, str) and 'ivona' in x.casefold()]


def synthesize_ivona(text: str, voice_name: str, *, timeout: int = 120,
                     cancel: threading.Event | None = None, rate: int = 0) -> str:
    if not text.strip():
        raise ValueError('Tekst do wypowiedzenia jest pusty.')
    if len(text) > 4000:
        raise ValueError('Wypowiedź jest za długa dla IVONA/SAPI.')
    fd, outpath = tempfile.mkstemp(prefix='capri_ivona_', suffix='.wav')
    os.close(fd)
    encoded_text = base64.b64encode(text.encode('utf-8')).decode('ascii')
    encoded_name = base64.b64encode(voice_name.encode('utf-8')).decode('ascii')
    encoded_path = base64.b64encode(outpath.encode('utf-8')).decode('ascii')
    script = r'''$ErrorActionPreference = 'Stop'
$inputText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('TEXT64'))
$targetVoice = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('NAME64'))
$dest = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('PATH64'))
$voice = New-Object -ComObject SAPI.SpVoice
$chosen = $null
foreach($token in $voice.GetVoices()) {
  $name = $token.GetDescription()
  if(($name -match '(?i)ivona') -and (($targetVoice -eq '') -or ($name -eq $targetVoice))) {
    $chosen = $token
    break
  }
}
if($null -eq $chosen) { throw 'IVONA nie jest zainstalowana (SAPI5 64-bit).' }
$voice.Voice = $chosen
$voice.Rate = RATE_PLACEHOLDER
$stream = New-Object -ComObject SAPI.SpFileStream
try {
  $stream.Open($dest, 3, $false)
  $voice.AudioOutputStream = $stream
  [void]$voice.Speak($inputText, 0)
} finally {
  $stream.Close()
}
'''.replace('TEXT64', encoded_text).replace('NAME64', encoded_name).replace('PATH64', encoded_path).replace('RATE_PLACEHOLDER', str(max(-5, min(6, int(rate)))))
    try:
        _run_powershell(script, timeout=timeout, cancel=cancel)
        if Path(outpath).stat().st_size < 256:
            raise RuntimeError('IVONA nie utworzyła poprawnego WAV.')
        return outpath
    except Exception:
        Path(outpath).unlink(missing_ok=True)
        raise
