# -*- coding: utf-8 -*-
"""Capri media agent: explicit user commands via Windows system media sessions.

No Spotify login, token, third-party app code or screen scraping is required.
Operations are per-session (Spotify will never fall through to a random player).
This module is loaded lazily and does not affect Capri startup/model loading.
"""
from __future__ import annotations

import asyncio
import re
import sys

_ALLOWED = {'play', 'pause', 'toggle', 'next', 'previous', 'volume', 'volume_delta', 'seek', 'seek_delta'}


def _normalize_app(raw):
    name = str(raw or 'active').strip().casefold()
    if name in {'', 'current', 'aktualna', 'aktywny', 'active', 'media', 'muzyka'}:
        return 'active'
    if name == 'spotify':
        return name
    # Optional generic Windows media sessions, never arbitrary program execution.
    if not re.fullmatch(r'[a-z0-9][a-z0-9 ._\-]{1,50}', name):
        raise ValueError('Niepoprawna nazwa odtwarzacza.')
    return name


def _media_runtime():
    if sys.platform != 'win32':
        raise RuntimeError('Sterowanie aplikacjami multimedialnymi wymaga Windows 10/11.')
    try:
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    except (ImportError, OSError) as exc:
        raise RuntimeError('Brak Windows Media API. Uruchom Napraw Capri (menu Start).') from exc
    return GlobalSystemMediaTransportControlsSessionManager


async def _choose_session(app):
    manager_class = _media_runtime()
    manager = await manager_class.request_async()
    if app == 'active':
        session = manager.get_current_session()
    else:
        sessions = list(manager.get_sessions())
        # Do not let matching Spotify fall back to an unrelated media app.
        session = next((s for s in sessions if app in str(s.source_app_user_model_id).casefold()), None)
    if session is None:
        name = 'aktywny odtwarzacz' if app == 'active' else app
        raise RuntimeError('Nie znalazłem sesji multimedialnej: '+name+'. Uruchom odtwarzanie w aplikacji i spróbuj ponownie.')
    return session


def _source(session):
    return str(getattr(session, 'source_app_user_model_id', '') or '')[:150]


async def _details(session):
    result = {'app': _source(session)}
    try:
        media = await session.try_get_media_properties_async()
        result['title'] = str(media.title or '')[:250]
        result['artist'] = str(media.artist or '')[:180]
        result['album'] = str(media.album_title or '')[:180]
    except Exception:
        result['metadata_unavailable'] = True
    try:
        info = session.get_playback_info()
        status = str(info.playback_status).casefold()
        # Enum display can vary between PyWinRT builds; report raw status too.
        result['playback_status'] = status[:80]
    except Exception:
        pass
    return result


async def _async_status(app):
    session = await _choose_session(app)
    return await _details(session)


async def _async_control(app, action):
    session = await _choose_session(app)
    call = {
        'play': session.try_play_async,
        'pause': session.try_pause_async,
        'toggle': session.try_toggle_play_pause_async,
        'next': session.try_skip_next_async,
        'previous': session.try_skip_previous_async,
    }[action]
    supported = await call()
    if supported is False:
        raise RuntimeError('Odtwarzacz odrzucił polecenie „'+action+'”.')
    # Metadata may update later; do not claim that it already changed.
    return {'action': action, 'app': _source(session), 'accepted': True}


def media_status(app='active'):
    return asyncio.run(_async_status(_normalize_app(app)))


def media_control(action, app='active', value=None):
    action = str(action or '').strip().casefold()
    if action not in _ALLOWED:
        raise ValueError('Nieznana komenda odtwarzacza.')
    app = _normalize_app(app)
    if app == 'spotify':
        from capri_spotify_web import connected, spotify_playback_control
        if connected():
            if action == 'toggle':
                # A media-session toggle is intentionally left to WinRT.
                return asyncio.run(_async_control(app, action))
            return spotify_playback_control(action, value)
        if action in {'volume', 'volume_delta', 'seek', 'seek_delta'}:
            raise RuntimeError('Regulacja głośności/przewijanie Spotify wymagają połączenia Spotify API w ustawieniach.')
    if action not in {'play', 'pause', 'toggle', 'next', 'previous'}:
        raise RuntimeError('Ta operacja wymaga Spotify API.')
    return asyncio.run(_async_control(app, action))


