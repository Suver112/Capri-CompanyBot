"""Explicit, approved Windows browser actions using the system default browser.

Direct commands are intentional: no language-model inference is needed to open
an incognito window. All actions are still individually approved by AgentRuntime.
"""
from __future__ import annotations

import ipaddress
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote_plus, urlsplit

BROWSERS = {
    'edge': ('msedge.exe', ['--new-tab'], ['--inprivate', '--new-window']),
    'chrome': ('chrome.exe', ['--new-tab'], ['--incognito', '--new-window']),
    'brave': ('brave.exe', ['--new-tab'], ['--incognito', '--new-window']),
    'firefox': ('firefox.exe', ['-new-tab'], ['-private-window']),
    'opera': ('opera.exe', [], ['--private']),
}
KNOWN = {spec[0]: browser for browser, spec in BROWSERS.items()}
SITES = {
    'youtube': 'https://www.youtube.com/', 'yt': 'https://www.youtube.com/',
    'google': 'https://www.google.com/', 'wikipedia': 'https://pl.wikipedia.org/',
    'reddit': 'https://www.reddit.com/', 'github': 'https://github.com/',
    'twitch': 'https://www.twitch.tv/', 'spotify': 'https://open.spotify.com/',
    'gmail': 'https://mail.google.com/', 'facebook': 'https://www.facebook.com/',
    'instagram': 'https://www.instagram.com/',
    'netflix': 'https://www.netflix.com/', 'disney plus': 'https://www.disneyplus.com/',
    'disney+': 'https://www.disneyplus.com/', 'prime video': 'https://www.primevideo.com/',
    'amazon': 'https://www.amazon.pl/', 'allegro': 'https://allegro.pl/',
    'steam': 'https://store.steampowered.com/', 'epic games': 'https://store.epicgames.com/',
    'stackoverflow': 'https://stackoverflow.com/', 'stack overflow': 'https://stackoverflow.com/',
    'gitlab': 'https://gitlab.com/', 'soundcloud': 'https://soundcloud.com/',
    'pinterest': 'https://www.pinterest.com/', 'x.com': 'https://x.com/',
    'twitter': 'https://x.com/', 'tiktok': 'https://www.tiktok.com/',
    'wykop': 'https://www.wykop.pl/', 'filmweb': 'https://www.filmweb.pl/',
    'twitch.tv': 'https://www.twitch.tv/', 'chatgpt': 'https://chatgpt.com/',

}
BROWSER_ALIASES = (
    ('firefoksie', 'firefox'), ('firefoks', 'firefox'), ('firefox', 'firefox'),
    ('chromie', 'chrome'), ('chrome', 'chrome'), ('edge', 'edge'), ('edgu', 'edge'),
    ('brave', 'brave'), ('operze', 'opera'), ('opera', 'opera'),
)
# A domain/URL, never a local file, script scheme, command line or userinfo URL.
_DOMAIN = re.compile(r'(?i)\b(?:https?://)?(?:[a-z\d-]+\.)+[a-z]{2,}(?::\d{1,5})?(?:/[^\s<>"\']*)?')
_SEARCH_VIDEO = re.compile(r'(?i)^\s*(?:wyszukaj|szukaj|znajdź|znajdz|search(?: for)?)\s+(?:na|w|on)\s+(?:youtube|yt)\s+(.+?)\s*$')
_POSITIVE = re.compile(r'(?i)\b(?:otw[oó]rz|otwieraj|w[łl][aą]cz|uruchom|stw[oó]rz|odpal|wejd[źz]|przejd[źz]|open|launch|go to|visit)\b')


def normalize_navigation_target(target: str) -> str:
    """Public HTTPS websites only: never turn user text into executable arguments."""
    if not isinstance(target, str) or not target.strip() or len(target) > 1900:
        raise ValueError('Podaj krótki adres publicznej strony HTTPS.')
    raw = target.strip().strip('"\'')
    raw = SITES.get(raw.casefold(), raw)
    if raw.startswith('//') or any(c.isspace() or ord(c) < 32 for c in raw):
        raise ValueError('Nieprawidłowy adres strony.')
    if not re.match(r'^https?://', raw, re.I):
        raw = 'https://' + raw
    parts = urlsplit(raw)
    if parts.scheme.lower() != 'https' or not parts.hostname or parts.username or parts.password:
        raise ValueError('Otwieram wyłącznie publiczne strony HTTPS.')
    if parts.fragment and any(c in parts.fragment for c in ('\n', '\r')):
        raise ValueError('Nieprawidłowy adres.')
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError('Niepoprawny port w adresie.') from exc
    if port and port != 443:
        raise ValueError('Dozwolony jest wyłącznie standardowy port HTTPS.')
    host = parts.hostname.lower().rstrip('.')
    if host in ('localhost',) or host.endswith('.localhost') or host.endswith('.local'):
        raise ValueError('Adresy lokalne są zablokowane.')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if '.' not in host or any(not label or label.startswith('-') or label.endswith('-') for label in host.split('.')):
            raise ValueError('To nie jest poprawna domena publicznej strony.')
    else:
        raise ValueError('Bezpośrednie adresy IP nie są obsługiwane.')
    # Preserve path/query/fragment verbatim, but never pass it to a shell.
    return raw


