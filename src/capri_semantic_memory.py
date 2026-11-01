"""Opt-in local semantic retrieval for Capri's existing conversation memory.

Uses Ollama /api/embed on LOOPBACK only. Never downloads models, never sends
memory to a remote URL and never changes a stored user's original message.
Indexing is scheduled off the Qt thread. Retrieval safely falls back to the
existing token search if the embedding model is unavailable.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import json
import math
from pathlib import Path
import sqlite3
import threading
import time
from urllib import request as urlrequest

from capri_memory import ConversationMemory, safe_to_store

EMBED_MODEL = 'embeddinggemma:300m'
_API = 'http://127.0.0.1:11434/api/embed'


def embedding(text: str, *, model=EMBED_MODEL, timeout=5, open_url=None) -> list[float]:
    payload = json.dumps({'model':model, 'input': text[:1400], 'truncate': True}).encode('utf-8')
    req = urlrequest.Request(_API, data=payload, method='POST',
                             headers={'Content-Type':'application/json'})
    with (open_url or urlrequest.urlopen)(req, timeout=timeout) as resp:
        doc = json.load(resp)
    values = (doc.get('embeddings') or [None])[0]
    if not isinstance(values, list) or not 32 <= len(values) <= 8192:
        raise ValueError('Niepoprawne embeddingi Ollama')
    vec = [float(x) for x in values]
    if not all(math.isfinite(x) for x in vec):
        raise ValueError('Embedding zawiera NaN/Inf')
    magnitude = math.sqrt(sum(x*x for x in vec))
    if magnitude <= 0:
        raise ValueError('Pusty embedding')
    return [x/magnitude for x in vec]


class SemanticConversationMemory:
    def __init__(self, memory: ConversationMemory, *, embed_fn=None):
        self.memory = memory
        self.embed_fn = embed_fn or embedding
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='capri-memory')
        self._state_lock = threading.RLock()
        self._index_future = None
        self._offline_until = 0.0
        with sqlite3.connect(memory.path, timeout=4) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS semantic_turns (
                turn_id INTEGER PRIMARY KEY,
                vector TEXT NOT NULL,
                FOREIGN KEY(turn_id) REFERENCES turns(id))''')

    def _embed(self, text: str) -> list[float]:
        # After an unavailable local embedding endpoint, don't stall every
        # conversational turn with another five-second network timeout.
        with self._state_lock:
            if time.monotonic() < self._offline_until:
                raise RuntimeError('Lokalne embeddingi tymczasowo niedostępne')
        try:
            result = self.embed_fn(text)
        except Exception:
            with self._state_lock:
                self._offline_until = time.monotonic() + 60.0
            raise
        with self._state_lock:
            self._offline_until = 0.0
        return result

    def index_recent(self, limit=6):
        """Keep at most one outstanding indexing task, never queue unbounded work."""
        with self._state_lock:
            if self._index_future is not None and not self._index_future.done():
                return self._index_future
            if time.monotonic() < self._offline_until:
                skipped = Future()
                skipped.set_result(None)
                return skipped
            self._index_future = self.pool.submit(self._index_recent, limit)
            return self._index_future

    def _index_recent(self, limit):
        with sqlite3.connect(self.memory.path, timeout=4) as db:
            rows = db.execute('''SELECT id, user_text, assistant_text FROM turns
                WHERE id NOT IN (SELECT turn_id FROM semantic_turns)
                ORDER BY id DESC LIMIT ?''', (max(1, min(limit, 30)),)).fetchall()
        for turn_id, user, assistant in rows:
            if not safe_to_store(user, assistant):
                continue
            try:
                vector = self._embed(user[:900])
                with sqlite3.connect(self.memory.path, timeout=4) as db:
                    # Verify that the turn still exists (memory.clear() may run).
                    if db.execute('SELECT 1 FROM turns WHERE id=?',(turn_id,)).fetchone():
                        db.execute('INSERT OR IGNORE INTO semantic_turns(turn_id,vector) VALUES (?,?)',
                                   (turn_id, json.dumps(vector)))
            except Exception:
                # Missing embedding model: ordinary lexical recall still works.
                break

    def schedule_index(self):
        return self.index_recent(3)

    def recall(self, query: str, lang: str, *, recent_users=(), limit=3, max_chars=1350) -> str:
        lexical = self.memory.recall(query, lang, limit=limit, max_chars=max_chars,
                                     recent_users=recent_users)
        try:
            query_vector = self._embed(query[:900])
            with sqlite3.connect(self.memory.path, timeout=4) as db:
                rows = db.execute('''SELECT t.user_text, t.assistant_text, s.vector
                    FROM semantic_turns s JOIN turns t ON t.id=s.turn_id
                    WHERE t.lang=? ORDER BY t.id DESC LIMIT 1000''', (lang,)).fetchall()
            ranked = []
            excluded = {u.strip() for u in recent_users}
            for user, answer, vector in rows:
                if user.strip() in excluded or not safe_to_store(user, answer):
                    continue
                vec = json.loads(vector)
                if len(vec) != len(query_vector):
                    continue
                sim = sum(a*b for a,b in zip(query_vector,vec))
                if sim >= .54:
                    ranked.append((sim,user,answer))
            ranked.sort(key=lambda x: -x[0])
            if not ranked:
                return lexical
            selected=[]
            for score,user,answer in ranked[:limit]:
                selected.append('Wcześniejsza wypowiedź użytkownika: '+user[:400])
            semantic='\n\n'.join(selected)
            return semantic[:max_chars] if semantic else lexical
        except Exception:
            return lexical

    def clear_embeddings(self):
        with sqlite3.connect(self.memory.path, timeout=4) as db:
            db.execute('DELETE FROM semantic_turns')

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
