"""Local Fish S2-Pro GGUF client for s2.cpp HTTP/Vulkan backend.

No cloud calls: connects only to 127.0.0.1. Uses the main reference and
its exact transcription saved by Capri. Requires a separately built s2.cpp
server (not a copy of Fish's Python msgpack API).
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import socket
import struct
import threading
import time
from array import array
import sys
import tempfile
import re
import urllib.error
import urllib.request
import uuid
import wave

from fish_bridge import fish_reference_path
from fish_emotions import fish_emotional_text
from voice_clone import clean_speech_text
from capri_tts_language import prepare_fish_chunks
from capri_voice_cache import audio_key, cached_audio, save_audio
from capri_fish_profiles import cached_profile, note_profile_server_failure, usable_profile

DEFAULT_S2_PORT = 3030
MAX_WAV_BYTES = 100 * 1024 * 1024
# A single local Fish server can synthesize only one request at a time. The
# lock also prevents two background TTS jobs from this Capri process racing.
_FISH_REQUEST_LOCK = threading.Lock()
FISH_BUSY_WAIT_SECONDS = 120.0


class FishSynthesisCancelled(RuntimeError):
    """Expected when an obsolete utterance is interrupted by a new turn."""


def _check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise FishSynthesisCancelled('Przerwano poprzednią syntezę Fish.')


def _wait_cancelable(seconds: float, cancel):
    if cancel is None:
        time.sleep(seconds)
    elif cancel.wait(seconds):
        raise FishSynthesisCancelled('Przerwano poprzednią syntezę Fish.')


def _fish_request_with_busy_retry(request_fn, *, cancel=None, wait_seconds=FISH_BUSY_WAIT_SECONDS):
    """Serialize in-process POSTs and wait on an external client's HTTP 503.

    Never resubmit completed generations: only 503 (request rejected as busy)
    is retried. Failed HTTP 4xx/5xx (other than 503) and network errors escape.
    Cancellation interrupts waiting and is checked after blocking I/O finishes.
    """
    deadline = time.monotonic() + max(0.0, float(wait_seconds))
    while True:
        _check_cancel(cancel)
        if _FISH_REQUEST_LOCK.acquire(timeout=0.2):
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Fish nadal przetwarza wcześniejsze nagranie. Spróbuj ponownie za chwilę.')
    try:
        delay = 0.6
        while True:
            _check_cancel(cancel)
            try:
                result = request_fn()
                _check_cancel(cancel)
                return result
            except urllib.error.HTTPError as exc:
                if exc.code != 503:
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError(
                        'Fish S2.cpp nadal jest zajęty (HTTP 503) po oczekiwaniu. '
                        'Sprawdź, czy nie trwa inna synteza lub czy serwer nie utknął.'
                    ) from exc
                _wait_cancelable(min(delay, remaining), cancel)
                delay = min(delay * 1.65, 4.0)
    finally:
        _FISH_REQUEST_LOCK.release()


def _base_url(port: int) -> str:
    port = int(port)
    if not (1024 <= port <= 65535):
        raise ValueError("s2.cpp: nieprawidłowy port")
    return f"http://127.0.0.1:{port}"


def s2_port_ready(port: int = DEFAULT_S2_PORT, timeout: float = 1.5) -> bool:
    # s2.cpp documents POST /generate; do NOT probe Fish Python /v1/health.
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def _multipart(fields: dict[str, str], ref: Path | None = None) -> tuple[bytes, str]:
    boundary = "----CapriS2" + uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n"
                     "Content-Type: text/plain; charset=utf-8\r\n\r\n").encode())
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")
    if ref is not None:
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"reference\"; "
                     f"filename=\"{ref.name}\"\r\nContent-Type: audio/wav\r\n\r\n").encode())
        if ref.stat().st_size > 25 * 1024 * 1024:
            raise ValueError("Próbka s2.cpp jest za długa. Wybierz 5–30 sekund.")
        body.extend(ref.read_bytes())
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def _check_wav(payload: bytes) -> tuple[int, int, int, bytes]:
    """Decode PCM WAV or IEEE float32 WAV from s2.cpp to PCM16."""
    if len(payload) < 12 or payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise RuntimeError("s2.cpp nie zwrócił pliku WAV (RIFF/WAVE).")
    offset = 12
    fmt = None
    audio = None
    while offset + 8 <= len(payload):
        tag = payload[offset:offset + 4]
        size = struct.unpack_from("<I", payload, offset + 4)[0]
        start = offset + 8
        end = start + size
        if end > len(payload):
            raise RuntimeError("s2.cpp zwrócił ucięty WAV.")
        if tag == b"fmt ":
            if size < 16:
                raise RuntimeError("s2.cpp: niepełny nagłówek WAV.")
            fmt = struct.unpack_from("<HHIIHH", payload, start)
        elif tag == b"data":
            audio = payload[start:end]
        offset = end + (size & 1)
    if fmt is None or audio is None:
        raise RuntimeError("s2.cpp: brak sekcji fmt/data w WAV.")
    encoding, channels, rate, _bitrate, block_align, bits = fmt
    if not (1 <= channels <= 2 and 8000 <= rate <= 192000):
        raise RuntimeError("s2.cpp: nieobsługiwane kanały lub częstotliwość WAV.")
    if encoding == 3 and bits == 32:  # IEEE float32, s2.cpp native output
        if len(audio) % 4:
            raise RuntimeError("s2.cpp: niepełne próbki float32.")
        samples = array("h")
        for (value,) in struct.iter_unpack("<f", audio):
            if value != value:  # NaN
                value = 0.0
            value = max(-1.0, min(1.0, value))
            samples.append(max(-32768, min(32767, round(value * 32768))))
        if sys.byteorder != "little":
            samples.byteswap()
        audio = samples.tobytes()
        width = 2
    elif encoding == 1 and bits in (8, 16, 24, 32):
        width = bits // 8
    else:
        raise RuntimeError(f"s2.cpp: nieobsługiwany format WAV (kod={encoding}, bits={bits}).")
    if len(audio) < rate * channels * width // 5:
        raise RuntimeError("s2.cpp zwrócił zbyt krótki dźwięk (poniżej 0,2 s).")
    return channels, width, rate, audio




def _smooth_fish_chunks(text: str, language: str) -> list[tuple[str, str]]:
    """Keep punctuation *inside* one synthesis unit instead of a cut after every sentence.

    Long units may still drift in tempo due to the Fish model itself; keeping
    several short phrases together avoids stitching at ordinary commas/full stops.
    """
    pieces = prepare_fish_chunks(text, language, max_len=175)
    joined: list[tuple[str, str]] = []
    for chunk, locale in pieces:
        if joined and joined[-1][1] == locale and len(joined[-1][0]) + 1 + len(chunk) <= 185:
            prev, _ = joined.pop()
            joined.append((prev.rstrip() + ' ' + chunk.lstrip(), locale))
        else:
            joined.append((chunk, locale))
    return joined


def _trim_pcm16_boundaries(pcm: bytes, channels: int, rate: int) -> bytes:
    """Trim only excessive leading/trailing silence; preserve natural micro-pauses."""
    if not pcm or len(pcm) % (2 * channels):
        return pcm
    samples = array('h')
    samples.frombytes(pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    step = max(1, rate // 100) * channels   # 10ms frames
    if len(samples) < step * 15:
        return pcm
    quiet_threshold = 180   # ~ -45 dBFS; do not silence whispery speech interior
    start = 0
    stop = len(samples)
    while start + step < stop and max(abs(v) for v in samples[start:start+step]) < quiet_threshold:
        start += step
    while stop - step > start and max(abs(v) for v in samples[stop-step:stop]) < quiet_threshold:
        stop -= step
    margin = int(rate * .035) * channels
    start = max(0, start - margin)
    stop = min(len(samples), stop + margin)
    if not start and stop == len(samples):
        return pcm
    kept = samples[start:stop]
    if sys.byteorder != 'little':
        kept.byteswap()
    return kept.tobytes()


def _join_smooth_audio(chunks: list[bytes], channels: int, sample_width: int,
                       rate: int) -> bytes:
    """Keep every original sample, then add tiny pauses and a decoder-safe tail.

    Previous joining trimmed boundaries and crossfaded away the final 18 ms
    of each segment. This could eat quiet Polish consonants. No source frame
    is removed now; a short silent tail allows Qt/Windows to finish playback.
    """
    if not chunks:
        raise ValueError("Fish nie zwrócił fragmentów audio")
    if not (1 <= channels <= 2 and 1 <= sample_width <= 4 and rate >= 8000):
        raise ValueError("Fish zwrócił błędny format audio")
    frame_size = channels * sample_width
    if any(len(part) % frame_size for part in chunks):
        raise ValueError("Fish zwrócił niepełną ramkę audio")
    gap = bytes(int(rate * .045) * frame_size)
    tail = bytes(int(rate * .18) * frame_size)
    return gap.join(chunks) + tail

def synthesize_s2cpp(text: str, lang: str, reference_path: str, transcript: str,
                     *, transcript_reference_path: str = "", port: int = DEFAULT_S2_PORT,
                     progress=None, timeout: int = 900, profile: str = "clear",
                     whisper: bool = False, emotion_intensity: int = 65,
                     auto_emotions: bool = True, forced_emotion: str | None = None,
                     reuse_audio: bool = False, cancel=None) -> str:
    _check_cancel(cancel)
    if lang not in ("pl", "en"):
        raise ValueError("s2.cpp: wymagany język PL lub EN")
    ref = Path(fish_reference_path(reference_path)).resolve()
    transcript = (transcript or "").strip()
    if not transcript or not transcript_reference_path:
        raise ValueError("s2.cpp wymaga transkrypcji GŁÓWNEJ próbki. Kliknij AUTO STT i sprawdź tekst.")
    if Path(transcript_reference_path).resolve() != ref:
        raise ValueError("Transkrypcja nie pasuje do próbki. Użyj AUTO STT dla GŁÓWNEJ próbki.")
    # Reuse the complete saved utterance before starting Fish. Persisted WAVs
    # work across process restarts and while the Vulkan server is offline.
    full_key = None
    if reuse_audio:
        try:
            full_key = audio_key(text, lang, str(ref), transcript,
                                 transcript_reference_path=transcript_reference_path,
                                 profile=profile, whisper=whisper,
                                 emotion_intensity=emotion_intensity,
                                 auto_emotions=auto_emotions,
                                 forced_emotion=forced_emotion, cache_scope='utterance')
            hit = cached_audio(full_key)
            if hit:
                if progress: progress('s2_cache_hit')
                return hit
        except (OSError, ValueError):
            full_key = None
    if not s2_port_ready(port):
        raise RuntimeError("Serwer s2.cpp Vulkan nie działa na 127.0.0.1:%s. "
                           "Uruchom URUCHOM_CAPRI.vbs, bez WSL." % port)
    if progress:
        progress("s2_load")
    # Convert numbers and embedded foreign names ONLY in the voice track.
    # Keep fully English sentences intact; preserve original chat messages.
    chunks = _smooth_fish_chunks(clean_speech_text(text), lang)
    if not chunks:
        raise ValueError("Brak tekstu do odczytu")
    if len(chunks) > 300:
        raise ValueError("Wypowiedź jest zbyt długa dla jednego generowania (300 fragmentów). Niczego nie ucięto; podziel ją na mniejsze wiadomości.")
    # Reuse an existing encoded voice, but NEVER launch a second CPU-only
    # s2.exe during GPU synthesis. The HTTP server can encode the reference
    # WAV itself on its Vulkan/CUDA backend when no profile is cached.
    voice_profile = cached_profile(ref, transcript, program_root=Path(__file__).resolve().parent)
    if progress and usable_profile(voice_profile):
        progress('s2_profile_reuse')
    all_frames = []
    format_spec = None
    for i, (chunk, chunk_lang) in enumerate(chunks, 1):
        _check_cancel(cancel)
        if progress:
            progress(f"s2_chunk:{i}/{len(chunks)}")
        # Sentence-level reuse: a banked phrase can be part of a new, longer
        # AI-generated reply without substituting any different spoken words.
        # Only exact matching speech chunks + identical voice settings count.
        chunk_key = None
        if reuse_audio:
            try:
                chunk_key = audio_key(
                    chunk, chunk_lang, str(ref), transcript,
                    transcript_reference_path=transcript_reference_path,
                    profile=profile, whisper=whisper,
                    emotion_intensity=emotion_intensity, auto_emotions=auto_emotions,
                    forced_emotion=forced_emotion)
                hit = cached_audio(chunk_key)
                if hit:
                    with wave.open(hit, 'rb') as cached:
                        chunk_spec = (cached.getnchannels(), cached.getsampwidth(), cached.getframerate())
                        chunk_frames = cached.readframes(cached.getnframes())
                    if format_spec is None:
                        format_spec = chunk_spec
                    if chunk_spec == format_spec:
                        all_frames.append(chunk_frames)
                        continue
            except (OSError, ValueError, wave.Error):
                chunk_key = None
        expressive = fish_emotional_text(chunk, chunk_lang, intensity=emotion_intensity,
                                         whisper=whisper, enabled=auto_emotions,
                                         forced_emotion=forced_emotion)
        params = {"max_new_tokens": 1024, "temperature": 0.60 if str(profile).startswith("clear") else 0.69,
                  "top_p": 0.85, "top_k": 35, "stream": False, "chunked": False}
        def send(use_voice: bool):
            if use_voice:
                fields = {"text": expressive, "voice": voice_profile.name,
                          "voice_dir": str(voice_profile.folder), "params": json.dumps(params)}
                body, content_type = _multipart(fields)
            else:
                fields = {"text": expressive, "reference_text": transcript,
                          "params": json.dumps(params)}
                body, content_type = _multipart(fields, ref)
            req = urllib.request.Request(_base_url(port) + "/generate", data=body,
                                         headers={"Content-Type": content_type,
                                                  "Accept": "audio/wav"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read(MAX_WAV_BYTES + 1)

        def generate_once():
            try:
                return send(usable_profile(voice_profile))
            except urllib.error.HTTPError as exc:
                # Legacy s2.cpp may reject an encoded voice profile. Only these
                # protocol errors justify falling back to a WAV reference.
                profile_error = (usable_profile(voice_profile) and exc.code in (400, 422, 500))
                if not profile_error:
                    raise
                note_profile_server_failure(voice_profile, exc.code)
                if progress:
                    progress('s2_profile_fallback')
                return send(False)

        try:
            payload = _fish_request_with_busy_retry(generate_once, cancel=cancel)
        except urllib.error.HTTPError as exc:
            problem = exc.read(900).decode("utf-8", "replace")
            raise RuntimeError(f"s2.cpp HTTP {exc.code}: {problem}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("s2.cpp: błąd lokalnego serwera Vulkan: " + str(exc)) from exc
        _check_cancel(cancel)
        if len(payload) > MAX_WAV_BYTES:
            raise RuntimeError("Zbyt duża odpowiedź WAV")
        c, w, r, frames = _check_wav(payload)
        spec = (c, w, r)
        if format_spec is None:
            format_spec = spec
        if spec != format_spec:
            raise RuntimeError("s2.cpp zwrócił fragmenty WAV o różnych formatach")
        all_frames.append(frames)
        if chunk_key is not None:
            # WAV cache is also populated by normal, non-prerendered replies.
            # Cache failures never break the live TTS response.
            fd_chunk, path_chunk = tempfile.mkstemp(prefix='capri_chunk_', suffix='.wav')
            try:
                with os.fdopen(fd_chunk, 'wb') as output:
                    with wave.open(output, 'wb') as wav:
                        wav.setnchannels(c)
                        wav.setsampwidth(w)
                        wav.setframerate(r)
                        wav.writeframes(frames)
                try:
                    save_audio(chunk_key, path_chunk)
                except (OSError, ValueError):
                    pass
            finally:
                try:
                    os.unlink(path_chunk)
                except OSError:
                    pass
    c, w, r = format_spec
    audio = _join_smooth_audio(all_frames, c, w, r)
    fd, outpath = tempfile.mkstemp(prefix="capri_s2cpp_", suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as raw:
            with wave.open(raw, "wb") as target:
                target.setnchannels(c)
                target.setsampwidth(w)
                target.setframerate(r)
                target.writeframes(audio)
        if full_key is not None:
            try:
                stored_path = save_audio(full_key, outpath)
                Path(outpath).unlink(missing_ok=True)
                return stored_path
            except (OSError, ValueError):
                pass  # A read-only/full cache must not suppress live TTS.
        return outpath
    except BaseException:
        try:
            os.unlink(outpath)
        except OSError:
            pass
        raise
