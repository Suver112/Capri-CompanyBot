"""Capri voice capture for Parakeet TDT v3.

Independent implementation: local capture with speech pre-roll and adaptive
endpointing. No service or network calls. Hands-free mode is controlled by the
application, and must be explicitly enabled on every launch.
"""
from __future__ import annotations

from collections import deque
import io
import math
import threading
import time
import wave

import numpy as np


class SpeechGate:
    """Adaptive, bounded speech segmenter (20ms mono PCM16 frames)."""

    def __init__(self, sample_rate: int = 16000, *, pause_ms: int = 900,
                 pre_roll_ms: int = 420, max_seconds: float = 20.0,
                 wake_mode: bool = False):
        if sample_rate < 8000:
            raise ValueError('Invalid sample rate')
        self.sample_rate = int(sample_rate)
        self.wake_mode = bool(wake_mode)
        self.frame_ms = 20
        self.block = max(1, round(self.sample_rate * self.frame_ms / 1000))
        self.pre = deque(maxlen=max(1, math.ceil(pre_roll_ms / self.frame_ms)))
        self.min_voice_frames = 4 if self.wake_mode else 5  # 80/100 ms sustained speech
        self.end_frames = max(1, math.ceil(pause_ms / self.frame_ms))
        self.max_frames = max(1, int(max_seconds * 1000 / self.frame_ms))
        self.noise = 95.0
        self.frames_before = 0
        self.voiced_run = 0
        self.quiet_run = 0
        self.voiced_frames = 0
        self.recorded: list[np.ndarray] = []
        self.started = False
        self.done = False
        self.pending = np.empty(0, dtype=np.int16)

    def _frame(self, frame: np.ndarray) -> None:
        if self.done:
            return
        v = frame.astype(np.float32)
        rms = float(np.sqrt(np.mean(v*v)))
        # A relative threshold rejects steady fan/computer noise; the absolute
        # floor prevents very quiet mic hiss from starting a recording.
        gate = max(145.0 if self.wake_mode else 175.0,
                   self.noise * (2.0 if self.wake_mode else 2.35))
        audible = rms >= gate and float(np.max(np.abs(v))) > (230.0 if self.wake_mode else 280.0)
        if not self.started:
            self.frames_before += 1
            self.pre.append(frame.copy())
            self.voiced_run = self.voiced_run + 1 if audible else max(0, self.voiced_run - 2)
            # Update noise only outside potential voice; do not let a user's
            # first syllable establish the noise baseline.
            if not audible:
                self.noise = max(35., min(5000., 0.96*self.noise + 0.04*rms))
            if self.voiced_run >= self.min_voice_frames:
                self.started = True
                self.recorded.extend(self.pre)
                self.pre.clear()
                self.voiced_frames = self.voiced_run
            return
        self.recorded.append(frame.copy())
        if audible:
            self.voiced_frames += 1
            self.quiet_run = 0
        else:
            self.quiet_run += 1
            self.noise = max(35., min(5000., 0.995*self.noise + 0.005*rms))
        # If a short click was mistaken for voice, reset and continue listening.
        if self.quiet_run >= self.end_frames and self.voiced_frames < 10:
            self.started = False
            self.recorded.clear()
            self.quiet_run = 0
            self.voiced_frames = 0
            self.voiced_run = 0
            return
        if self.quiet_run >= self.end_frames or len(self.recorded) >= self.max_frames:
            self.done = True

    def feed(self, samples) -> bool:
        """Feed PCM16 samples; returns True once an utterance is complete."""
        if self.done:
            return True
        arr = np.asarray(samples, dtype=np.int16).reshape(-1)
        if self.pending.size:
            arr = np.concatenate((self.pending, arr))
        whole = len(arr) // self.block * self.block
        for start in range(0, whole, self.block):
            self._frame(arr[start:start+self.block])
            if self.done:
                break
        self.pending = arr[whole:].copy()
        return self.done

    def samples(self) -> np.ndarray:
        if not self.started or not self.recorded:
            return np.empty(0, dtype=np.int16)
        arr = np.concatenate(self.recorded)
        if not self.done and self.pending.size:
            arr = np.concatenate((arr, self.pending))
        return arr


def _wav(data: np.ndarray, sample_rate: int) -> bytes:
    out = io.BytesIO()
    with wave.open(out, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(np.asarray(data, dtype='<i2').tobytes())
    return out.getvalue()


def record_utterance(stop: threading.Event, *, auto_stop: bool = True,
                     seconds_limit: int = 45, wake_mode: bool = False,
                     device_preference=None) -> bytes:
    """Capture one utterance; never keeps more than 0.42 s before speech starts.

    Try native 16kHz first for Parakeet; fall back to the default microphone
    sample rate when a device doesn't expose 16kHz. Explicit stop is honored.
    """
    import sounddevice as sd
    from capri_microphone import resolve_input_device
    device_index = resolve_input_device(sd, device_preference)

    if not auto_stop:
        # Legacy push-to-talk mode: collect full recording until user stops.
        try:
            device = sd.query_devices(device_index, kind='input') if device_index is not None else sd.query_devices(kind='input')
            default_rate = int(device['default_samplerate'])
        except Exception:
            default_rate = 48000
        rate = default_rate if 8000 <= default_rate <= 192000 else 48000
        frames = []
        def capture(indata, _n, _time, _status):
            if not stop.is_set():
                frames.append(indata[:, 0].copy())
        with sd.InputStream(device=device_index, samplerate=rate, channels=1, dtype='int16',
                            callback=capture, blocksize=max(1, rate // 50)):
            stop.wait(seconds_limit)
        return _wav(np.concatenate(frames) if frames else np.empty(0, dtype=np.int16), rate)

    device = sd.query_devices(device_index, kind='input') if device_index is not None else sd.query_devices(kind='input')
    default_rate = int(device.get('default_samplerate', 48000))
    rates = [16000]
    if 8000 <= default_rate <= 192000 and default_rate != 16000:
        rates.append(default_rate)
    last_error = None
    for rate in rates:
        # Wake detection gets more pre-roll and tolerates a natural pause
        # between "Hej" and "Capri"; ordinary dictation stays unchanged.
        gate = (SpeechGate(rate, pause_ms=1380, pre_roll_ms=680,
                           max_seconds=18.0, wake_mode=True)
                if wake_mode else SpeechGate(rate))
        complete = threading.Event()
        def capture(indata, _n, _time, _status):
            if stop.is_set() or complete.is_set():
                return
            if gate.feed(indata[:, 0]):
                complete.set()
        try:
            with sd.InputStream(device=device_index, samplerate=rate, channels=1, dtype='int16',
                                blocksize=max(1, rate // 50), callback=capture):
                end = time.monotonic() + max(1, seconds_limit)
                while not stop.is_set() and not complete.is_set() and time.monotonic() < end:
                    stop.wait(.04)
            return _wav(gate.samples(), rate)
        except sd.PortAudioError as exc:
            last_error = exc
    raise RuntimeError('Mikrofon nie obsługuje wybranej częstotliwości: ' + str(last_error))
