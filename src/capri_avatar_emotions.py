"""Configurable emotional avatars, including live folders inside the Capri program.

Emotion folders are user-owned. Upgrades must never overwrite their media.
Legacy AppData mappings are still loaded for backward compatibility.
"""
from __future__ import annotations

import json
import random
import re
import shutil
import time
import uuid
from pathlib import Path

EMOTIONS = (
    "neutral", "happy", "playful", "caring", "serious", "annoyed", "furious", "surprised", "sleepy",
    "flirty", "bashful", "smug", "curious", "skeptical", "sad", "worried", "relieved", "excited",
)
ACTIVITIES = ("idle", "thinking", "speaking", "reaction")
SUPPORTED = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".mp4", ".webm", ".mov"})
DEFAULT_TRANSITIONS = {"emotion": 350, "variant": 500, "reaction": 180, "return": 850}


def smoothstep(progress: float) -> float:
    """Clamped easing for crossfades: no abrupt velocity at either endpoint."""
    t = max(0.0, min(1.0, float(progress)))
    return t * t * (3.0 - 2.0 * t)


# A message must address Capri (or clearly continue a direct conversation)
# before praise/flirt turns into an in-character reaction. This is NOT a
# personality switch and never forces a prepared line of dialogue.
_DIRECT = re.compile(r"\b(capri|ty|tobie|ciebie|cię|cie|twój|twoj|twoja|twoje|jesteś|jestes|you|your)\b", re.I)
_TECH = re.compile(r"\b(błąd|blad|napraw(?!d)|instalac|api|program|kod|python|windows|steam|plik|model|klucz|problem|bug|error|fix|update)\w*", re.I)
_META = re.compile(r"\b(co oznacza|przetłumacz|napisz|przykład|przyklad|cytat|co to jest|what does|translate|example|definition)\b", re.I)
_COMPLIMENT = re.compile(
    r"\b((?:jesteś|jestes) (?:naprawdę )?(super|świetna|swietna|niesamowita|mądra|madra|genialna|urocza|cudowna|ładna|ladna|piękna|piekna|śliczna|sliczna)|"
    r"(?:ładna|ladna|piękna|piekna|śliczna|sliczna) jesteś|"
    r"świetnie sobie radzisz|swietnie sobie radzisz|podziwiam cię|podziwiam cie|"
    r"masz świetny głos|masz swietny glos|ładnie wyglądasz|ladnie wygladasz|"
    r"you are (great|amazing|brilliant|pretty|beautiful|gorgeous)|"
    r"you look (great|pretty|beautiful|gorgeous)|you did great|i admire you)\b", re.I)


def is_direct_compliment(text: str) -> bool:
    """Avoid crediting quotes, technical feedback and praise for a third party."""
    lower = (text or '').casefold()
    return (bool(_DIRECT.search(lower)) and bool(_COMPLIMENT.search(lower))
            and not _META.search(lower) and not _TECH.search(lower))


