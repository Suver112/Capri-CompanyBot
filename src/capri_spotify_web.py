# -*- coding: utf-8 -*-
"""Spotify track playback with explicit user OAuth PKCE approval.

No password scraping. Credentials live in the OS credential store. If disconnected,
open a search page and *do not pretend playback began*.
"""
from __future__ import annotations
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
import secrets
import time
from urllib import error, parse, request
import webbrowser

SERVICE = 'Capri Spotify Playback'
CALLBACK = 'http://127.0.0.1:8765/callback'
SCOPES = 'user-read-private user-read-playback-state user-modify-playback-state'


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError as exc:
        raise RuntimeError('Spotify: brak biblioteki keyring. Zainstaluj wymagania Capri.') from exc


def _store(name, value):
    _keyring().set_password(SERVICE, name, value)


def _load(name):
    return _keyring().get_password(SERVICE, name) or ''


def _form_post(url, data):
    req = request.Request(url, data=parse.urlencode(data).encode(),
                          headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
    try:
        with request.urlopen(req, timeout=25) as res:
            return json.loads(res.read(300000).decode())
    except error.HTTPError as exc:
        raise RuntimeError('Spotify OAuth: HTTP ' + str(exc.code) + '. Sprawdź Client ID i adres przekierowania.') from exc


def connect(client_id: str):
    """Interactive *local console* pairing. Requires a Spotify developer app ID."""
    client_id = client_id.strip()
    if not re.fullmatch(r'[a-zA-Z0-9]{20,80}', client_id):
        raise ValueError('Wpisz poprawny Spotify Client ID ze Spotify Developer Dashboard.')
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip('=')
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state = secrets.token_urlsafe(24)
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            data = parse.urlsplit(self.path)
            params = parse.parse_qs(data.query)
            if data.path != '/callback' or params.get('state', [''])[0] != state:
                self.send_error(400, 'Invalid OAuth state'); return
            result['code'] = params.get('code', [''])[0]
            result['error'] = params.get('error', [''])[0]
            body = ('Spotify polaczono z Capri. Mozesz zamknac to okno.' if result['code']
                    else 'Odmowa polaczenia Spotify.').encode('utf-8')
            self.send_response(200 if result['code'] else 400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def log_message(self, fmt, *args):
            pass

    with HTTPServer(('127.0.0.1', 8765), CallbackHandler) as server:
        server.timeout = 180
        query = parse.urlencode({'response_type':'code','client_id':client_id,
                                 'scope': SCOPES, 'redirect_uri':CALLBACK,
                                 'code_challenge_method':'S256','code_challenge':challenge,
                                 'state':state})
        print('Otwieram logowanie Spotify. Zatwierdz dostep w przegladarce...')
        webbrowser.open('https://accounts.spotify.com/authorize?' + query)
        deadline = time.monotonic() + 180
        server.timeout = 2
        while not result.get('code') and not result.get('error') and time.monotonic() < deadline:
            server.handle_request()
    if not result.get('code'):
        raise RuntimeError('Spotify: nie otrzymano autoryzacji. ' + result.get('error', 'Przekroczono czas lub anulowano.'))
    tokens = _form_post('https://accounts.spotify.com/api/token', {
        'grant_type':'authorization_code','code':result['code'],
        'redirect_uri':CALLBACK,'client_id':client_id,'code_verifier':verifier})
    if not tokens.get('access_token') or not tokens.get('refresh_token'):
        raise RuntimeError('Spotify nie zwrocil wymaganych tokenow.')
    _store('client_id', client_id)
    _store('refresh_token', tokens['refresh_token'])
    _store('access_token', tokens['access_token'])
    _store('expires_at', str(int(time.time() + tokens.get('expires_in', 3600) - 60)))
    return True


def _access_token():
    client_id = _load('client_id')
    refresh = _load('refresh_token')
    if not client_id or not refresh:
        raise RuntimeError('Spotify nie jest połączone. W ustawieniach wybierz POŁĄCZ SPOTIFY API.')
    token = _load('access_token')
    if token and int(_load('expires_at') or '0') > time.time():
        return token
    data = _form_post('https://accounts.spotify.com/api/token', {
        'grant_type':'refresh_token','refresh_token':refresh,'client_id':client_id})
    if not data.get('access_token'):
        raise RuntimeError('Spotify: nie udało się odświeżyć tokenu. Połącz konto ponownie.')
    _store('access_token', data['access_token'])
    _store('expires_at', str(int(time.time() + data.get('expires_in', 3600) - 60)))
    if data.get('refresh_token'):
        _store('refresh_token', data['refresh_token'])
    return data['access_token']


def _api(method, path, body=None):
    token = _access_token()
    url = 'https://api.spotify.com/v1' + path
    headers = {'Authorization':'Bearer ' + token, 'Accept':'application/json'}
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode('utf-8')
    req = request.Request(url, method=method, data=data, headers=headers)
    try:
        with request.urlopen(req, timeout=25) as res:
            payload = res.read(2_000_000)
            return json.loads(payload.decode('utf-8')) if payload else {}
    except error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError('Spotify API odrzuciło dostęp (HTTP 403). Sprawdź Spotify Premium, uprawnienia user-modify-playback-state oraz listę użytkowników aplikacji w Spotify Developer Dashboard.') from exc
        if exc.code == 404:
            raise RuntimeError('Spotify nie wykrywa aktywnego urządzenia. Otwórz Spotify i uruchom dowolny utwór.') from exc
        if exc.code == 401:
            raise RuntimeError('Spotify: brak autoryzacji. Połącz konto ponownie.') from exc
        detail = ''
        if exc.code == 400:
            try:
                raw = exc.read(1000).decode('utf-8','replace')
                parsed = json.loads(raw)
                message = parsed.get('error', {}) if isinstance(parsed, dict) else {}
                if isinstance(message, dict):
                    detail = str(message.get('message',''))
            except (ValueError, OSError, UnicodeError):
                pass
            detail = re.sub(r'[\r\n\t]+', ' ', detail)[:180]
        raise RuntimeError(f'Spotify API: HTTP {exc.code}' + (': ' + detail if detail else '.') ) from exc


def _album_context_for_track(item: dict, track_uri: str) -> str:
    """Album context avoids a current Spotify desktop-client regression.

    Several desktop clients acknowledge a single-track ``uris`` request with
    HTTP 204, then clear the current player instead of starting the new track.
    Never fall back to that destructive request when album context is absent.
    """
    album = item.get('album') or {}
    album_uri = str(album.get('uri') or '') if isinstance(album, dict) else ''
    if not re.fullmatch(r'spotify:album:[A-Za-z0-9]+', album_uri):
        track_id = track_uri.rsplit(':', 1)[-1]
        detail = _api('GET', '/tracks/' + track_id)
        album = detail.get('album') or {}
        album_uri = str(album.get('uri') or '') if isinstance(album, dict) else ''
    if not re.fullmatch(r'spotify:album:[A-Za-z0-9]+', album_uri):
        raise RuntimeError(
            'Spotify nie zwrócił albumu wybranego utworu. '
            'Nie przerywam bieżącego odtwarzania; spróbuj innego utworu.')
    return album_uri


def _original_cyberpunk_track(query: str) -> bool:
    return 'i really want to stay at your house' in query.casefold()


def _verified_song_name(item: dict) -> bool:
    """Don't accept a karaoke/cover/remix just because Spotify ranks it first."""
    import unicodedata
    name = unicodedata.normalize('NFKC', str(item.get('name') or '')).casefold().strip()
    name = re.sub(r'\s+', ' ', name)
    authors = ' '.join(str(a.get('name','')).casefold() for a in item.get('artists', []))
    return name == 'i really want to stay at your house' and ('rosa walton' in authors or 'hallie coggins' in authors)


def _find_safely(query: str) -> dict:
    """Search exact original first, and refuse substituting an unrelated result."""
    original = _original_cyberpunk_track(query)
    if original:
        queries = [
            'track:"I Really Want to Stay at Your House" artist:"Rosa Walton"',
            'I Really Want to Stay at Your House Rosa Walton Hallie Coggins',
            'I Really Want to Stay at Your House',
        ]
    else:
        queries = [query]
    for q in queries:
        tracks = _api('GET', '/search?' + parse.urlencode(
            {'q':q, 'type':'track','limit':10 if original else 5})).get('tracks', {}).get('items', [])
        if not tracks:
            continue
        if not original:
            return tracks[0]
        for track in tracks:
            if _verified_song_name(track) and re.fullmatch(r'spotify:track:[A-Za-z0-9]+', str(track.get('uri') or '')):
                return track
    if original:
        raise RuntimeError('Nie znalazłem w Spotify oryginalnego nagrania Rosa Walton / Hallie Coggins. Nie odtwarzam przypadkowego zamiennika.')
    raise RuntimeError('Spotify nie znalazł pasującego utworu: ' + query)


def _track_position_in_album(album_uri: str, track_uri: str) -> int | None:
    """Get an actual index; album-context offset by URI can produce HTTP 400
    when Spotify relinks a track to a different regional release.
    """
    album_id = album_uri.rsplit(':', 1)[-1]
    needle = track_uri.rsplit(':', 1)[-1]
    for offset in range(0, 300, 50):
        page = _api('GET', '/albums/' + album_id + '/tracks?' + parse.urlencode(
            {'limit':50, 'offset':offset}))
        items = page.get('items') or []
        for i, item in enumerate(items):
            if item.get('id') == needle or item.get('uri') == track_uri:
                return offset + i
        if len(items) < 50:
            break
    return None


def spotify_play_track(query: str):
    """Play a verified Spotify track; never silently substitute another title.

    A track's album context is preferred for Spotify Desktop where a bare
    'uris' command may return 204 without actually starting a new song.
    We confirm the actual playing item before claiming success.
    """
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 180:
        raise ValueError('Spotify: podaj konkretny tytuł lub wykonawcę (2–180 znaków).')
    item = _find_safely(query.strip())
    uri = str(item.get('uri') or '')
    if not re.fullmatch(r'spotify:track:[A-Za-z0-9]+', uri):
        raise RuntimeError('Spotify zwrócił nieprawidłowy identyfikator utworu.')
    # Validate the playback target before fetching album context. A missing
    # device must report a device issue, not an unrelated missing-album error.
    devices = _api('GET','/me/player/devices').get('devices', []) or []
    available = [d for d in devices if d.get('id') and not d.get('is_restricted')]
    computers = [d for d in available if str(d.get('type','')).casefold() in ('computer', 'desktop')]
    active_computer = next((d for d in computers if d.get('is_active')), None)
    if active_computer:
        active = active_computer
    elif len(computers) == 1:
        active = computers[0]
    elif not computers:
        active = next((d for d in available if d.get('is_active')), None)
        if active is None and len(available) == 1:
            active = available[0]
    else:
        active = None
    if active is None:
        raise RuntimeError('Spotify: brak aktywnego odtwarzacza lub urządzenie niedostępne. Otwórz Spotify na tym komputerze.')
    device_id = str(active['id'])
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', device_id):
        raise RuntimeError('Spotify: odtwarzacz ma nieprawidłowy identyfikator.')
    album_uri = _album_context_for_track(item, uri)
    endpoint = '/me/player/play?' + parse.urlencode({'device_id':device_id})
    # Spotify allows offset by album position or URI. A verified numeric index
    # is preferable where URI offset is rejected as invalid (HTTP 400).
    try:
        index = _track_position_in_album(album_uri, uri)
    except (RuntimeError, ValueError, OSError):
        index = None
    if index is not None:
        try:
            _api('PUT', endpoint, {'context_uri':album_uri, 'offset':{'position':index}})
        except RuntimeError as exc:
            if 'HTTP 400' not in str(exc):
                raise
            _api('PUT', endpoint, {'context_uri':album_uri, 'offset':{'uri':uri}})
    else:
        try:
            _api('PUT', endpoint, {'context_uri':album_uri, 'offset':{'uri':uri}})
        except RuntimeError as exc:
            if 'HTTP 400' not in str(exc):
                raise
            # For a non-desktop client the official single-track URI format is
            # a reasonable last resort. On Desktop it can blank the playlist.
            if str(active.get('type','')).casefold() in ('computer','desktop'):
                raise RuntimeError('Spotify odrzucił kontekst albumu (HTTP 400). Nie zastępuję utworu losowym wynikiem. Szczegóły: ' + str(exc)[:170]) from exc
            _api('PUT', endpoint, {'uris':[uri]})
    # Neither HTTP 204 nor having a valid device is proof of playback.
    confirmed = False
    for attempt in range(5):
        time.sleep(0.4)
        try:
            state = _api('GET', '/me/player')
        except (RuntimeError, OSError):
            continue
        if not isinstance(state, dict):
            continue
        current = state.get('item') or {}
        if isinstance(current, dict) and (current.get('uri') == uri or current.get('id') == uri.rsplit(':',1)[-1]) and state.get('is_playing'):
            confirmed = True
            break
    artists = ', '.join(str(a.get('name','')) for a in item.get('artists', [])[:3])
    return {'status':'playing_confirmed' if confirmed else 'playback_unverified',
            'title':str(item.get('name',''))[:150], 'artist':artists[:200],
            'device':str(active.get('name','Spotify'))[:80]}



def spotify_playback_control(action: str, value: int | None = None):
    """Authenticated Spotify Connect control. Mutates only active playback.

    Playback start of a *new track* remains in spotify_play_track (album context)
    and is intentionally not modified by this helper.
    """
    action = str(action or '').casefold().strip()
    allowed = {'play', 'pause', 'next', 'previous', 'volume', 'volume_delta',
               'seek', 'seek_delta'}
    if action not in allowed:
        raise ValueError('Nieznana operacja Spotify.')
    if not connected():
        raise RuntimeError('Spotify API niepołączone. Połącz Spotify w ustawieniach.')
    player = _api('GET', '/me/player')
    if not isinstance(player, dict) or not player.get('device'):
        raise RuntimeError('Spotify: nie znaleziono aktywnego odtwarzacza. Uruchom muzykę w Spotify.')
    device = player['device']
    if device.get('is_restricted'):
        raise RuntimeError('Spotify: obecne urządzenie nie pozwala na zdalne sterowanie.')
    device_id = str(device.get('id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', device_id):
        raise RuntimeError('Spotify: nieprawidłowy identyfikator odtwarzacza.')
    suffix = '?' + parse.urlencode({'device_id': device_id})
    if action in ('volume', 'volume_delta'):
        if not device.get('supports_volume', True):
            raise RuntimeError('Spotify: urządzenie nie udostępnia regulacji głośności.')
        current = device.get('volume_percent')
        if action == 'volume_delta' and current is None:
            raise RuntimeError('Spotify nie podało aktualnej głośności; podaj wartość docelową, np. 40%.')
        target = int(value) + (int(current) if action == 'volume_delta' else 0)
        target = max(0, min(100, target))
        _api('PUT', '/me/player/volume?' + parse.urlencode({'volume_percent': target, 'device_id': device_id}))
        return {'action': action, 'app': 'spotify', 'accepted': True, 'value': target}
    if action in ('seek', 'seek_delta'):
        progress = player.get('progress_ms')
        if action == 'seek_delta' and progress is None:
            raise RuntimeError('Spotify nie podało aktualnego czasu utworu.')
        pos = int(value) + (int(progress) if action == 'seek_delta' else 0)
        duration = (player.get('item') or {}).get('duration_ms')
        # Never unintentionally skip a track when seeking beyond the end.
        pos = max(0, min(pos, max(0, int(duration) - 300) if duration else 86_400_000))
        _api('PUT', '/me/player/seek?' + parse.urlencode({'position_ms': pos, 'device_id': device_id}))
        return {'action': action, 'app': 'spotify', 'accepted': True, 'value': pos}
    method, endpoint = {'play': ('PUT', '/me/player/play'),
                        'pause': ('PUT', '/me/player/pause'),
                        'next': ('POST', '/me/player/next'),
                        'previous': ('POST', '/me/player/previous')}[action]
    _api(method, endpoint + suffix)
    return {'action': action, 'app': 'spotify', 'accepted': True}

def spotify_search_page(query: str):
    """Explicit fallback when OAuth isn't configured; this is NOT playback."""
    if not isinstance(query, str) or not query.strip() or len(query) > 180:
        raise ValueError('Spotify: nieprawidłowe wyszukiwanie.')
    url = 'https://open.spotify.com/search/' + parse.quote(query.strip(), safe='')
    webbrowser.open(url)
    return {'status':'search_opened', 'query':query.strip(), 'url':url}


def connected():
    try:
        return bool(_load('client_id') and _load('refresh_token'))
    except Exception:
        return False
