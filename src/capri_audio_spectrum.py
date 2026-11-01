"""FFT spectrum from the *actual* PCM waveform played by Capri.

Pure NumPy + stdlib module: no Qt, audio device, internet or additional runtime.
Generate 30 Hz frames outside the GUI thread and index them with the player's
actual position. This is not a procedural animation or a microphone simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import struct
import wave

import numpy as np

BARS = 61
FRAMES_PER_SECOND = 30
MAX_WAV_BYTES = 96 * 1024 * 1024
MAX_DURATION_SECONDS = 10 * 60


@dataclass(frozen=True)
class Spectrum:
    """Amplitude per logarithmic frequency band, 0..1, at 30 frames/second."""
    values: np.ndarray
    frame_rate: int = FRAMES_PER_SECOND

    def at_ms(self, position_ms: int) -> np.ndarray:
        index = max(0, int(position_ms * self.frame_rate / 1000))
        if index >= len(self.values):
            return np.zeros(self.values.shape[1], dtype=np.float32)
        return self.values[index]


def pcm_to_mono(data: bytes, sample_width: int, channels: int, *, float_pcm=False) -> np.ndarray:
    """Read interleaved PCM samples; 24-bit and IEEE float WAV are supported."""
    if channels < 1 or channels > 16:
        raise ValueError('Invalid WAV channel count')
    if sample_width == 1 and not float_pcm:
        samples = (np.frombuffer(data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2 and not float_pcm:
        samples = np.frombuffer(data, dtype='<i2').astype(np.float32) / 32768.0
    elif sample_width == 3 and not float_pcm:
        b = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
        value = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) |
                 (b[:, 2].astype(np.int32) << 16))
        signed = (value ^ 0x800000) - 0x800000
        samples = signed.astype(np.float32) / 8388608.0
    elif sample_width == 4 and not float_pcm:
        samples = np.frombuffer(data, dtype='<i4').astype(np.float32) / 2147483648.0
    elif sample_width == 4 and float_pcm:
        samples = np.frombuffer(data, dtype='<f4').astype(np.float32)
    elif sample_width == 8 and float_pcm:
        samples = np.frombuffer(data, dtype='<f8').astype(np.float32)
    else:
        raise ValueError('Unsupported WAV sample format')
    if samples.size % channels:
        raise ValueError('Incomplete WAV PCM frame')
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    np.nan_to_num(samples, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(samples, -1.0, 1.0)


def _read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """PCM WAV via stdlib; fallback parser for IEEE-float/extensible WAV.

    No soundfile dependency. Keep reads bounded so unexpected giant input files
    cannot freeze or exhaust the analyzer worker.
    """
    path = Path(path)
    if path.stat().st_size > MAX_WAV_BYTES:
        raise ValueError('WAV exceeds visualizer safety limit')
    try:
        with wave.open(str(path), 'rb') as wav:
            sr, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
            if sr < 8000 or sr > 384000:
                raise ValueError('Invalid WAV sample rate')
            maximum = min(wav.getnframes(), sr * MAX_DURATION_SECONDS)
            raw = wav.readframes(maximum)
        return pcm_to_mono(raw, width, channels), sr
    except wave.Error:
        pass  # Python 3.11 rejects IEEE_FLOAT and some WAVE_FORMAT_EXTENSIBLE files.
    blob = path.read_bytes()
    if len(blob) < 12 or blob[:4] != b'RIFF' or blob[8:12] != b'WAVE':
        raise ValueError('Not a RIFF WAVE audio file')
    offset = 12
    fmt = None
    data = None
    while offset + 8 <= len(blob):
        tag, length = struct.unpack_from('<4sI', blob, offset)
        offset += 8
        if length > len(blob) - offset:
            raise ValueError('Incomplete WAV chunk')
        if tag == b'fmt ' and length >= 16:
            fmt = blob[offset:offset + length]
        elif tag == b'data':
            data = memoryview(blob)[offset:offset + length]
            if fmt is not None:
                break
        offset += length + (length & 1)
    if fmt is None or data is None:
        raise ValueError('Missing WAV format/audio data')
    codec, ch, sr, _, block_align, bits = struct.unpack_from('<HHIIHH', fmt)
    if codec == 0xFFFE and len(fmt) >= 40:
        codec = struct.unpack_from('<I', fmt, 24)[0]  # WAVE_FORMAT_EXTENSIBLE subformat
    if codec not in (1, 3) or bits % 8:
        raise ValueError('Unsupported compressed WAV audio')
    width = bits // 8
    if block_align != ch * width or sr < 8000 or sr > 384000:
        raise ValueError('Invalid WAV format')
    length = min(len(data) // block_align, sr * MAX_DURATION_SECONDS)
    return pcm_to_mono(bytes(data[:length * block_align]), width, ch, float_pcm=codec == 3), sr


def spectrum_from_samples(samples: np.ndarray, sample_rate: int, *, bands: int = BARS,
                          frame_rate: int = FRAMES_PER_SECOND) -> Spectrum:
    """Short-time FFT, logarithmic bands, absolute silence gate, clip-relative scale.

    No fake oscillation: all displayed heights derive from the signal spectrum.
    Normalization is global for the clip to avoid pumping and keep bands stable.
    """
    if sample_rate < 8000 or bands < 2 or frame_rate < 1:
        raise ValueError('Invalid FFT analysis parameters')
    mono = np.asarray(samples, dtype=np.float32)
    if mono.ndim != 1:
        raise ValueError('Expected mono samples')
    max_samples = min(mono.size, int(sample_rate * MAX_DURATION_SECONDS))
    mono = mono[:max_samples]
    if mono.size == 0:
        return Spectrum(np.zeros((1, bands), dtype=np.float32), frame_rate)
    # ~85 ms windows: enough pitch resolution for speech, responsive to consonants.
    nfft = 2 ** int(round(math.log2(sample_rate * 0.085)))
    nfft = max(1024, min(8192, nfft))
    hop = sample_rate / frame_rate
    num_frames = max(1, int(math.ceil(mono.size / hop)))
    window = np.hanning(nfft).astype(np.float32)
    hz = np.fft.rfftfreq(nfft, 1 / sample_rate)
    high = min(8500, sample_rate * 0.48)
    edges = np.geomspace(75, high, bands + 1)
    # Small bass bands may map to the same FFT bin; this is truthful resolution,
    # not invented extra frequencies.
    mappings = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        start = int(np.searchsorted(hz, lo, side='left'))
        stop = int(np.searchsorted(hz, hi, side='right'))
        start = min(start, len(hz) - 1)
        stop = max(start + 1, min(stop, len(hz)))
        mappings.append((start, stop))
    raw = np.zeros((num_frames, bands), dtype=np.float32)
    rms = np.zeros(num_frames, dtype=np.float32)
    frame = np.zeros(nfft, dtype=np.float32)
    half = nfft // 2
    scale = 2.0 / max(float(window.sum()), 1.0)
    for i in range(num_frames):
        center = int(i * hop)
        start = center - half
        lo = max(0, start)
        hi = min(mono.size, start + nfft)
        frame.fill(0)
        if lo < hi:
            frame[lo - start:hi - start] = mono[lo:hi]
        rms[i] = float(np.sqrt(np.mean(frame * frame)))
        if rms[i] < 0.0003:
            continue
        spectrum = np.abs(np.fft.rfft(frame * window)) * scale
        for j, (left, right) in enumerate(mappings):
            power = spectrum[left:right]
            raw[i, j] = float(np.sqrt(np.mean(power * power)))
    # Logarithmic compression preserves quiet consonants without oscillations.
    high_level = float(np.percentile(raw.max(axis=1), 90))
    if high_level > 1e-7:
        factor = 16.0 / high_level
        result = np.log1p(raw * factor) / math.log1p(16.0)
        result = np.clip(result, 0, 1).astype(np.float32)
        # Gate true silence and near-silence; do not animate when nothing sounds.
        gate = np.maximum(0.0005, float(rms.max()) * 0.022)
        result[rms < gate] = 0
    else:
        result = raw
    result.setflags(write=False)
    return Spectrum(result, frame_rate)


def spectrum_from_wav(path: str | Path) -> Spectrum:
    samples, sample_rate = _read_wav(path)
    return spectrum_from_samples(samples, sample_rate)
