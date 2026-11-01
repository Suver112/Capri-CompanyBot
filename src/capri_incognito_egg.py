"""Local, ephemeral Easter egg after three successful private-window commands.

Only the in-memory timestamps of *successful* browser actions are counted.
No incognito activity history or image is uploaded to any online model or
saved to the user's long-term memory.
"""
from __future__ import annotations

from collections import deque
import time

WINDOW_SECONDS = 30 * 60
REQUIRED_OPENS = 3


def private_window_opened(agent_session) -> bool:
    """Read the last audited browser action, not an inferred LLM response."""
    if agent_session is None:
        return False
    observations = getattr(agent_session, 'observations', ()) or ()
    for item in reversed(observations):
        if not isinstance(item, dict) or item.get('tool') != 'browser_control':
            continue
        args = item.get('args') or {}
        result = item.get('result') or {}
        return (isinstance(args, dict) and isinstance(result, dict)
                and args.get('action') == 'private_window'
                and result.get('status') == 'launched'
                and result.get('action') == 'private_window'
                and 'error' not in result
                and not result.get('denied_by_user'))
    return False


class IncognitoEasterEgg:
    """Fire on the 3rd successful private window within a rolling 30 min.

    The counter resets after firing. Nothing is persisted across a restart.
    A completed agent session is counted at most once even if the UI receives
    duplicate completion notifications.
    """

    def __init__(self, window_seconds: float = WINDOW_SECONDS,
                 required_opens: int = REQUIRED_OPENS):
        if window_seconds <= 0 or required_opens < 1:
            raise ValueError('The window must be positive and threshold >= 1')
        self.window_seconds = window_seconds
        self.required_opens = required_opens
        self._recent_opens: deque[float] = deque()
        self._last_counted_session = None

    def should_show(self, session, now: float | None = None) -> bool:
        if not private_window_opened(session):
            return False
        # Avoid double-counting duplicate completion events for the same
        # AgentSession. Each independently requested open has a new session.
        if session is self._last_counted_session:
            return False
        self._last_counted_session = session
        if now is None:
            now = time.monotonic()
        # Rolling interval: open #1 may expire while opens #2 and #3 count.
        while self._recent_opens and (now - self._recent_opens[0] >= self.window_seconds
                                      or now < self._recent_opens[0]):
            self._recent_opens.popleft()
        self._recent_opens.append(now)
        if len(self._recent_opens) < self.required_opens:
            return False
        self._recent_opens.clear()
        return True