def emotion_from_text(text: str, *, reply: bool = False) -> tuple[str, float]:
    """Conservative conversational cues, not random mood changes or a script.

    Affection is distinct from intrusive sexual pressure; abuse still takes
    priority. Emojis and generic compliments are not sufficient on their own.
    """
    message = (text or "").strip()
    if not message:
        return "neutral", 0.0
    if not reply:
        from capri_anger import detect_provocation, detect_annoyance
        if detect_provocation(message).triggered:
            return "furious", 1.0
        if detect_annoyance(message).triggered:
            return "annoyed", .94
    low = message.casefold()
    personal = bool(_DIRECT.search(low))
    meta = bool(_META.search(low))
    technical = bool(_TECH.search(low))
    # Don't become bashful about example sentences, log entries or code.
    if not reply and not meta and not technical:
        if personal and re.search(
            r"\b(pójdziemy na randkę|pojdziemy na randke|umówisz się ze mną|umowisz sie ze mna|"
            r"chcę cię pocałować|chce cie pocalowac|mogę cię pocałować|moge cie pocalowac|"
            r"flirtujmy|flirtuję z tobą|flirtuje z toba|zakochałem się w tobie|zakochalam sie w tobie|"
            r"date me|go on a date|flirting with you|can i kiss you)\b", low):
            return "flirty", .95
        if personal and re.search(
            r"\b((?:jesteś|jestes) (prześliczna|przesliczna|przepiękna|przepiekna|urocza|cudowna|śliczna|sliczna|ładna|ladna|piękna|piekna)|"
            r"(?:ładna|ladna|piękna|piekna|śliczna|sliczna) jesteś|"
            r"masz (piękny|piekny|śliczny|sliczny|uroczy) (uśmiech|usmiech|głos|glos)|"
            r"pięknie dziś wyglądasz|pieknie dzis wygladasz|ładnie wyglądasz|ladnie wygladasz|"
            r"you are (so )?(beautiful|gorgeous|adorable|pretty)|you look (gorgeous|beautiful|pretty))\b", low):
            return "bashful", .9
        if personal and re.search(r"\b(i tak nie dasz rady|nie założysz się|nie zalozysz sie|"
                                  r"założę się, że nie|zaloze sie, ze nie|bet you can't|prove me wrong)\b", low):
            return "smug", .85
        if re.search(r"\b(zgadnij co|mam dla ciebie niespodziankę|mam dla ciebie niespodzianke|"
                     r"wiesz co się stało|wiesz co sie stalo|guess what|i have a surprise)\b", low):
            return "curious", .82
        if personal and re.search(r"\b(jesteś pewna|jestes pewna|na pewno tak myślisz|"
                                  r"na pewno tak myslisz|are you sure|you really believe)\b", low):
            return "skeptical", .82
    if re.search(r"\b(uff|nareszcie się udało|nareszcie sie udalo|wreszcie działa|wreszcie dziala|"
                 r"co za ulga|thank goodness|what a relief|finally worked)\b", low):
        return "relieved", .88
    if re.search(r"\b(nie mogę się doczekać|nie moge sie doczekac|ale się jaram|ale sie jaram|"
                 r"już nie mogę się doczekać|can't wait|so excited)\b", low):
        return "excited", .9
    if re.search(r"\b(co za smutna historia|to przygnębiające|to przygnebiajace|"
                 r"bardzo smutna wiadomość|very sad news|what a tragedy)\b", low):
        return "sad", .83
    if re.search(r"\b(martwię się o|martwie sie o|boję się o|boje sie o|"
                 r"nie wiem czy wszystko będzie dobrze|worried about|i'm concerned for)\b", low):
        return "worried", .85
    if not reply and is_direct_compliment(message):
        # A single ordinary compliment is pleasant, not instant romantic RP.
        # MoodEngine escalates only after repeated direct praise.
        return 'happy', .82
    patterns = (
        ("caring", r"\b(przykro mi|trzymaj się|wspieram|jestem przy tobie|martwi mnie|sorry|i'm sorry)\b"),
        ("sleepy", r"\b(dobranoc|idę spać|good night|śpij dobrze|spokojnej nocy)\b"),
        ("surprised", r"\b(serio\?|naprawdę\?|no way|niemożliwe|cooo+|wow|o kurczę)\b"),
        ("playful", r"\b(xd+|haha+|hehe+|żart|żartuję|lol|śmieszn|zabaw|podroczy|droczysz|podgryzam)"),
        ("happy", r"\b(dzięki|dziękuję|super|świetnie|kocham|uwielbiam|cudownie|fantastycznie|awesome|love)\b"),
        ("caring", r"\b(pomocy|jest mi smutno|boję się|potrzebuję wsparcia|nie daję rady|help me)\b"),
        ("serious", r"\b(problem|błąd|awari|napraw(?!d)|nie działa|crash|error|piln|zepsu|diagnost|bug|kod|technicz)"),
    )
    for emotion, pat in patterns:
        if re.search(pat, low):
            return emotion, .81
    # Punctuation and uppercase alone are too ambiguous to change the avatar.
    return "neutral", 0.0


