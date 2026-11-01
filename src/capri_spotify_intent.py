"""Explicit Spotify song intentions, including conversational lead-ins.

No LLM text counts as an executed playback action. This module only extracts
unambiguous *user* requests to play a named song; the agent remains responsible
for consent and actual Spotify API execution.
"""
from __future__ import annotations

import re
import unicodedata
from capri_media_control import parse_direct_spotify_track_request

# Avoid playing merely because someone mentions a track or asks about music.
_COMMAND = re.compile(
    r"(?<!\w)(?:puść|pusc|puścić|p[uó]j[sś][cć]|p[oó]j[sś][cć](?:ie)?|"
    r"odtwórz|odtworz|odtworzyć|odtworzyc|zagraj|włącz|wlacz|"
    r"włączyć|wlaczyc|zapuść|zapusc|play)\b",
    re.IGNORECASE,
)
_STOP = re.compile(r"\b(?:nie|nigdy|bez|zamiast)\s+(?:mi\s+)?(?:puść|pusc|puścić|odtwórz|odtworz|zagraj|włącz|wlacz)\b", re.I)
_MUSIC = re.compile(r"\b(?:spotify\w*|spotifaj\w*|spotifi\w*|spotyfi\w*|piosenk\w*|utw[oó]r\w*|kawa[łl]k\w*|muzyk\w*)\b", re.I)
_POLITE = re.compile(r"\b(?:możesz|mozesz|m[oó]g[łl]by[sś]|proszę|prosze|chc[eę]|chcia[łl]bym|chcialbym|weź|wez)\b", re.I)
_CONTEXT = re.compile(r"\b(?:spotify\w*|spotifaj\w*|spotifi\w*|spotyfi\w*)\b", re.I)
_SONG_PREFIX = re.compile(r"^(?:(?:mi|nam|proszę|prosze|teraz|nareszcie|piosenkę|piosenke|piosenk[ię]|utw[oó]r|utwor|kawa[łl]ek|kawa[łl]ka|numer|track)\s+){0,5}", re.I)
# This preference is resolved only for a direct playback request, not injected
# into unrelated roleplay prompts or treated as an objective chart ranking.
SAD_SONG_QUERY = 'I Really Want to Stay at Your House Rosa Walton'