def _clean_command(text: str) -> str:
    t = re.sub(r'\s+', ' ', text.strip()).strip(' ,.!?')
    for _ in range(4):
        before = t
        t = re.sub(r'^(?:hej(?:ka)?|siema|cześć|czesc|hey|hi)[!, ]+', '', t, flags=re.I)
        t = re.sub(r'^(?:capri|kapri)[!, ]+', '', t, flags=re.I)
        t = re.sub(r'^(?:proszę|prosze|możesz|mozesz|weź|wez)[, ]+', '', t, flags=re.I)
        if t == before:
            break
    return t


def parse_browser_request(text: str) -> dict | None:
    """Recognize intentional commands, not questions, quotes or negative orders."""
    if not isinstance(text, str) or len(text) > 2000:
        return None
    t = _clean_command(text)
    if re.match(r'(?i)^(?:czy|dlaczego|jak|po co|nie|bez|what|can you|could you|why|how)\b', t):
        return None
    if re.search(r'(?i)\b(?:nie otwieraj|nie włączaj|nie wlaczaj|nie uruchamiaj|nie wchodź|nie wchodz)\b', t):
        return None
    browser = 'default'
    # Browser name must be mentioned as a browser, not the destination URL.
    for alias, name in BROWSER_ALIASES:
        if re.search(r'\b' + re.escape(alias) + r'\b', t, re.I):
            browser = name
            break
    video = _SEARCH_VIDEO.match(t)
    if video:
        query = video.group(1).strip()
        if not query or len(query) > 250:
            return None
        return {'action': 'open_url', 'browser': browser,
                'url': 'https://www.youtube.com/results?search_query=' + quote_plus(query)}
    if not _POSITIVE.search(t):
        return None
    private = re.search(r'(?i)\b(?:incognito|inprivate|prywatn\w*|private(?: window)?)\b', t)
    new_tab = re.search(r'(?i)\b(?:now[aą]\s+kart[ęeaę]|new\s+tab)\b', t)
    action = 'private_window' if private else ('new_tab' if new_tab else 'open_url')
    candidate = _DOMAIN.search(t)
    url = None
    if candidate:
        try:
            url = normalize_navigation_target(candidate.group(0).rstrip('.,;:!?'))
        except ValueError:
            return None
    else:
        # Named services as destination, not just the name of an app to launch.
        for alias, site in SITES.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', t, re.I):
                # Allow "otwórz YouTube", but not "otwórz nową kartę w Chrome".
                url = site
                break
    if action == 'open_url' and not url:
        # The previous hard-coded allowlist prevented visiting virtually any
        # less-popular site. Explicit WEB navigation may open a search for the
        # named destination, but arbitrary 'launch game/application' commands
        # must still go to app discovery, never here.
        is_web_navigation = bool(re.search(
            r'(?i)\b(?:stron[ęeaey]|witryn[ęeya]|portal\w*|website|webpage|'
            r'przegl[aą]dar\w*|adres\w*|www|https?://|wejd[źz]|przejd[źz])\b', t))
        if not is_web_navigation:
            return None
        phrase = re.sub(r'(?i)^(?:otw[oó]rz|wejd[źz]|przejd[źz]|uruchom|w[łl][aą]cz|odpal|open|go to|visit)\s+', '',t)
        phrase = re.sub(r'(?i)^(?:na|do|stron[ęeaey]|witryn[ęeya]|portal\w*|website|webpage|w)\s+', '', phrase)
        phrase = re.sub(r'(?i)\s+(?:w|na|przez)\s+przegl[aą]dar\w*.*$', '', phrase)
        phrase = phrase.strip(' .,!?')
        if not 2 <= len(phrase) <= 110:
            return None
        url = 'https://www.google.com/search?q=' + quote_plus(phrase)

    result = {'action': action, 'browser': browser}
    if url:
        result['url'] = url
    return result