# Deliberately narrow fast parser. Unknown/ambiguous requests go to the LLM agent.
# Never execute media controls in response to questions, negative commands or quotes.
def parse_direct_media_request(text):
    if not isinstance(text, str) or len(text) > 280:
        return None
    q = text.strip().lower()
    # Common Polish declensions and phonetic STT spellings of Spotify.
    # Normalize only standalone platform tokens, not arbitrary song titles.
    q = re.sub(r'\b(?:spotifya|spotifyu|spotifyem|spotifyie|spotifaj|spotifaja|spotifaju|spotifajem|spotifi|spotyfi)\b', 'spotify', q)
    q = re.sub(r'^(?:(?:hej|siema|ej|cześć|czesc|hello|hey)[,! ]+)?(?:capri|kapri)[,! ]*', '', q)
    q = re.sub(r'^(?:proszę|prosze|możesz|mozesz|weź|wez|teraz|szybko|mi|no to|czy możesz|czy mozesz)\s+', '', q)
    q = q.strip(' .!?')
    if re.search(r'\b(?:nie|nigdy|bez|zamiast|jak|dlaczego|czy potrafisz|czy umiesz)\b', q):
        return None
    if re.search(r'\b(?:powiedz|wytłumacz|wytlumacz|opisz)\b', q):
        return None
    # Only explicit player or media nouns; generic 'stop' should not trigger.
    context = bool(re.search(r'\b(?:spotify|muzyk\w*|piosenk\w*|utw[oó]r\w*|odtwarzan\w*|player|vlc|youtube|tidal|media)\b', q))
    if not context:
        return None
    app = 'spotify' if 'spotify' in q else ('vlc' if re.search(r'\bvlc\b', q) else 'active')
    # Status queries, which do not change playback.
    if re.search(r'(?:co|jaki|jaka|kt[oó]ry|kt[oó]ra|what|which)\b', q) and re.search(r'(?:gra|leci|s[łl]ucham|piosenk|utw[oó]r|odtwarzan|playing|track)', q):
        return {'tool':'media_status', 'args':{'app':app}}
    # Spotify-specific volume and position commands must be parsed BEFORE
    # generic pause/next commands; numeric values cannot be guessed by an LLM.
    if app == 'spotify':
        volume_context = bool(re.search(r'\b(?:g[łl]o[sś]no[sś][cć]\w*|g[łl]o[sś]niej|ciszej|[sś]cisz\w*|podg[łl]o[sś]\w*|volume)\b', q))
        number = re.search(r'(?<!\w)(\d{1,3})(?:\s*%|\b)', q)
        if volume_context and number:
            amount = int(number.group(1))
            if amount > 100:
                return None
            down = bool(re.search(r'[sś]cisz|ciszej|zmniejsz|obni[zż]', q))
            up = bool(re.search(r'podg[łl]o[sś]|g[łl]o[sś]niej|zwi[eę]ksz|podnie[sś]', q))
            delta = bool(re.search(r'\bo\s+\d', q))
            if delta and (down or up):
                return {'tool':'media_control','args':{'app':app,'action':'volume_delta',
                        'value': amount * (-1 if down else 1)}}
            if not delta:
                return {'tool':'media_control','args':{'app':app,'action':'volume','value':amount}}
        if volume_context and not number:
            down = bool(re.search(r'[sś]cisz|ciszej|zmniejsz|obni[zż]', q))
            up = bool(re.search(r'podg[łl]o[sś]|g[łl]o[sś]niej|zwi[eę]ksz|podnie[sś]', q))
            if down or up:
                return {'tool':'media_control','args':{'app':app,'action':'volume_delta',
                        'value': -10 if down else 10}}
        if re.search(r'\b(?:przewi[nń]\w*|cofnij\w*|przeskocz\w*|seek)\b', q):
            minutes_seconds = re.search(r'\b(\d{1,2}):(\d{2})\b', q)
            if minutes_seconds and int(minutes_seconds.group(2)) < 60:
                millis = (int(minutes_seconds.group(1))*60 + int(minutes_seconds.group(2))) * 1000
            else:
                seconds = re.search(r'\b(\d{1,3})\s*(?:sekund\w*|s\b)', q)
                minutes = re.search(r'\b(\d{1,2})\s*minut\w*', q)
                millis = (int(seconds.group(1))*1000 if seconds else
                          int(minutes.group(1))*60_000 if minutes else None)
            if millis is not None:
                backwards = bool(re.search(r'\b(?:cofnij|wstecz|do\s+ty[łl]u)\b',q))
                relative = bool(re.search(r'\bo\s+\d|\b(?:wstecz|do\s+przodu|do\s+ty[łl]u)\b',q))
                return {'tool':'media_control','args':{'app':app,
                    'action':'seek_delta' if relative else 'seek',
                    'value':(-millis if backwards else millis)}}
    patterns = [
        ('next', r'\b(?:nast[eę]pn\w*|kolejn\w*|pomi[nń]\w*|przeskocz\w*|skip|next)\b'),
        ('previous', r'\b(?:poprzedn\w*|cofnij\w*|previous|prev|back)\b'),
        ('pause', r'\b(?:pauza|wstrzymaj\w*|zatrzymaj\w*|stopuj\w*|spauzuj\w*|pauzuj\w*|pause|stop|wy[łl][aą]cz)\b'),
        ('toggle', r'\b(?:prze[łl][aą]cz\w*|toggle)\b'),
        ('play', r'\b(?:wzn[oó]w|odtw[oó]rz|pu[sś][cć]|pusc|graj|play|w[łl][aą]cz\s+muzyk\w*|start\s+muzyk\w*)\b'),
    ]
    for action, pattern in patterns:
        if re.search(pattern, q):
            return {'tool':'media_control', 'args':{'app':app, 'action':action}}
    return None