def _fold_phonetic(text: str) -> str:
    """Normalize Polish STT drift only for a *positive explicit* playback request."""
    text = unicodedata.normalize('NFKD', text.casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return text.translate(str.maketrans({'ł':'l'}))

def _asked_for_cyberpunk_sad_song(text: str) -> bool:
    v = _fold_phonetic(text)
    # Avoid changing the meaning of a story about music or a negative request.
    if re.search(r'\b(?:nie|bez|zamiast)\s+(?:mi\s+)?(?:pusc|pust|wlacz|odtworz)\b', v):
        return False
    if re.search(r'\b(?:nie puszczaj|nie odtwarzaj|nie wlaczaj)\b', v):
        return False
    if re.match(r'^(?:co|jaka|jaki|dlaczego|jak|czy to|opowiedz|wytlumacz)\b', v):
        return False
    verb = re.search(r'\b(?:pusc|pust|pus|puscic|p[oou]jsc|pojscie|odtworz|zagraj|wlacz|lacz|zapusc|play)\b', v)
    if not verb:
        return False
    # 'biosenka' is a real observed Parakeet error for 'piosenka'.
    topic = re.search(r'\b(?:piosenk\w*|biosenk\w*|utwor\w*|kawalk\w*|muzyk\w*)\b', v)
    mood = re.search(r'\b(?:naj\s*smutniejsz\w*|smutniejsz\w*|najbardziej\s+smutn\w*)\b', v)
    soundtrack = re.search(r'\b(?:cyberpunk\w*|edgerunners\w*)\b', v)
    platform = re.search(r'\b(?:spotify\w*|spotifaj\w*|spotifi\w*|spotyfi\w*)\b', v)
    return bool(topic and mood and (platform or soundtrack))
_SAD_SONG = re.compile(r'\b(?:najsmutniejsz\w*|smutniejsz\w*|najbardziej\s+smutn\w*)\s+(?:piosenk\w*|utw[oó]r\w*|kawa[łl]k\w*|muzyk\w*)\b', re.I)
_GENERIC = re.compile(r"^(?:muzyk[aeęi]|piosenk[aeęi]?|utw[oó]r|odtwarzanie|co[sś]|cokolwiek|spotify|radio|playlist[aęy]?)$", re.I)


def parse_requested_spotify_track(text: str) -> dict | None:
    """Return a tool request only for a named song with positive action intent."""
    if not isinstance(text, str) or not (2 <= len(text.strip()) <= 2000):
        return None
    q = re.sub(r"\s+", " ", text.strip())
    # Resolve the personal preference before invoking the LLM planner. A vague
    # song category is otherwise an invitation to hallucinate a random title.
    # Require an affirmative playback verb and Spotify/music context. Quotes,
    # negations and factual questions must not start playback.
    if _asked_for_cyberpunk_sad_song(q):
        return {'tool': 'spotify_play_track', 'args': {'query': SAD_SONG_QUERY}}
    direct = parse_direct_spotify_track_request(text)
    if direct:
        title = str(direct.get('args', {}).get('query', '')).strip()
        # The legacy parser may treat an indefinite music category as a song.
        if re.match(r'^(?:jaka[sś]|jak[aą]ś|jakiego[sś]|jak[aą]kolwiek|dowoln[aą]|co[sś])\s+(?:smutn\w*\s+|weso[łl]\w*\s+)?(?:piosenk\w*|utw[oó]r\w*|kawa[łl]k\w*)\b', title, re.I):
            return None
        return direct
    q = re.sub(r"\s+", " ", text.strip())
    # Negated instructions or quotes are not an authorization to play anything.
    if _STOP.search(q) or re.search(r'\b(?:nie puszczaj|nie odtwarzaj|nie włączaj)\b', q, re.I):
        return None
    # Do not reinterpret a question *about* a song as a command.
    if re.match(r'^(?:co|jaka|jaki|dlaczego|jak|czy\s+to|opowiedz|wytłumacz)\b', q, re.I):
        return None
    m = _COMMAND.search(q)
    if not m:
        return None
    lead = q[:m.start()]
    # In conversational requests, require clear media context; a generic verb
    # after an unrelated sentence is not enough. 'pójść' is only a STT alias
    # if Spotify is explicitly named (not a general synonym for 'puść').
    raw_verb = m.group().lower()
    if re.match(r'p[oóu]j', raw_verb) and not _CONTEXT.search(q):
        return None
    if lead and not (_MUSIC.search(q) or _POLITE.search(q)):
        return None
    # A reported/quoted statement is not an instruction to the assistant.
    if re.search(r'(?:powiedzia[łl]|napisa[łl]|cytat|m[oó]wi[łl]).{0,30}$', lead, re.I):
        return None
    rest = _SONG_PREFIX.sub('', q[m.end():].strip(' ",.:;!?'))
    rest = re.sub(r'\s+(?:(?:na|w|przez)\s+)?(?:spotify\w*|spotifaj\w*|spotifi\w*|spotyfi\w*)\b.*$', '', rest, flags=re.I)
    rest = re.sub(r'\s*(?:\?|!|\.|,|;|:)\s*(?:bo|prosz[eę]|dzi[eę]ki|please|tak\s+na\s+dobry\s+pocz[aą]tek)\b.*$', '', rest, flags=re.I)
    rest = rest.strip(' ,.!?\"\'„”')
    # Ambiguous requests are left to the planner, never submitted as songs.
    if not 2 <= len(rest) <= 180 or _GENERIC.fullmatch(rest):
        return None
    if re.match(r'^(?:jaka[sś]|jak[aą]ś|jakiego[sś]|jak[aą]kolwiek|dowoln[aą]|co[sś])\s+(?:smutn\w*\s+|weso[łl]\w*\s+)?(?:piosenk\w*|utw[oó]r\w*|kawa[łl]k\w*)\b', rest, re.I):
        return None
    if re.search(r'\b(?:gr[eę]|game|program|aplikacj\w*|youtube|filmi?\w*|podcast\w*)\b', rest, re.I):
        return None
    # For misleading game requests like 'włącz Ligę', a Spotify platform is
    # required for playback, and launch-specific names remain in the game agent.
    if raw_verb in ('włącz','wlacz','włączyć','wlaczyc') and not (_CONTEXT.search(q) or re.search(r'\b(?:piosenk\w*|utw[oó]r\w*|kawa[łl]k\w*)\b', q, re.I)):
        return None
    return {'tool':'spotify_play_track', 'args':{'query':rest}}


def explicit_spotify_action(text: str) -> bool:
    """Whether explicit Spotify execution was requested (not merely discussed)."""
    if parse_requested_spotify_track(text) is not None:
        return True
    if _STOP.search(text or ''):
        return False
    return bool(_CONTEXT.search(text or '') and _COMMAND.search(text or ''))