def _browser_from_registry_progid(progid: str) -> str | None:
    value = str(progid).casefold()
    for term, browser in [('brave', 'brave'), ('firefox', 'firefox'),
                          ('chrome', 'chrome'), ('opera', 'opera'),
                          ('microsoftedge', 'edge'), ('msedge', 'edge'), ('msehtml', 'edge'), ('edge', 'edge')]:
        if term in value:
            return browser
    return None


def _default_browser() -> str | None:
    """Read Windows HTTPS UserChoice; never silently substitute Edge."""
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice') as key:
            progid = str(winreg.QueryValueEx(key, 'ProgId')[0])
        recognized = _browser_from_registry_progid(progid)
        if recognized:
            return recognized
        # Some default apps use an AppX id rather than a readable browser name.
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid + r'\shell\open\command') as key:
            command = str(winreg.QueryValueEx(key, '')[0]).casefold()
        return next((name for exe, name in KNOWN.items() if exe in command), None)
    except (OSError, ImportError, ValueError):
        return None


def _browser_paths(browser: str) -> list[Path]:
    exe = BROWSERS[browser][0]
    paths = []
    if sys.platform == 'win32':
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, rf'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}') as key:
                        paths.append(Path(str(winreg.QueryValueEx(key, '')[0]).strip('"')))
                except OSError:
                    continue
        except ImportError:
            pass
    program_files = (os.environ.get('ProgramFiles',r'C:\Program Files'),
                     os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))
    local = os.environ.get('LOCALAPPDATA','')
    folders = {
        'edge': [f'{program_files[0]}/Microsoft/Edge/Application',f'{program_files[1]}/Microsoft/Edge/Application'],
        'chrome': [f'{program_files[0]}/Google/Chrome/Application',f'{program_files[1]}/Google/Chrome/Application',f'{local}/Google/Chrome/Application'],
        'brave': [f'{program_files[0]}/BraveSoftware/Brave-Browser/Application',f'{program_files[1]}/BraveSoftware/Brave-Browser/Application',f'{local}/BraveSoftware/Brave-Browser/Application'],
        'firefox': [f'{program_files[0]}/Mozilla Firefox',f'{program_files[1]}/Mozilla Firefox'],
        'opera': [f'{local}/Programs/Opera',f'{local}/Programs/Opera GX',f'{program_files[0]}/Opera',f'{program_files[1]}/Opera'],
    }
    paths.extend(Path(folder) / exe for folder in folders[browser])
    return paths


def launch_browser_action(action: str, browser: str = 'default', url: str | None = None) -> dict:
    """Execute the single approved action using system default or an explicit browser."""
    if sys.platform != 'win32':
        raise RuntimeError('Sterowanie przeglądarką wymaga Windows.')
    if action not in ('new_tab', 'private_window', 'open_url') or browser not in (*BROWSERS, 'default'):
        raise ValueError('Nieobsługiwana akcja lub przeglądarka.')
    target = normalize_navigation_target(url) if url else None
    selected = _default_browser() if browser == 'default' else browser
    if browser == 'default' and target and action != 'private_window':
        # Windows ShellExecute honors the user's real HTTPS association, even
        # when the ProgId belongs to a browser Capri does not recognize.
        os.startfile(target)
        return {'browser': selected or 'system-default', 'action': action, 'status': 'launched',
                'opened_url': target, 'message': 'Wysłano stronę do domyślnej przeglądarki Windows.'}
    if selected is None:
        raise RuntimeError('Windows nie udostępnia rozpoznawalnej domyślnej przeglądarki. '
                           'Ustaw domyślną przeglądarkę dla HTTPS lub podaj jej nazwę.')
    candidates = [p for p in _browser_paths(selected)
                  if p.is_file() and p.name.lower() == BROWSERS[selected][0]]
    if not candidates:
        raise FileNotFoundError(f'Nie znalazłem {selected}. Sprawdź przeglądarkę domyślną w Windows.')
    _, tab, private = BROWSERS[selected]
    args = list(private if action == 'private_window' else tab)
    args.append(target or 'about:blank')
    subprocess.Popen([str(candidates[0]), *args], shell=False, close_fds=True)
    return {'browser': selected, 'action': action, 'status': 'launched',
            **({'opened_url': target} if target else {}),
            'message': 'Wysłano polecenie otwarcia okna prywatnego.' if action == 'private_window'
                       else 'Wysłano polecenie otwarcia strony.' if target
                       else 'Wysłano polecenie otwarcia nowej karty.'}
