"""Reversible, deliberately opt-in runtime optimizations."""
from __future__ import annotations

OPT_KEYS = frozenset(('opt_adaptive_llm',
                      'opt_short_keepalive', 'opt_idle_ui'))


def llm_options(options: dict, kind: str, enabled: bool) -> dict:
    """Keep long-form RP and factual queries at the original context size."""
    result = dict(options)
    if enabled:
        result['num_ctx'] = 4096 if kind in ('greeting', 'chat') else 8192
    return result


def ollama_keep_alive(short_mode: bool) -> str:
    """Ollama itself manages model residency; don't forcibly unload in-flight work."""
    return '3m' if short_mode else '15m'
