"""Turn lifecycle coordination, used by Capri's beta chat path.

A late response from an outdated worker must never overwrite a newer turn.
This is deliberately small, independent of PySide6 and the TTS engines.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
import time


@dataclass(frozen=True)
class TurnToken:
    sequence: int
    kind: str


class TurnCoordinator:
    def __init__(self):
        self.lock=RLock()
        self.sequence=0
        self.current=None
        self.started=0.
        self.stage='idle'

    def begin(self, kind='chat') -> TurnToken:
        with self.lock:
            self.sequence += 1
            self.current=TurnToken(self.sequence,kind)
            self.started=time.monotonic()
            self.stage='thinking'
            return self.current

    def is_current(self, token: TurnToken) -> bool:
        with self.lock:
            return self.current == token

    def mark(self, token: TurnToken, stage: str) -> bool:
        with self.lock:
            if self.current != token:
                return False
            self.stage=str(stage)[:32]
            return True

    def finish(self, token: TurnToken) -> float | None:
        with self.lock:
            if self.current != token:
                return None
            elapsed=time.monotonic()-self.started
            self.current=None
            self.stage='ready'
            return elapsed

    def cancel(self):
        with self.lock:
            self.current=None
            self.sequence += 1
            self.stage='cancelled'