def parse_direct_spotify_track_request(text):
    """Select a specific Spotify TRACK, never confuse a basic play/pause command."""
    if not isinstance(text, str) or len(text) > 330:
        return None
    q = text.strip().lower()
    q = re.sub(r'\b(?:spotifya|spotifyu|spotifyem|spotifyie|spotifaj|spotifaja|spotifaju|spotifajem|spotifi|spotyfi)\b', 'spotify', q)
    q = re.sub(r'^(?:(?:hej|hey|hello|ej|siema|cześć|czesc)[,! ]+)?(?:capri|kapri)[,! ]*', '', q)
    q = re.sub(r'^(?:proszę|prosze|weź|wez|mi|teraz)\s+', '', q).strip(' ,.!?')
    q = re.sub(r'^(pos[łl]ucha[łl]|pu[sś]ci[łl])\s+bym\b', r'\1bym', q, flags=re.I)
    # Voice STT can transcribe 'Hej Capri' as 'Hejka Play'. Remove the stray
    # wake-word only if the next words clearly express a listening request.
    q = re.sub(r'^(?:hejka\s+)?(?:play|plej)\s+'
               r'(?=(?:pos[łl]ucha[łl]bym|pos[łl]ucha[łl]abym|'
               r'chcia[łl]bym\s+pos[łl]ucha[cć]|mam\s+ochot[eę]\s+pos[łl]ucha[cć]))',
               '', q, flags=re.I)
    if re.search(r'\b(?:nie|nigdy|bez|zamiast|jak|dlaczego|czy|czy potrafisz|how|why)\b', q):
        return None
    # Explicit track-selection vocabulary. Plain "włącz Spotify" still opens app.
    pattern = (r'^(?:puść|pusc|odtwórz|odtworz|zagraj|włącz|wlacz|odpal|play|posłuchaj|posluchaj)\s+'
               r'(?:(?:mi|piosenkę|piosenke|utwór|utwor|numer|kawałek|kawalek|track)\s+)*'
               r'(.+?)\s+(?:na|w|przez)\s+spotify$')
    match = re.match(pattern, q, flags=re.I)
    if not match:
        match = re.match(r'^spotify[, ]+?(?:puść|pusc|odtwórz|odtworz|zagraj|włącz|wlacz|odpal|play)\s+(.+)$',q,re.I)
    if not match:
        match = re.match(r'^(?:włącz|wlacz|odpal|puść|pusc)\s+(?:na|w)\s+spotify\s+(.+)$',q,re.I)
    if not match:
        # First-person requests are common in natural Polish voice commands.
        # They still require a named song, never a generic desire for music.
        wish = re.match(
            r'^(?:pos[łl]ucha[łl]bym|pos[łl]ucha[łl]abym|'
            r'pu[sś]ci[łl]bym|pu[sś]ci[łl]abym|'
            r'(?:chcia[łl]bym|chcia[łl]abym|chc[eę]|mam\s+ochot[eę])'
            r'\s+(?:sobie\s+)?(?:pos[łl]ucha[cć]|posluchac|pu[sś]ci[cć]|puscic))'
            r'\s+(?:sobie\s+)?(?:(?:piosenk[ięe]|utwor[uó]?|kawa[łl]k[aąu]?|numeru|tracku)\s+)?'
            r'(.+?)(?:\s+(?:na|w|przez)\s+spotify)?$', q, flags=re.I)
        if wish:
            candidate = wish.group(1).strip(' ,.!?\"\'')
            if not re.fullmatch(
                r'(?:muzyk[aię]|czego[sś]|co[sś]|cokolwiek|'
                r'jak[aą][sś]\s+piosenk[aię]|jakiego[sś]\s+utwor[uó]?|'
                r'czego[sś]\s+nowego|spotify)', candidate, flags=re.I):
                match = wish
    if not match:
        # Explicit "play [song]" should work without saying "on Spotify".
        bare = re.match(
            r'^(?:play|puść|pusc|odtwórz|odtworz|zagraj)\s+'
            r'(?:(?:mi|the\s+song|piosenkę|piosenke|utwór|utwor|kawałek|kawalek)\s+)*'
            r'(.+)$', q, flags=re.I)
        if not bare:
            return None
        candidate = bare.group(1).strip(' ,.!?"')
        if (re.match(r'^(?:zagra[łl]bym|pogra[łl]bym|zagra[łl]abym|pogra[łl]abym)\s+w\s+', candidate)
                or re.search(r'\b(?:youtube|film\w*|video|wideo|gra|grę|gre|game|gier\w*|'
                      r'program\w*|aplikacj\w*|playlist\w*|podcast\w*)\b', candidate)
                or re.fullmatch(r'(?:muzyka|muzykę|muzyke|piosenk[iaę]|utwór|utwor|'
                                r'spotify|music|something|cokolwiek|dalej|again)', candidate)):
            return None
        match = bare
    title = match.group(1).strip(' ,.!?\"\'')
    if not 2 <= len(title) <= 180 or title in {'piosenkę','piosenke','piosenki','muzykę','muzyke','muzyka','spotify','odtwarzanie'}:
        return None
    return {'tool':'spotify_play_track', 'args':{'query':title}}


