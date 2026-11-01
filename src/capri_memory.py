"""Private, local-only conversational memory for Capri.

Unlike fictional Project Capricorn lore, these are the user's real dialogue turns.
There is no network, background cloud sync, or automatic factual inference.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from functools import lru_cache
import sqlite3
import time
import unicodedata
import uuid
from pathlib import Path

# Do not retain obvious credentials. This is a safeguard, not a DLP guarantee.
_SENSITIVE = re.compile(
    r"(?i)(?:\b(?:password|haslo|hasło|api[_ -]?key|token|secret|klucz[_ -]?api)\b\s*[:=]\s*\S+|"
    r"\bsk-[A-Za-z0-9_-]{12,}\b|\bgh[pousr]_[A-Za-z0-9_]{12,}\b|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
_STOPWORDS = frozenset('''a aby ale albo bo by byl byla byly być co czy dla do gdy i ich jak jaka jakie
jest jestem jego jej juz już kiedy kto ktory która które lub mi mnie mój moja na nie o od
on ona oni po pod się sie ten ta tego to tu twoj twoja w we z za ze że the and for what when
why how where who you your this that is are was were with have from about them it problem pomoc pomoz pomóż sprawdz sprawdź capri kapri'''.split())


def safe_to_store(*texts: str) -> bool:
    return not any(_SENSITIVE.search(str(t)) for t in texts)


@lru_cache(maxsize=2048)
def _terms_cached(value: str) -> frozenset[str]:
    value = unicodedata.normalize('NFKD', value.casefold().replace('ł', 'l'))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return frozenset(word for word in re.findall(r'[a-z0-9]{3,}', value) if word not in _STOPWORDS)


def _terms(value: str) -> frozenset[str]:
    """Bounded in-process cache; no database migration or network."""
    return _terms_cached(value)


class ConversationMemory:
    """Creates its own short-lived SQLite connections; safe to call across threads."""

    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                lang TEXT NOT NULL,
                user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL
            )''')
            db.execute('CREATE INDEX IF NOT EXISTS turns_session ON turns(session_id)')

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=3)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def new_session(self) -> None:
        self.session_id = uuid.uuid4().hex

    def save_turn(self, user: str, assistant: str, lang: str) -> bool:
        user, assistant = user.strip(), assistant.strip()
        if not user or not assistant or not safe_to_store(user, assistant):
            return False
        with self._connect() as db:
            db.execute('INSERT INTO turns(created_at, session_id, lang, user_text, assistant_text) '
                       'VALUES (?,?,?,?,?)', (int(time.time()), self.session_id, lang, user[:3500], assistant[:5000]))
            # Bound disk use; prune oldest messages, but never cross into voice assets.
            db.execute('DELETE FROM turns WHERE id NOT IN (SELECT id FROM turns ORDER BY id DESC LIMIT 3000)')
        return True

    def recall(self, question: str, lang: str, limit: int = 3, max_chars: int = 1350,
               recent_users: tuple[str, ...] = ()) -> str:
        """Retrieve relevant completed past turns, not an invented personality summary.

        Retrieve earlier sessions and messages that have fallen out of the active
        short conversation context; avoid repeating recent in-context messages.
        """
        keywords = _terms(question)
        if not keywords:
            return ''
        with self._connect() as db:
            rows = db.execute('SELECT id, user_text, assistant_text FROM turns '
                              'WHERE lang = ? ORDER BY id DESC LIMIT 1500',
                              (lang,)).fetchall()
        recent = {text.strip() for text in recent_users}
        scored = []
        for row_id, user, answer in rows:
            if user.strip() in recent:
                continue
            terms = _terms(user)
            matches = terms.intersection(keywords)
            # Simple, conservative Polish inflection tolerance: Laguną/Lagunie,
            # hamulce/hamulców, without a heavyweight embedding model.
            approximate = {query for query in keywords if len(query) >= 6 and
                           any(len(word) >= 6 and word[:5] == query[:5] for word in terms)}
            matches |= approximate
            if not matches:
                continue
            # The user's wording carries the strongest signal; older items
            # are never given universal priority solely for being recent.
            score = sum(2.5 if len(token) >= 6 else 1.5 for token in matches)
            if len(matches) > 1:
                score += 1.8
            scored.append((score, row_id, user, answer))
        scored.sort(key=lambda item: (-item[0], -item[1]))
        chosen = []
        used = 0
        for score, _, user, answer in scored:
            if score < 1.5:
                continue
            # No system roles or raw control markup taken from remembered turns.
            line = f'Wcześniejsza wypowiedź użytkownika (niezależna od fikcyjnego lore): {user[:450]}'
            if len(line) + used > max_chars:
                continue
            chosen.append(line)
            used += len(line) + 2
            if len(chosen) >= limit:
                break
        return '\n\n'.join(chosen)

    def count(self) -> int:
        with self._connect() as db:
            return int(db.execute('SELECT COUNT(*) FROM turns').fetchone()[0])

    def clear(self) -> None:
        with self._connect() as db:
            db.execute('DELETE FROM turns')
            db.execute('DELETE FROM sqlite_sequence WHERE name = ?', ('turns',))
        # VACUUM cannot run inside a transaction.
        with self._connect() as db:
            db.execute('VACUUM')
        self.new_session()
