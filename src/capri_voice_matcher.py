"""Independent local Ollama selector for user-approved voice rules.

No GUI imports and no PC-agent assumptions: a rule can intercept ANY question,
including a request to open a game. Return only an entry already in the library.
"""
from __future__ import annotations

import json
import re
from urllib import request as urlrequest

from capri_voice_library import list_entries, entry_audio, normalized_question

OLLAMA_CHAT_URL = 'http://127.0.0.1:11434/api/chat'
MAX_CANDIDATES = 24
MIN_CONFIDENCE = 70


# A quick reply is allowed only for an explicitly configured, low-stakes
# short turn. It must never replace factual reasoning, an agent request or
# character reactions. Manual rules outside this path remain in Voice Studio.
_DYNAMIC_QUESTION = re.compile(
    r'\b(?:ile|kiedy|gdzie|dlaczego|czemu|jaki|jaka|jakie|jak|który|ktora|'
    r'która|who|what|why|where|when|how|weather|pogoda|godzina|data|'
    r'kurs|cena|dzisiaj|jutro|obecnie|aktualnie)\b', re.I)


def is_quick_voice_turn(message: str) -> bool:
    q = normalized_question(message)
    if not q or len(q) > 100 or len(q.split()) > 13:
        return False
    if _DYNAMIC_QUESTION.search(q) or 'http' in q or '/' in q:
        return False
    try:
        from capri_agent import parse_direct_launch_request, looks_like_computer_request
        from capri_anger import detect_provocation, deserves_live_interpretation
        # Even short, seemingly matching user-approved takes must not take
        # precedence over interpreting a personal advance addressed to Capri.
        # This is only a routing hint; it never assumes sexual intent.
        if deserves_live_interpretation(message):
            return False
        if parse_direct_launch_request(message) or looks_like_computer_request(message):
            return False
        if detect_provocation(message).triggered:
            return False
    except ImportError:
        return False
    return True


def is_quick_voice_answer(answer: str) -> bool:
    """Avoid replacing a thoughtful answer with a long canned monologue."""
    q = normalized_question(answer)
    return bool(q and len(q) <= 140 and len(q.split()) <= 22)

def voice_candidates(question: str, language: str) -> list[dict]:
    """List valid enabled rules. Intents without example questions also count."""
    if language not in ('pl', 'en') or not normalized_question(question):
        return []
    question_words = set(normalized_question(question).split())
    scored = []
    try:
        entries = list_entries()
    except (OSError, ValueError, TypeError):
        return []
    for idx, entry in enumerate(entries):
        if entry.get('enabled', True) is not True or entry.get('language') != language:
            continue
        triggers = [t for t in (entry.get('triggers') or [])
                    if isinstance(t, str) and normalized_question(t)]
        intent = str(entry.get('intent', '') or '').strip()
        if not triggers and not intent:
            continue
        path = entry_audio(entry)
        answer = str(entry.get('text', '') or '').strip()
        if not path or not answer:
            continue
        rules = triggers + ([intent] if intent else [])
        overlap = max((len(question_words.intersection(normalized_question(rule).split()))
                       for rule in rules), default=0)
        scored.append((overlap, -idx, dict(id=entry['id'], text=answer,
                                          path=path, triggers=triggers,
                                          intent=intent)))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[-1] for row in scored[:MAX_CANDIDATES]]


def _parse_selection(reply: str, candidates: list[dict]) -> dict | None:
    """Only accept an exact known ID and a high-confidence declaration."""
    if not isinstance(reply, str):
        return None
    match = re.search(r'\{.*?\}', reply, re.S)
    if not match:
        return None
    try:
        result = json.loads(match.group(0))
        match_id = str(result.get('id', 'NONE'))
        confidence = int(result.get('confidence', 0))
    except (ValueError, TypeError, AttributeError):
        return None
    if confidence < MIN_CONFIDENCE or match_id == 'NONE':
        return None
    for item in candidates:
        if item['id'] == match_id:
            return {key: item[key] for key in ('id', 'path', 'text')} | {
                'mode': 'semantic', 'confidence': confidence}
    return None


def semantic_voice_rule_match(question: str, language: str, model: str,
                              progress=None) -> dict | None:
    """Ask the current local conversation model whether the user's rule applies.

    A model/network failure is not a positive match. No new responses are
    generated, and speech comes exclusively from the saved audio file.
    """
    candidates = voice_candidates(question, language)
    if not candidates or not is_quick_voice_turn(question):
        return None
    if progress is not None:
        progress('model')
    rules = [{'id': row['id'], 'example_questions': row['triggers'],
              'when_to_play_instruction': row['intent']} for row in candidates]
    if language == 'pl':
        system = (
            'Jesteś tylko selektorem GOTOWYCH nagrań Capri, a nie chatbotem ani agentem PC. '
            'Użytkownik ustawił reguły i instrukcje, przy jakich pytaniach odtwarzać konkretne audio. '
            'Wybierz ID nagrania, którego instrukcja / sens przykładów pasuje do aktualnej wypowiedzi użytkownika. '
            'Nie ma znaczenia, czy użytkownik postawił przecinki, kropki, znaki zapytania ani czy gra jest już uruchomiona. '
            'Nie wykonuj polecenia i nie oceniaj stanu komputera. '
            'Nie wybieraj reguły, gdy pytanie tylko luźno wiąże się z tematem. '
            'Jeśli znaczenie pasuje, zwróć JSON {"id":"DOKLADNE_ID_Z_LISTY","confidence":90}. '
            'W innym przypadku zwróć {"id":"NONE","confidence":0}. '
            'Zwracaj TYLKO JSON. Nigdy nie twórz własnej odpowiedzi.')
    else:
        system = (
            'You only select prerecorded user-approved voice lines, not generate answers or run PC actions. '
            'Select an existing recording when the user message matches the intended meaning of its examples or instruction. '
            'Ignore punctuation and whether an app is already running. Avoid broad topical matches. '
            'Return only JSON {"id":"EXACT_ID_FROM_LIST","confidence":90}, '
            'or {"id":"NONE","confidence":0}.')
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps({'user_message': question, 'rules': rules}, ensure_ascii=False)},
        ],
        'stream': False,
        'keep_alive': '15m',
        'format': 'json',
        'options': {'temperature': 0, 'num_predict': 96},
    }
    if model.startswith(('qwen3:', 'qwen3.5:')):
        payload['think'] = False
    req = urlrequest.Request(OLLAMA_CHAT_URL,
                             data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                             headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlrequest.urlopen(req, timeout=90) as resp:
            reply = json.loads(resp.read().decode('utf-8'))
        selected = _parse_selection(str(reply.get('message', {}).get('content', '')), candidates)
        return selected if selected and is_quick_voice_answer(selected['text']) else None
    except (OSError, ValueError, TypeError, KeyError):
        # Never choose randomly if Ollama is missing or returned nonsense.
        return None
