"""Voice game-title hints and conservative, catalog-backed STT corrections.

No invented Steam IDs; never rewrite a question into an action. All catalog
reads are local and run on the existing transcription worker thread.
"""
from __future__ import annotations

from functools import lru_cache
import re
import time
from capri_app_catalog import LocalCatalog, match_score
from capri_agent import parse_direct_launch_request

_CACHE = (0., ())


def installed_game_names(*, refresh=False, catalog=None) -> tuple[str, ...]:
    global _CACHE
    now = time.monotonic()
    if catalog is None and not refresh and now - _CACHE[0] < 120:
        return _CACHE[1]
    try:
        entries = (catalog or LocalCatalog())._collect('game')
        result = tuple(dict.fromkeys(e.name.strip() for e in entries
                                     if e.kind == 'game' and 3 <= len(e.name) <= 90))[:120]
    except (OSError, ValueError, RuntimeError):
        result = ()
    if catalog is None:
        _CACHE = (now, result)
    return result


def initial_prompt(lang: str, names: tuple[str, ...]) -> str:
    intro = ('Polska rozmowa z asystentką Capri. Nazwy gier, wymawiane także po polsku: '
             if lang == 'pl' else 'Conversation with Capri. Installed game names: ')
    # 380 chars max to avoid burying actual speech beneath a massive prompt.
    return (intro + ', '.join(names[:16]))[:380]


def resolved_launch_query(text: str, names: tuple[str, ...]) -> str | None:
    """Return exact installed title for a sufficiently confident voice command."""
    request = parse_direct_launch_request(text)
    if not request or request.get('kind') == 'folder':
        return None
    spoken = request.get('query', '').strip()
    if len(spoken) < 4:
        return None
    scored = sorted(((match_score(spoken, name), name) for name in names), reverse=True)
    if not scored or scored[0][0] < 85:
        return None
    if len(scored) > 1 and scored[1][0] >= scored[0][0] - 9:
        return None
    return scored[0][1]
