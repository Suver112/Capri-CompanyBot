"""Fish Audio S2-Pro local server client, isolated from the desktop Python environment.

The client ONLY connects to loopback. It never starts a remote/cloud service.
S2-Pro server requires WSL/Linux, separate installation and significant memory.
Voice cloning needs BOTH the primary WAV and its accurate transcript.
"""
from __future__ import annotations
import os
from pathlib import Path
import tempfile
import urllib.request
import urllib.error
import json
import wave

from voice_clone import resolve_references, clean_speech_text, split_tts_text
from fish_emotions import fish_emotional_text

FISH_PORT = 8080
MAX_OUTPUT_BYTES = 120 * 1024 * 1024


def fish_reference_path(reference_path: str) -> str:
    refs = resolve_references(reference_path)
    if not refs:
        raise RuntimeError("Brak próbki GŁÓWNEJ. Wybierz ją w ZARZĄDZAJ.")
    path = Path(refs[0]).resolve()
    if path.suffix.lower() != ".wav" or not path.is_file():
        raise ValueError("Fish S2-Pro potrzebuje głównej próbki WAV z biblioteki Capri.")
    return str(path)


def _server(port: int) -> str:
    port = int(port)
    if not (1024 <= port <= 65535):
        raise ValueError("Fish: port musi mieć wartość 1024–65535")
    return f"http://127.0.0.1:{port}"


def fish_server_health(port: int = FISH_PORT, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(_server(port) + "/v1/health", timeout=timeout) as r:
            obj = json.loads(r.read(4096).decode("utf-8"))
        return obj.get("status") == "ok"
    except (ValueError, OSError, urllib.error.URLError):
        return False


def _validate_audio(bytestr: bytes):
    if not bytestr.startswith(b"RIFF") or bytestr[8:12] != b"WAVE":
        raise RuntimeError("Fish nie zwrócił pliku WAV. Sprawdź, czy serwer ładuje S2-Pro.")
    import io
    with wave.open(io.BytesIO(bytestr), "rb") as w:
        if w.getnframes() < w.getframerate() // 4:
            raise RuntimeError("Fish wygenerował za krótką wypowiedź")


def synthesize_fish(text: str, lang: str, reference_path: str, transcript: str,
                    *, transcript_reference_path: str = "", port: int = FISH_PORT,
                    progress=None, timeout: int = 1200, profile: str = "clear",
                    whisper: bool = False, emotion_intensity: int = 65,
                    auto_emotions: bool = True) -> str:
    try:
        import msgpack
    except ImportError as exc:
        raise RuntimeError("Brakuje klienta msgpack (opcjonalny Fish Python/WSL). Zainstaluj msgpack w aktywnym Pythonie.") from exc
    if lang not in ("pl", "en"):
        raise ValueError("Fish: obsługiwane języki Capri: polski i angielski")
    ref = fish_reference_path(reference_path)
    transcript = transcript.strip()
    if not transcript:
        raise ValueError("Fish potrzebuje tekstu próbki głównej: kliknij AUTO STT w ustawieniach, sprawdź i popraw transkrypcję.")
    if transcript_reference_path and Path(transcript_reference_path).resolve() != Path(ref):
        raise ValueError("Zmieniła się próbka GŁÓWNA. Kliknij ponownie AUTO STT, żeby dopasować tekst do nagrania.")
    if not transcript_reference_path:
        raise ValueError("Transkrypcja nie jest przypisana do próbki. Kliknij AUTO STT lub edytuj jej tekst.")
    if not fish_server_health(port):
        raise RuntimeError("Fish S2-Pro nie działa pod 127.0.0.1:%s. Uruchom osobno serwer WSL lub wybierz Fish Vulkan." % port)
    if progress:
        progress("fish_load")
    chunks = split_tts_text(clean_speech_text(text), max_len=170)
    if not chunks:
        raise ValueError("Brak tekstu do odczytania")
    if len(chunks) > 300:
        raise ValueError("Za długa wiadomość do syntezy Fish (300 fragmentów). Niczego nie ucięto.")
    wav_ref = Path(ref).read_bytes()
    if len(wav_ref) > 25 * 1024 * 1024:
        raise ValueError("Próbka WAV jest za długa do Fish S2-Pro. Wybierz klip 5–15 s.")
    # Fish API uses application/msgpack; its reference contains actual audio
    # bytes and EXACT transcription, not a filepath or JSON string.
    paths = []
    for idx, chunk in enumerate(chunks, 1):
        if progress:
            progress(f"fish_chunk:{idx}/{len(chunks)}")
        chunk = fish_emotional_text(
            chunk, lang, intensity=emotion_intensity,
            whisper=whisper, enabled=auto_emotions)
        data = {"text": chunk,
                "references": [{"audio": wav_ref, "text": transcript}],
                "reference_id": None,
                "format": "wav", "streaming": False,
                "temperature": 0.65, "top_p": 0.75,
                "chunk_length": 170}
        packed = msgpack.packb(data, use_bin_type=True)
        url = _server(port) + "/v1/tts?format=msgpack"
        req = urllib.request.Request(url, data=packed, method="POST",
               headers={"Content-Type": "application/msgpack", "Accept": "audio/wav"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                audio = r.read(MAX_OUTPUT_BYTES + 1)
        except urllib.error.HTTPError as exc:
            msg = exc.read(1000).decode("utf-8", "replace")
            raise RuntimeError(f"Fish S2-Pro HTTP {exc.code}: {msg}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Fish S2-Pro: przerwane połączenie z lokalnym WSL: " + str(exc)) from exc
        if len(audio) > MAX_OUTPUT_BYTES:
            raise RuntimeError("Fish zwrócił nieprawidłowo duże nagranie")
        _validate_audio(audio)
        paths.append(audio)
    if len(paths) == 1:
        combined = paths[0]
    else:
        # Joining WAVE chunks with consistent channel/sample rate/bit depth.
        import io
        params = None
        frames = []
        for wav_data in paths:
            with wave.open(io.BytesIO(wav_data), "rb") as reader:
                spec = (reader.getnchannels(),reader.getsampwidth(),reader.getframerate(), reader.getcomptype())
                if params is None:
                    params = spec
                if spec != params:
                    raise RuntimeError("Fish wygenerował fragmenty o różnych parametrach WAV")
                frames.append(reader.readframes(reader.getnframes()))
        silence = b"\0" * int(params[2] * 0.08 * params[0] * params[1])
        output = io.BytesIO()
        with wave.open(output,"wb") as dest:
            dest.setnchannels(params[0]);dest.setsampwidth(params[1]);dest.setframerate(params[2])
            dest.writeframes(silence.join(frames))
        combined = output.getvalue()
    fd, name = tempfile.mkstemp(prefix="capri_fish_s2_", suffix=".wav")
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(combined)
        return name
    except BaseException:
        try: os.unlink(name)
        except OSError: pass
        raise