def format_media_result(tool, args, result, lang='pl'):
    if result.get('denied_by_user'):
        return 'Nie zmieniłem odtwarzania.' if lang == 'pl' else 'Playback was not changed.'
    if 'error' in result:
        return ('Nie udało się sterować odtwarzaniem: ' if lang == 'pl' else 'Media control failed: ') + str(result['error'])[:400]
    if tool == 'media_status':
        artist = result.get('artist') or ''
        title = result.get('title') or ''
        if title:
            return 'Teraz: ' + (artist + ' — ' if artist else '') + title
        return 'Odtwarzacz działa, ale nie podał tytułu utworu.' if lang == 'pl' else 'Player did not provide track metadata.'
    names = {'play':'Wysłałem polecenie odtwarzania.', 'pause':'Wysłałem pauzę.',
             'toggle':'Przełączyłem odtwarzanie.', 'next':'Wysłałem następny utwór.',
             'previous':'Wysłałem poprzedni utwór.',
             'volume':'Ustawiłem głośność Spotify.', 'volume_delta':'Zmieniłem głośność Spotify.',
             'seek':'Przewinąłem utwór.', 'seek_delta':'Przewinąłem utwór.'}
    # WinRT acknowledges request but cannot guarantee music will audibly play.
    return names.get(args.get('action'), 'Wysłałem polecenie odtwarzaczowi.')
