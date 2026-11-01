"""Low-overhead, loss-aware LLM context packing for Capri.

Preserves the latest user request verbatim, keeps recent complete turns, and
never changes the core persona or retrieved long-term memories. No summary LLM.
"""
from __future__ import annotations


def compact_history(history: list[dict], kind: str = 'chat') -> list[dict]:
    """Keep coherent recent exchanges, not independent requests.

    Earlier complete user/assistant pairs are retained as far as the budget
    permits. Never clip the current user message or orphan a previous response.
    The local token context limit is still the final authority.
    """
    caps = {'greeting': (12, 5500), 'chat': (16, 6900),
            'factual': (16, 8500), 'play': (16, 7500)}
    max_messages, budget = caps.get(kind, caps['chat'])
    valid = [dict(m) for m in history if m.get('role') in ('user', 'assistant')
             and isinstance(m.get('content'), str) and m['content'].strip()]
    if not valid:
        return []
    # Group consecutive dialog messages into exchanges, retaining order.
    exchanges = []
    pending = []
    for m in valid[-max_messages:]:
        if m['role'] == 'user' and pending:
            exchanges.append(pending)
            pending = []
        pending.append(m)
    if pending:
        exchanges.append(pending)
    chosen = []
    used = 0
    for i, pair in enumerate(reversed(exchanges)):
        cost = sum(len(m['content']) for m in pair)
        # Always retain the two newest exchanges, even if unusually long.
        if i >= 2 and used + cost > budget:
            break
        chosen.append(pair)
        used += cost
    return [m for pair in reversed(chosen) for m in pair]


def output_budget(options: dict, question: str, kind: str) -> dict:
    """Honor explicit requests for long stories or detailed explanations.

    Routine chat stays concise, but user intent always overrides the default
    conversational token cap. Return a new dict, never mutate caller settings.
    """
    import re
    from unicodedata import normalize
    result = dict(options)
    if kind == 'greeting':
        return result
    s = ''.join(x for x in normalize('NFKD', str(question).casefold().replace('ł','l'))
                if not (0x300 <= ord(x) <= 0x36f))
    if re.search(r'\b(?:szczegolowo|dokladnie|obszernie|rozwin|rozpisz|dlug[aią]|'
                 r'krok po kroku|wiecej szczegolow|pelna historie|whole story|'
                 r'in detail|step by step|long answer|comprehensive)\b', s):
        result['num_predict'] = max(int(result.get('num_predict', 0)), 640)
    return result