class MoodEngine:
    """Temporary reaction + slowly decaying baseline; no periodic random moods."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.emotion = "neutral"
        self.base_mood = "neutral"
        self._expiry = 0.0
        self._base_expiry = 0.0
        self._streak = 0
        self._quiet_turns = 0
        self._compliment_streak = 0
        self._last_compliment = 0.0

    def observe(self, text: str, *, reply: bool = False) -> str:
        now = self.clock()
        if reply:
            # A generated reply cannot abruptly change the emotion selected
            # by the user's actual conversational cue.
            return self.tick()
        value, confidence = emotion_from_text(text)
        if is_direct_compliment(text):
            self._compliment_streak = self._compliment_streak + 1 if now-self._last_compliment < 110 else 1
            self._last_compliment = now
            if self._compliment_streak >= 2 and self.emotion != 'flirty':
                value, confidence = 'bashful', .91
        elif value not in ('bashful', 'flirty'):
            self._compliment_streak = 0
        if value == "neutral" or confidence < .78:
            # A normal next turn immediately releases anger. Do not preserve
            # previous frustration for 26-80 seconds after a single insult.
            if self.emotion in ('annoyed', 'furious') or self.base_mood in ('annoyed', 'furious'):
                self.emotion = 'neutral'
                self.base_mood = 'neutral'
                self._expiry = now
                self._base_expiry = now
                self._streak = 0
                self._quiet_turns = 0
                return 'neutral'
            self._quiet_turns += 1
            if self._quiet_turns >= 2 and self.emotion not in ('annoyed', 'furious'):
                self.emotion = 'neutral'
                self.base_mood = 'neutral'
                self._expiry = now
                self._base_expiry = now
            return self.tick()
        self._quiet_turns = 0
        if self._expiry > now and self.emotion == 'flirty' and value == 'bashful':
            # Consecutive compliments sustain the playful scene rather than
            # switching the avatar on every sentence.
            self._expiry = now + 30
            return self.emotion
        if self._expiry > now and self.emotion not in ("neutral", value):
            # Strong context changes win (boundaries, safety, distress), but
            # small banter signals never cause rapid emotional ping-pong.
            urgent = value in ("furious", "annoyed", "caring", "worried", "sad", "serious")
            # A direct warm compliment should be able to de-escalate a lingering
            # irritated mood from the previous turn instead of freezing Capri in anger.
            positive_reset = self.emotion in ('annoyed', 'furious') and value in ('happy', 'bashful', 'flirty', 'playful')
            if not urgent and confidence < .9 and not positive_reset:
                return self.emotion
        self._streak = self._streak + 1 if value == self.emotion else 1
        self.emotion = value
        if value in ('annoyed', 'furious'):
            self.base_mood = 'neutral'
            self._base_expiry = now
        self._expiry = now + (32 if value in ("flirty", "bashful", "caring", "sad") else 26)
        # A second, consistent cue earns a longer-lived baseline. A one-off
        # flirt should not dominate the next unrelated five conversations.
        if value not in ('annoyed', 'furious') and (self._streak >= 2 or value in ("playful", "caring", "sleepy")):
            self.base_mood = value
            self._base_expiry = now + (80 if self._streak >= 2 else 160)
        return self.emotion

    def tick(self) -> str:
        now = self.clock()
        if now >= self._base_expiry:
            self.base_mood = "neutral"
            self._streak = 0
        if now >= self._expiry:
            self.emotion = self.base_mood
        return self.emotion


class AvatarLibrary:
    """User-editable mapping: emotion -> activity -> weighted media paths."""
    def __init__(self, base_dir: str | Path, rng=None, *, program_root: str | Path | None = None):
        self.root = Path(base_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.media_root = self.root / "avatar_media"
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / "avatar_emotions.json"
        # Program folder: assets/emocje/happy/zdjecie.gif, etc. Files placed
        # directly inside an emotion folder are valid for ALL activities.
        # Optional subfolders split idle/thinking/speaking/reaction content.
        self.program_root = Path(program_root).expanduser().resolve() if program_root else None
        self.emotions_root = self.program_root / "assets" / "emocje" if self.program_root else None
        if self.emotions_root:
            for emotion in EMOTIONS:
                try:
                    (self.emotions_root / emotion).mkdir(parents=True, exist_ok=True)
                    for activity in ACTIVITIES:
                        (self.emotions_root / emotion / activity).mkdir(exist_ok=True)
                except OSError:
                    # Read-only installations can still display bundled assets.
                    pass
        self.rng = rng or random.Random()
        self.config = self._read()
        self.previous: dict[tuple[str, str], str] = {}

    def _read(self) -> dict:
        config = {"transition_ms": dict(DEFAULT_TRANSITIONS), "emotions": {}}
        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                source = raw.get("emotions", {})
                if isinstance(source, dict):
                    for emotion in EMOTIONS:
                        slots = source.get(emotion, {})
                        if not isinstance(slots, dict):
                            continue
                        config["emotions"][emotion] = {}
                        for activity in ACTIVITIES:
                            entries = slots.get(activity, [])
                            if isinstance(entries, list):
                                config["emotions"][emotion][activity] = [entry for entry in entries if self._valid_entry(entry)]
                values = raw.get("transition_ms", {})
                if isinstance(values, dict):
                    for key in DEFAULT_TRANSITIONS:
                        try:
                            config["transition_ms"][key] = max(80, min(2000, int(values.get(key, DEFAULT_TRANSITIONS[key]))))
                        except (ValueError, TypeError):
                            pass
        except (OSError, ValueError):
            pass
        return config

    @staticmethod
    def _valid_entry(entry) -> bool:
        return (isinstance(entry, dict) and isinstance(entry.get("file"), str)
                and Path(entry["file"]).suffix.lower() in SUPPORTED
                and isinstance(entry.get("weight", 1), (float, int))
                and 0 < float(entry.get("weight", 1)) <= 100)

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.config_path)

    def folder_for(self, emotion: str, activity: str | None = None) -> Path | None:
        if self.emotions_root is None or emotion not in EMOTIONS:
            return None
        if activity is not None and activity not in ACTIVITIES:
            return None
        return self.emotions_root / emotion / activity if activity else self.emotions_root / emotion

    def _folder_entries(self, emotion: str, activity: str) -> list[dict]:
        """Enumerate on every access, so ordinary filenames need no registration."""
        if not self.emotions_root:
            return []
        items: list[dict] = []
        for folder in (self.folder_for(emotion), self.folder_for(emotion, activity)):
            if folder is None or not folder.is_dir():
                continue
            try:
                files = sorted(folder.iterdir(), key=lambda path: path.name.casefold())
            except OSError:
                continue
            for path in files:
                if path.is_file() and path.suffix.casefold() in SUPPORTED and self.resolve(str(path)):
                    items.append({"file": str(path), "label": path.name, "weight": 1, "folder_file": True})
        return items

    def add(self, emotion: str, activity: str, source: str | Path, weight: int = 3) -> str:
        if emotion not in EMOTIONS or activity not in ACTIVITIES:
            raise ValueError("Nieznany stan emocji lub aktywności")
        original = Path(source).expanduser()
        if original.suffix.lower() not in SUPPORTED or not original.is_file():
            raise ValueError("Nieobsługiwany albo brakujący plik avatara")
        if original.stat().st_size > 250 * 1024 * 1024:
            raise ValueError("Plik jest większy niż 250 MB")
        destination_folder = self.folder_for(emotion, activity) or self.media_root
        destination_folder.mkdir(parents=True, exist_ok=True)
        destination = destination_folder / original.name
        if original.resolve() != destination.resolve():
            index = 2
            while destination.exists():
                destination = destination_folder / f"{original.stem}_{index}{original.suffix}"
                index += 1
            shutil.copy2(original, destination)
        item_path = ("@program/" + destination.relative_to(self.program_root).as_posix()
                     if self.program_root else str(destination.relative_to(self.root)))
        entries = self.config.setdefault("emotions", {}).setdefault(emotion, {}).setdefault(activity, [])
        if not any(self.resolve(e['file']) == destination.resolve() for e in entries):
            entries.append({"file": item_path, "label": destination.name, "weight": max(1, min(100, int(weight)))})
        self.save()
        return str(destination)

    def list_entries(self, emotion: str, activity: str) -> list[dict]:
        if emotion not in EMOTIONS or activity not in ACTIVITIES:
            return []
        saved = list(self.config.get("emotions", {}).get(emotion, {}).get(activity, []))
        existing = {str(path) for item in saved if (path := self.resolve(item["file"])) is not None}
        for entry in self._folder_entries(emotion, activity):
            if str(self.resolve(entry["file"])) not in existing:
                saved.append(entry)
        return saved

    def resolve(self, name: str) -> Path | None:
        """Only managed files inside root; reject config-path traversal."""
        if not isinstance(name, str):
            return None
        if name.startswith("@program/"):
            if self.program_root is None:
                return None
            candidate = (self.program_root / name[len("@program/"):]).resolve()
        else:
            candidate = (self.root / name).resolve()
        allowed = candidate.is_relative_to(self.media_root)
        if self.emotions_root is not None:
            allowed = allowed or candidate.is_relative_to(self.emotions_root)
        if not allowed or candidate.suffix.lower() not in SUPPORTED:
            return None
        return candidate if candidate.is_file() else None

    def set_weight(self, emotion: str, activity: str, index: int, value: int) -> None:
        entries = self.list_entries(emotion, activity)
        if not 0 <= index < len(entries):
            return
        selected = entries[index]
        if selected.get("folder_file"):
            # Explicit override for a file discovered directly from the folder.
            file_id = "@program/" + Path(selected["file"]).relative_to(self.program_root).as_posix() if self.program_root else selected["file"]
            self.config.setdefault("emotions", {}).setdefault(emotion, {}).setdefault(activity, []).append(
                {"file": file_id, "label": selected["label"], "weight": int(value)})
        else:
            selected["weight"] = int(value)
        self.save()

    def remove(self, emotion: str, activity: str, index: int) -> None:
        entries = self.list_entries(emotion, activity)
        if not 0 <= index < len(entries):
            return
        item = entries[index]
        path = item.get("file", "")
        configured = self.config.setdefault("emotions", {}).setdefault(emotion, {}).setdefault(activity, [])
        if not item.get("folder_file") and item in configured:
            configured.remove(item)
        # Program media are user files. An editor remove action deletes the
        # selected file; manual deletion from Explorer is also supported.
        managed = self.resolve(path)
        referenced = any(
            self.resolve(other.get("file", "")) == managed
            for group in self.config.get("emotions", {}).values()
            for values in group.values()
            for other in values
        )
        if managed and not referenced:
            managed.unlink(missing_ok=True)
        self.save()

    def choose(self, emotion: str, activity: str, *, fresh: bool = False) -> str | None:
        """Fallback: same emotion idle -> neutral activity -> neutral idle.

        If nothing exists, the caller displays the original avatar.
        """
        if emotion not in EMOTIONS:
            emotion = "neutral"
        if activity not in ACTIVITIES:
            activity = "idle"
        fallback = (("annoyed", activity), ("annoyed", "idle")) if emotion == "furious" else ()
        for e, a in ((emotion, activity), (emotion, "idle"), *fallback, ("neutral", activity), ("neutral", "idle")):
            usable = [(str(p), float(item.get("weight", 1)))
                      for item in self.list_entries(e, a)
                      if (p := self.resolve(item["file"])) is not None]
            if not usable:
                continue
            key = (e, a)
            last = self.previous.get(key)
            if fresh and len(usable) > 1:
                choices = [(path, weight) for path, weight in usable if path != last]
                if choices:
                    usable = choices
            options, weights = zip(*usable)
            selected = self.rng.choices(options, weights=weights, k=1)[0]
            self.previous[key] = selected
            return selected
        return None
