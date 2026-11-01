"""Robust Ollama NDJSON stream reader; doesn't display or speak thinking tokens."""
from __future__ import annotations

import json
from urllib import request as urlrequest


def generate(request_data: dict, *, endpoint='http://127.0.0.1:11434/api/chat',
             progress=None, timeout=240, open_url=None):
    """Return (content, diagnostics) from streamed Ollama response.

    The caller handles empty responses and retry. Progress reports only the
    approximate number of generated characters, never raw private thinking.
    """
    body = dict(request_data, stream=True)
    req = urlrequest.Request(endpoint,
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    opener = open_url or urlrequest.urlopen
    pieces = []
    total_chars = 0
    last_progress_step = 0
    saw_thinking = False
    last = {}
    with opener(req, timeout=timeout) as resp:
        for raw in resp:
            if not raw.strip():
                continue
            try:
                part = json.loads(raw.decode('utf-8'))
            except (UnicodeError, ValueError) as exc:
                raise RuntimeError('Nieprawidłowa odpowiedź strumieniowa Ollamy') from exc
            if part.get('error'):
                raise RuntimeError('Ollama: ' + str(part['error'])[:300])
            msg = part.get('message') or {}
            if msg.get('thinking') or part.get('thinking'):
                saw_thinking = True
            token = msg.get('content')
            if isinstance(token, str) and token:
                pieces.append(token)
                total_chars += len(token)
                step = total_chars // 60
                if progress and step > last_progress_step:
                    progress('model_stream:' + str(total_chars))
                last_progress_step = step
            # Deliberately ignore message.thinking, never send it to TTS or UI.
            if part.get('done'):
                last = part
                break
    return ''.join(pieces), {
        'done_reason':last.get('done_reason', 'no_done_event'),
        'eval_count':last.get('eval_count'),
        'had_thinking':saw_thinking,  # tokens discarded, only a boolean returned
    }
