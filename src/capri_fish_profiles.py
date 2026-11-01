"""Optional reusable Fish S2.cpp voice profiles (no cloud, no cached speech).

A profile contains encoded reference voice features, NOT generated responses.
The upstream s2.cpp HTTP server can load `.s2voice` profiles via its `voice`
form field but cannot create them. We therefore build them once using the CLI.
If preparation fails, the caller must continue with reference-WAV HTTP mode.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass

from capri_paths import local_root

_lock = threading.Lock()
_failed: set[str] = set()  # one attempt per process/profile (avoid repeated costly loads)


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    folder: Path

    @property
    def file(self) -> Path:
        return self.folder / (self.name + '.s2voice')


def engine_paths(program_root: Path) -> tuple[Path, Path, Path]:
    root = Path(program_root) / 's2_cpp_engine'
    executable = Path((root / 's2-executable.txt').read_text(encoding='utf-8-sig').strip())
    if not executable.is_absolute():
        executable = root / executable
    executable = executable.resolve()
    model_name = (root / 'selected-model.txt').read_text(encoding='utf-8-sig').strip()
    if not model_name or Path(model_name).name != model_name:
        raise ValueError('Niepoprawna nazwa modelu Fish')
    from capri_paths import local_root
    user_models = local_root() / 'fish_models'
    models = user_models if (user_models / model_name).is_file() else root / 'models'
    model = models / model_name
    tokenizer = models / 'tokenizer.json'
    for name, path in [('s2.exe', executable), ('GGUF', model), ('tokenizer', tokenizer)]:
        if not path.is_file():
            raise FileNotFoundError(f'Brakuje pliku {name}: {path}')
    return executable, model, tokenizer


def _fingerprint(reference: Path, transcript: str, model: Path, tokenizer: Path,
                 executable: Path) -> str:
    """A cheap identity check without re-reading multi-MB WAV on each utterance."""
    def stamp(path: Path) -> dict:
        stat = path.stat()
        return {'path': str(path.resolve()), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
    record = {'reference': stamp(reference), 'transcript': transcript.strip(),
              'model': stamp(model), 'tokenizer': stamp(tokenizer), 'exe': stamp(executable),
              'format': 'capri-s2-profile-v1'}
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _child_path(executable: Path) -> str:
    """Add only child process DLL paths; don't change the global Windows PATH."""
    extra = [str(executable.parent)]
    build_root = executable.parent.parent
    if executable.parent.name.lower() == 'release':
        extra += [str(build_root / 'bin' / 'Release'), str(build_root / 'ggml' / 'src' / 'Release')]
    return os.pathsep.join(extra + [os.environ.get('PATH', '')])


def profile_for(reference: Path, transcript: str, *, program_root: Path,
                profile_root: Path | None = None) -> tuple[VoiceProfile, tuple[Path, Path, Path]]:
    executable, model, tokenizer = engine_paths(program_root)
    reference = Path(reference).resolve()
    if not reference.is_file() or reference.stat().st_size > 25 * 1024 * 1024:
        raise ValueError('Brak próbki lub próbka przekracza 25 MB')
    if not transcript.strip():
        raise ValueError('Brak transkrypcji próbki')
    folder = (Path(profile_root) if profile_root is not None else local_root() / 'fish_voice_profiles').resolve()
    name = 'capri_' + _fingerprint(reference, transcript, model, tokenizer, executable)[:28]
    return VoiceProfile(name, folder), (executable, model, tokenizer)


def _valid(profile: VoiceProfile) -> bool:
    return profile.file.is_file() and profile.file.stat().st_size > 64


def _append_log(profile: VoiceProfile, message: str) -> None:
    # Avoid writing the transcript or private WAV path into diagnostics.
    try:
        profile.folder.mkdir(parents=True, exist_ok=True)
        with (profile.folder / 'preparation.log').open('a', encoding='utf-8') as handle:
            handle.write(time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + message[:400] + '\n')
    except OSError:
        pass


def prepare_profile(reference: Path, transcript: str, *, program_root: Path,
                    profile_root: Path | None = None, progress=None,
                    timeout: int = 360, runner=None, force: bool = False) -> VoiceProfile | None:
    """Return reusable voice or None. Failed preparation never blocks speech.

    Loading a second full GGUF while the HTTP server is running can exhaust
    GPU memory, so offline profile encoding defaults to CPU mode. A separate
    one-time preparer can be run before starting the main application.
    """
    try:
        profile, (exe, model, tokenizer) = profile_for(reference, transcript,
                                                         program_root=program_root,
                                                         profile_root=profile_root)
    except (OSError, ValueError) as exc:
        return None
    with _lock:
        if _valid(profile):
            return profile
        if profile.name in _failed and not force:
            return None
        if progress:
            progress('s2_profile_create')
        profile.folder.mkdir(parents=True, exist_ok=True)
        # Save only the encoded prompt. The generated test WAV is discarded.
        fd, temp_name = tempfile.mkstemp(prefix='capri_profile_test_', suffix='.wav')
        os.close(fd)
        cmd = [str(exe), '--model', str(model), '--tokenizer', str(tokenizer),
               '--prompt-audio', str(Path(reference).resolve()),
               '--prompt-text', transcript.strip(),
               '--voice', profile.name, '--voice-dir', str(profile.folder),
               '--save-voice', '--text', 'Dzień dobry.',
               '--output', temp_name, '--vulkan', '-1', '--max-tokens', '48']
        env = dict(os.environ)
        env['PATH'] = _child_path(exe)
        try:
            call = runner or subprocess.run
            done = call(cmd, cwd=str(program_root), env=env, capture_output=True,
                        timeout=timeout, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if done.returncode != 0 or not _valid(profile):
                _failed.add(profile.name)
                # Never reuse an incomplete profile.
                try:
                    profile.file.unlink(missing_ok=True)
                except OSError:
                    pass
                _append_log(profile, f'Przygotowanie profilu nieudane: returncode={done.returncode}. Tryb WAV nadal dostepny.')
                return None
            _append_log(profile, f'Profil zapisany: {profile.name}.')
            if progress:
                progress('s2_profile_ready')
            return profile
        except (OSError, subprocess.TimeoutExpired) as exc:
            _failed.add(profile.name)
            try:
                profile.file.unlink(missing_ok=True)
            except OSError:
                pass
            _append_log(profile, f'Przygotowanie profilu przerwane: {type(exc).__name__}. Tryb WAV nadal dostepny.')
            return None
        finally:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass


def cached_profile(reference: Path, transcript: str, *, program_root: Path,
                   profile_root: Path | None = None) -> VoiceProfile | None:
    """Reuse an existing voice profile without CPU GGUF initialization.

    Normal GPU speech should never prepare a second model on the CPU just to
    create a .s2voice file. If no cached profile exists, the HTTP server gets
    the original WAV and transcription and performs the work on its selected
    backend. Explicit offline preparation remains available through the CLI.
    """
    try:
        profile, _ = profile_for(reference, transcript,
                                 program_root=program_root,
                                 profile_root=profile_root)
        return profile if usable_profile(profile) else None
    except (OSError, ValueError):
        return None


def note_profile_server_failure(profile: VoiceProfile, status: int) -> None:
    """Keep profile on disk for later engines; prevent repeat attempts this run."""
    with _lock:
        _failed.add(profile.name)
    _append_log(profile, f'HTTP {status} nie przyjal profilu; uzyto referencji WAV.')


def usable_profile(profile: VoiceProfile | None) -> bool:
    return profile is not None and _valid(profile) and profile.name not in _failed
