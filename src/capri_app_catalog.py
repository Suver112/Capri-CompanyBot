"""Read-only Windows app/game/folder discovery and explicit, approved launching.

No global disk scan, no shell=True, no executable from web content, no arbitrary
paths supplied by the LLM to the launcher. Candidates are rebuilt from local,
well-known OS/launcher indexes and referenced by opaque IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata
import hashlib
import json
import os
from pathlib import Path
import re
import time
import subprocess
import sys
from urllib.parse import quote
from typing import Callable


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    kind: str                   # program | game | folder
    source: str
    launch_type: str            # shortcut | executable | steam | uwp | folder
    value: str

    @property
    def id(self) -> str:
        key = '\0'.join((self.kind, self.launch_type, self.value.casefold()))
        return hashlib.sha256(key.encode('utf-8')).hexdigest()[:20]

    def public(self, *, score: int = 0) -> dict:
        return {'id': self.id, 'name': self.name[:120], 'kind': self.kind,
                'source': self.source, 'score': score}


def normalize(value: str) -> str:
    value = str(value).casefold().replace('_', ' ')
    value = re.sub(r'(?<=\w)[.-](?=\w)', ' ', value)
    value = re.sub(r'[^\w\s]+', ' ', value, flags=re.UNICODE)
    return ' '.join(value.split())[:180]


def _search_tokens(text: str) -> list[str]:
    """Accent/STT-tolerant tokens. Real installed catalog is still authoritative."""
    value = unicodedata.normalize('NFKD', normalize(text))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r'\b(?:trzydziesci\s+trzy|thirty\s+three)\b', '33', value)
    aliases = {'ekspedycja': 'expedition', 'ekspedycje': 'expedition',
               'ekspedycje': 'expedition', 'expedycja': 'expedition',
               'obscuro': 'obscur', 'obskur': 'obscur', 'obskuro': 'obscur',
               'wiedzmin': 'witcher', 'wiedzmina': 'witcher',
               'cyberpunka': 'cyberpunk', 'cyberpank': 'cyberpunk',
               'cyberpanka': 'cyberpunk', 'cyber pank': 'cyberpunk',
               'spotifya': 'spotify', 'spotifyu': 'spotify', 'spotifyem': 'spotify',
               'spotifyie': 'spotify', 'spotifaj': 'spotify', 'spotifaju': 'spotify',
               'spotifaja': 'spotify', 'spotifajem': 'spotify', 'spotifi': 'spotify',
               'spotyfi': 'spotify', 'steamie': 'steam', 'steama': 'steam',
               'steamu': 'steam', 'steamem': 'steam', 'stimie': 'steam',
               'stima': 'steam', 'stimu': 'steam', 'epicu': 'epic', 'epica': 'epic',
               'epikiem': 'epic', 'discordzie': 'discord', 'discorda': 'discord',
               'discordem': 'discord', 'chromie': 'chrome', 'chromea': 'chrome',
               'operze': 'opera', 'firefoksie': 'firefox', 'firefoksa': 'firefox',
               'vscode': 'visual studio code'}
    return [aliases.get(token, token) for token in value.split()]


def _near_word(query_token: str, title_token: str) -> bool:
    if query_token == title_token:
        return True
    if len(query_token) < 4 or len(title_token) < 4:
        return False
    if len(query_token) >= 5 and title_token.startswith(query_token):
        return True
    # STT often adds/removes one syllable: Obscur -> Obscuro.
    return SequenceMatcher(None, query_token, title_token).ratio() >= .80


def match_score(query: str, name: str) -> int:
    """Rank short names, subtitles and plausible STT mistakes against installed titles.

    Never infer an AppID from a name; resolution still uses LocalCatalog entries.
    Scores under 78 are treated as suggestions, not confident launch matches.
    """
    q, n = normalize(query), normalize(name)
    qt, nt = _search_tokens(query), _search_tokens(name)
    if not qt or not nt: return 0
    # Two common cross-language game references, while still matching the
    # user's *installed* games rather than a global title-to-AppID lookup.
    if q in {'cp2077', 'cp 2077'}: qt = ['cyberpunk', '2077']
    if q in {'gta5', 'gta v'}: qt = ['gta', 'v']
    if qt == nt: return 120
    # One word may identify a game, but its confidence must stay lower;
    # a bare number like '33' must never auto-match a long title.
    if len(qt) == 1 and len(nt) > 1:
        return 79 if len(qt[0]) >= 5 and any(_near_word(qt[0], y) for y in nt) else 0
    if len(qt) <= len(nt) and nt[:len(qt)] == qt: return 106
    if len(qt) <= len(nt) and any(nt[i:i+len(qt)] == qt for i in range(len(nt)-len(qt)+1)):
        return 98
    # Match descriptive title fragments, e.g. 'Expedition 33' in
    # 'Clair Obscur: Expedition 33' or 'Clair Obscuro' in the same title.
    if len(qt) >= 2 and all(any(_near_word(x, y) for y in nt) for x in qt):
        return 93 if len(qt) >= 3 else 89
    # Word-order differences: '33 Expedition', 'obscur clair'.
    if len(qt) >= 2 and all(any(x == y for y in nt) for x in qt):
        return 88
    # A single distinctive title fragment is useful only when it is not
    # potentially one of many series entries (the caller checks ambiguity).
    if len(qt) == 1 and len(qt[0]) >= 5 and any(_near_word(qt[0], y) for y in nt):
        return 79
    # Title + platform suffixes, e.g. 'Cyberpunka'.
    if len(qt) >= 2 and sum(any(_near_word(x, y) for y in nt) for x in qt) == len(qt)-1:
        return 64
    ratio = SequenceMatcher(None, ' '.join(qt), ' '.join(nt)).ratio()
    return round(ratio * 65) if ratio >= .79 else 0


def _env_path(name: str) -> Path | None:
    val = os.environ.get(name, '').strip()
    return Path(val) if val else None


def _path_str(p: Path) -> str:
    return str(p.resolve(strict=False))


def windows_known_folders(home: Path) -> list[Path]:
    """User-reassigned paths from Explorer registry, e.g. moved Downloads/OneDrive."""
    result=[]
    if sys.platform != 'win32': return result
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
            for reg_name in ('Desktop','Personal','My Pictures','My Music','My Video',
                             '{374DE290-123F-4565-9164-39C4925E467B}'):
                try:
                    raw=str(winreg.QueryValueEx(key,reg_name)[0])
                    raw=os.path.expandvars(raw.replace('%USERPROFILE%',str(home)))
                    path=Path(raw)
                    if path.is_dir(): result.append(path)
                except (OSError,ValueError): pass
    except (OSError,ImportError): pass
    return result

def start_menu_directories(home: Path) -> list[Path]:
    appdata = _env_path('APPDATA') or home/'AppData'/'Roaming'
    programdata = _env_path('PROGRAMDATA') or Path('C:/ProgramData')
    public = _env_path('PUBLIC') or home.parent/'Public'
    dirs = [appdata/'Microsoft'/'Windows'/'Start Menu'/'Programs',
            programdata/'Microsoft'/'Windows'/'Start Menu'/'Programs',
            public/'Desktop',home/'Desktop']
    onedrive = _env_path('OneDrive')
    if onedrive: dirs.append(onedrive/'Desktop')
    return list(dict.fromkeys(p for p in dirs if p.is_dir()))


def _scan_shortcuts(home: Path):
    for base in start_menu_directories(home):
        # Windows native shortcuts: never execute at enumeration time.
        for folder, dirs, files in os.walk(base, followlinks=False):
            if len(Path(folder).relative_to(base).parts) > 5:
                dirs[:] = []; continue
            dirs[:] = sorted(x for x in dirs if not (Path(folder)/x).is_symlink())[:80]
            for fname in sorted(files):
                path = Path(folder)/fname
                if path.suffix.lower() != '.lnk' or path.is_symlink(): continue
                name = path.stem.strip()
                if name and name.casefold() not in ('uninstall','odinstaluj'):
                    yield CatalogEntry(name,'program','Menu Start / skrót','shortcut',_path_str(path))


def _scan_app_paths():
    if sys.platform != 'win32': return
    try: import winreg
    except ImportError: return
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        key_path = r'Software\Microsoft\Windows\CurrentVersion\App Paths'
        try: base=winreg.OpenKey(hive,key_path)
        except OSError: continue
        with base:
            try: count=winreg.QueryInfoKey(base)[0]
            except OSError: count=0
            for i in range(min(count,2000)):
                try:
                    name=winreg.EnumKey(base,i)
                    with winreg.OpenKey(base,name) as sub:
                        target=str(winreg.QueryValueEx(sub,'')[0])
                    path=Path(os.path.expandvars(target.strip('"')))
                    if path.is_file() and path.suffix.lower()=='.exe':
                        yield CatalogEntry(path.stem,'program','Windows App Paths','executable',_path_str(path))
                except (OSError, ValueError, TypeError): pass


def _parse_steam_vdf_paths(vdf: Path) -> list[Path]:
    try: text=vdf.read_text(encoding='utf-8-sig',errors='replace')
    except OSError: return []
    paths=[]
    for match in re.finditer(r'"path"\s+"((?:[^"\\]|\\.)*)"',text,re.IGNORECASE):
        raw=match.group(1).replace('\\\\','\\')
        if raw: paths.append(Path(raw))
    # Legacy vdf: "1" "D:\\SteamLibrary" (when no nested path field).
    if not paths:
        for m in re.finditer(r'^\s*"\d+"\s+"([A-Za-z]:[^"\n]+)"',text,re.MULTILINE):
            paths.append(Path(m.group(1).replace('\\\\','\\')))
    return paths[:30]


def _steam_roots() -> list[Path]:
    roots=[]
    pf86 = _env_path('ProgramFiles(x86)')
    if pf86: roots.append(pf86/'Steam')
    pf = _env_path('ProgramFiles')
    if pf: roots.append(pf/'Steam')
    if sys.platform == 'win32':
        try:
            import winreg
            for hive, keyname in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                                  (winreg.HKEY_LOCAL_MACHINE, r'Software\Valve\Steam'),
                                  (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Valve\Steam')):
                try:
                    with winreg.OpenKey(hive, keyname) as k:
                        for name in ('SteamPath', 'SteamExe', 'InstallPath'):
                            try:
                                val=winreg.QueryValueEx(k, name)[0]
                                folder=Path(os.path.expandvars(str(val).strip('"')))
                                roots.append(folder.parent if folder.suffix.lower()=='.exe' else folder)
                            except OSError:
                                pass
                except OSError:
                    pass
        except ImportError:
            pass
    return list(dict.fromkeys(p for p in roots if p.is_dir()))


def _steam_executable() -> Path | None:
    """Find an installed Steam client, including non-default directories."""
    for root in _steam_roots():
        exe = root / 'steam.exe'
        if exe.is_file():
            return exe
    return None


def _scan_steam():
    steamapps=[]
    for root in _steam_roots():
        steamapps.append(root/'steamapps')
        for library in _parse_steam_vdf_paths(root/'steamapps'/'libraryfolders.vdf'):
            steamapps.append(library/'steamapps')
    seen=set()
    for apps in steamapps:
        if not apps.is_dir() or _path_str(apps) in seen: continue
        seen.add(_path_str(apps))
        for manifest in list(apps.glob('appmanifest_*.acf'))[:800]:
            try:
                raw=manifest.read_text(encoding='utf-8-sig', errors='replace')
                name=re.search(r'"name"\s+"([^"]{2,180})"',raw,re.I)
                appid=re.search(r'"appid"\s+"(\d{1,15})"',raw,re.I)
                if name and appid:
                    yield CatalogEntry(name.group(1),'game','Steam — zainstalowana gra',
                                       'steam',appid.group(1))
            except OSError: pass



def _scan_riot_league(home: Path):
    """Find the real League install, not an arbitrary LOL-looking executable.

    Riot is neither a Steam nor an Epic library. Prefer a Windows shortcut,
    which automatically accommodates Riot launcher updates and a custom path.
    Otherwise locate the actual League client in a bounded set of known roots.
    No shell commands, downloads or full-disk scans are involved.
    """
    from capri_league import is_league_name

    for item in _scan_shortcuts(home):
        if is_league_name(item.name) or normalize(item.name) in ('league of legends', 'league client'):
            yield CatalogEntry('League of Legends', 'game', 'Riot Games / skrót',
                               'shortcut', item.value)
            return  # Avoid duplicate matches for the same installed game.

    candidates = []
    # The game's supported default path, but do not require C:.
    for letter in 'CDEFGHIJKL':
        candidates.append(Path(f'{letter}:/Riot Games'))
    for key in ('ProgramFiles', 'ProgramFiles(x86)'):
        value = _env_path(key)
        if value:
            candidates.append(value/'Riot Games')
    # Riot installation records contain paths but no executable contents.
    if sys.platform == 'win32':
        try:
            import winreg
            keys = (
                r'Software\Microsoft\Windows\CurrentVersion\Uninstall\League of Legends',
                r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\League of Legends',
            )
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for key_name in keys:
                    try:
                        with winreg.OpenKey(hive, key_name) as key:
                            value = str(winreg.QueryValueEx(key, 'InstallLocation')[0]).strip(' "')
                        if value:
                            candidates.append(Path(value).parent)
                    except (OSError, ValueError, TypeError):
                        pass
        except ImportError:
            pass

    seen = set()
    for root in candidates:
        root = root.resolve(strict=False)
        if str(root).casefold() in seen:
            continue
        seen.add(str(root).casefold())
        if root.name.casefold() == 'league of legends':
            league_client = root/'LeagueClient.exe'
            riot_dir = root.parent/'Riot Client'
        else:
            league_client = root/'League of Legends'/'LeagueClient.exe'
            riot_dir = root/'Riot Client'
        if not league_client.is_file():
            continue
        riot = riot_dir/'RiotClientServices.exe'
        if riot.is_file():
            yield CatalogEntry('League of Legends', 'game', 'Riot Games',
                               'riot_league', str(riot))
        else:
            yield CatalogEntry('League of Legends', 'game', 'Riot Games',
                               'executable', str(league_client))
        return

def _scan_epic():
    data = _env_path('PROGRAMDATA') or Path('C:/ProgramData')
    root = data/'Epic'/'EpicGamesLauncher'/'Data'/'Manifests'
    if not root.is_dir(): return
    for item in list(root.glob('*.item'))[:500]:
        try:
            data=json.loads(item.read_text(encoding='utf-8-sig',errors='replace'))
            if not isinstance(data,dict) or data.get('bIsIncompleteInstall'): continue
            name=data.get('DisplayName')
            base=Path(data.get('InstallLocation',''))
            rel=Path(data.get('LaunchExecutable',''))
            if (not isinstance(name,str) or not name.strip() or not base.is_dir() or
                rel.is_absolute() or '..' in rel.parts or not rel.name): continue
            target=(base/rel).resolve(strict=True)
            if target.suffix.lower()=='.exe' and target.is_file() and base.resolve() in target.parents:
                yield CatalogEntry(name,'game','Epic Games — zainstalowana gra',
                                   'executable',str(target))
        except (OSError,ValueError,TypeError,RuntimeError): continue


_START_APPS_CACHE: tuple[float, list[CatalogEntry]] = (0, [])

def _scan_start_apps():
    """Windows UWP/Store apps through built-in Get-StartApps, with a bounded timeout."""
    global _START_APPS_CACHE
    if sys.platform!='win32': return
    if time.monotonic() - _START_APPS_CACHE[0] < 120:
        yield from _START_APPS_CACHE[1]
        return
    try:
        completed=subprocess.run(
            ['powershell.exe','-NoProfile','-NonInteractive','-Command',
             '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress'],
            shell=False,capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if completed.returncode: return
        items=json.loads(completed.stdout.decode('utf-8-sig',errors='replace'))
        if isinstance(items,dict): items=[items]
        if not isinstance(items,list): return
        results=[]
        for item in items[:1500]:
            if not isinstance(item,dict): continue
            name=item.get('Name'); appid=item.get('AppID')
            if isinstance(name,str) and isinstance(appid,str) and 2<=len(name)<=180 and 2<=len(appid)<=500:
                results.append(CatalogEntry(name,'program','Aplikacja Windows / Microsoft Store','uwp',appid))
        _START_APPS_CACHE=(time.monotonic(),results)
        yield from results
    except (OSError,ValueError,subprocess.TimeoutExpired,TypeError): return


FOLDER_ALIASES = {
    'desktop': 'Desktop','pulpit':'Desktop','documents':'Documents','dokumenty':'Documents',
    'downloads':'Downloads','pobrane':'Downloads','zdjecia':'Pictures','zdjęcia':'Pictures',
    'pictures':'Pictures','obrazy':'Pictures','muzyka':'Music','music':'Music',
    'wideo':'Videos','filmy':'Videos','videos':'Videos',
}


def _fixed_drives():
    if sys.platform!='win32': return []
    try:
        import ctypes
        mask=int(ctypes.windll.kernel32.GetLogicalDrives())
        result=[]
        for i in range(26):
            if not mask & (1 << i): continue
            root=Path(chr(65+i)+':/')
            if ctypes.windll.kernel32.GetDriveTypeW(str(root))==3:
                result.append(root)
        return result
    except (AttributeError,OSError): return []


def _drive_folders(path_allowed):
    """Only top 2 levels of fixed drives. Avoid scanning system folders and the full disk."""
    ignored={'windows','program files','program files (x86)','programdata',
             'users','recovery','system volume information','$recycle.bin',
             'appdata','node_modules','.git'}
    count=0
    for drive in _fixed_drives():
        try:
            top=sorted((p for p in drive.iterdir() if p.is_dir() and p.name.casefold() not in ignored),
                       key=lambda p:p.name.casefold())[:100]
        except (OSError,PermissionError): continue
        for folder in top:
            if folder.is_symlink() or (path_allowed is not None and not path_allowed(folder)):
                continue
            count+=1
            if count>650: return
            yield CatalogEntry(folder.name,'folder','Folder na dysku','folder',_path_str(folder))
            try:
                children=sorted((p for p in folder.iterdir() if p.is_dir() and
                                 p.name.casefold() not in ignored and not p.is_symlink()),
                                 key=lambda p:p.name.casefold())[:75]
            except (OSError,PermissionError): continue
            for child in children:
                if path_allowed is not None and not path_allowed(child): continue
                count+=1
                if count>650: return
                yield CatalogEntry(child.name,'folder','Folder na dysku','folder',_path_str(child))


def _local_folders(home: Path, allowed_roots: list[Path], full_access: bool,
                   path_allowed: Callable[[Path],bool] | None):
    roots=list(dict.fromkeys(Path(x) for x in allowed_roots))
    if full_access:
        roots+= [home/'Desktop',home/'Downloads',home/'Documents',home/'Pictures',
                 home/'Videos',home/'Music']
        onedrive=_env_path('OneDrive')
        if onedrive: roots.extend(onedrive/name for name in ('Desktop','Documents','Pictures'))
        roots.extend(windows_known_folders(home))
    roots=list(dict.fromkeys(p for p in roots if p.is_dir()))
    count=0
    for root in roots:
        if path_allowed is not None and not path_allowed(root): continue
        yield CatalogEntry(root.name,'folder','Folder użytkownika','folder',_path_str(root))
        # Deliberately bounded search: no entire C: traversal.
        for folder, dirs, files in os.walk(root,followlinks=False):
            base=Path(folder)
            depth=len(base.parts)-len(root.parts)
            dirs[:]=sorted(d for d in dirs if not d.startswith('.') and
                           not (base/d).is_symlink())[:70] if depth<3 else []
            for d in dirs:
                child=base/d
                count+=1
                if count>2400: return
                if path_allowed is not None and not path_allowed(child): continue
                yield CatalogEntry(d,'folder','Folder na dysku','folder',_path_str(child))


class LocalCatalog:
    def __init__(self, *, home: Path | str | None = None,
                 roots: list[Path] | None = None, full_access=False,
                 path_allowed: Callable[[Path],bool] | None = None,
                 static_entries: list[CatalogEntry] | None = None):
        self.home=Path(home or Path.home())
        self.roots=roots or []
        self.full_access=bool(full_access)
        self.path_allowed=path_allowed
        self.static_entries=static_entries

    def _collect(self, kind='all') -> list[CatalogEntry]:
        entries=[]
        if self.static_entries is not None:
            entries.extend(self.static_entries)
        elif kind == 'game':
            # Installed-game lookup must be lightweight. Do not run PowerShell
            # Get-StartApps or enumerate Windows shortcuts for a Steam game.
            entries.extend(_scan_steam() or [])
            entries.extend(_scan_epic() or [])
            entries.extend(_scan_riot_league(self.home) or [])
        elif kind in ('all', 'program'):
            entries.extend(_scan_shortcuts(self.home))
            entries.extend(_scan_app_paths() or [])
            entries.extend(_scan_steam() or [])
            entries.extend(_scan_epic() or [])
            entries.extend(_scan_riot_league(self.home) or [])
            entries.extend(_scan_start_apps() or [])
        if kind in ('all','folder') and self.static_entries is None:
            entries.extend(_local_folders(self.home,self.roots,self.full_access,self.path_allowed))
            if self.full_access: entries.extend(_drive_folders(self.path_allowed))
        # Native shortcuts often duplicate UWP / Steam entries, prefer known launcher entries.
        uniques={}
        for e in entries:
            if e.id not in uniques: uniques[e.id]=e
        return list(uniques.values())

    def search(self, query: str, *, kind: str = 'all', source: str = 'all', limit: int = 8) -> dict:
        query=str(query).strip()[:120]
        if len(normalize(query))<2:
            raise ValueError('Podaj przynajmniej 2 znaki nazwy programu, gry lub folderu.')
        if kind not in ('all','program','game','folder'):
            raise ValueError('Nieznany filtr katalogu.')
        if source not in ('all','steam','epic','start','windows'):
            raise ValueError('Nieznany filtr źródła.')
        entries=self._collect(kind)
        match_query = FOLDER_ALIASES.get(normalize(query),query) if kind in ('all','folder') else query
        candidates=[]
        for entry in entries:
            if source!='all' and source not in entry.source.casefold(): continue
            if kind=='folder' and entry.kind!='folder': continue
            if kind=='game' and entry.kind!='game': continue
            if kind=='program' and entry.kind not in ('program','game'): continue
            score=match_score(match_query if entry.kind=='folder' else query,entry.name)
            if score: candidates.append((score,entry))
        # If the name clearly identifies an installed game, a similarly named
        # downloads folder should not trigger a question about choosing a folder.
        if kind == 'all' and source == 'all' and any(score >= 75 and item.kind == 'game'
                                                     for score, item in candidates):
            candidates = [(score, item) for score, item in candidates
                          if item.kind != 'folder']
        priority={'game':0,'program':1,'folder':2}
        candidates.sort(key=lambda x:(-x[0],priority.get(x[1].kind,9),x[1].name.casefold(),x[1].source))
        if source=='all':
            # Start menu and Get-StartApps often list the SAME application.
            # Prefer the classic shortcut without obscuring distinct game installs.
            dedup=[]
            for score,entry in candidates:
                k=normalize(entry.name)
                existing=[(s,e) for s,e in dedup if normalize(e.name)==k]
                if existing and entry.kind=='program' and any(e.kind=='game' for s,e in existing):
                    continue
                if existing and entry.kind=='game':
                    dedup=[(s,e) for s,e in dedup if not (normalize(e.name)==k and e.kind=='program')]
                if entry.kind=='program' and any(e.kind=='program' for s,e in existing):
                    old=next(e for s,e in existing if e.kind=='program')
                    ranks={'shortcut':3,'uwp':2,'executable':1}
                    if ranks.get(entry.launch_type,0)<=ranks.get(old.launch_type,0): continue
                    dedup=[(s,e) for s,e in dedup if e!=old]
                dedup.append((score,entry))
            candidates=dedup
        shown=candidates[:max(1,min(limit,12))]
        ambiguous=(len(shown)>1 and shown[0][0] - shown[1][0] <= 6 and
                   normalize(shown[0][1].name)!=normalize(shown[1][1].name))
        # If the first two exact-name matches are different installed copies,
        # prefer human disambiguation, even though their display names are equal.
        if len(shown)>1 and shown[0][0]==shown[1][0] and shown[0][1].value!=shown[1][1].value:
            ambiguous=True
        return {'query':query,'matches':[e.public(score=s) for s,e in shown],
                'ambiguous':ambiguous,'truncated':len(candidates)>len(shown),
                'help':('Jeśli kilka podobnych wyników, poproś użytkownika o doprecyzowanie.'
                        if ambiguous else 'Uruchom tylko po zatwierdzeniu przez użytkownika.')}

    def by_id(self, item_id: str, *, kind: str = 'all') -> CatalogEntry:
        if not isinstance(item_id,str) or not re.fullmatch(r'[0-9a-f]{20}',item_id):
            raise ValueError('Nieprawidłowe ID znalezionej aplikacji.')
        for entry in self._collect(kind):
            if entry.id == item_id: return entry
        raise FileNotFoundError('Nie znaleziono już tego programu/folderu. Wyszukaj ponownie.')


def launch_entry(entry: CatalogEntry, *, path_allowed=None, platform=None) -> dict:
    platform=platform or sys.platform
    if platform!='win32': raise RuntimeError('Uruchamianie aplikacji wymaga Windows.')
    process_id = None
    if entry.launch_type in ('shortcut','executable'):
        path=Path(entry.value)
        if not path.is_file(): raise FileNotFoundError('Skrót lub plik wykonywalny już nie istnieje.')
        if entry.launch_type=='shortcut' and path.suffix.lower()!='.lnk':
            raise ValueError('Dozwolone są tylko skróty Windows .lnk.')
        if entry.launch_type=='executable' and path.suffix.lower()!='.exe':
            raise ValueError('Dozwolone są tylko pliki .exe.')
        if entry.launch_type=='shortcut':
            os.startfile(str(path))  # noqa: windows-only OS API; shortcut resolves via ShellExecute
        else:
            process_id = subprocess.Popen([str(path)],shell=False,cwd=str(path.parent)).pid
    elif entry.launch_type=='steam':
        if not re.fullmatch(r'\d{1,15}', entry.value):
            raise ValueError('Nieprawidłowe Steam appid.')
        steam = _steam_executable()
        if steam is None:
            raise FileNotFoundError('Nie znaleziono steam.exe. Sprawdź instalację Steam i jego lokalizację.')
        # -applaunch is handled by the actual Steam client, regardless of whether
        # the Windows steam:// URI association is broken or missing.
        try:
            proc = subprocess.Popen([str(steam), '-applaunch', entry.value],
                                    cwd=str(steam.parent), shell=False,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as exc:
            raise RuntimeError('Nie udało się przekazać polecenia do Steam: ' + str(exc)) from exc
        # Creating a launcher process is NOT proof that the game actually started.
        return {'opened':entry.name, 'kind':entry.kind, 'source':entry.source,
                'launch_type':'steam', 'target':entry.value, 'steam_pid':proc.pid,
                'status':'command_sent', 'verified_running':False}
    elif entry.launch_type=='riot_league':
        path = Path(entry.value)
        if path.name.casefold() != 'riotclientservices.exe' or not path.is_file():
            raise FileNotFoundError('Nie znaleziono klienta Riot do uruchomienia League of Legends.')
        # Riot game product identifiers are fixed constants: not LLM-provided
        # arbitrary command arguments. The client handles account login.
        proc = subprocess.Popen([
            str(path), '--launch-product=league_of_legends',
            '--launch-patchline=live'], cwd=str(path.parent), shell=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return {'opened': entry.name, 'kind': entry.kind, 'source': entry.source,
                'launch_type': 'riot_league', 'status': 'command_sent',
                'verified_running': False, 'riot_pid': proc.pid,
                'target': 'Riot Client / league_of_legends'}
    elif entry.launch_type=='uwp':
        if not entry.value or len(entry.value)>500 or any(x in entry.value for x in '\r\n"'):
            raise ValueError('Nieprawidłowe ID aplikacji Windows.')
        # Safe argument passing (no shell). Explorer knows the AppsFolder namespace.
        subprocess.Popen(['explorer.exe',f'shell:AppsFolder\\{entry.value}'],shell=False)
    elif entry.launch_type=='folder':
        path=Path(entry.value)
        if path_allowed is not None and not path_allowed(path):
            raise PermissionError('Folder nie jest objęty przyznanym dostępem.')
        if not path.is_dir(): raise FileNotFoundError('Folder już nie istnieje.')
        subprocess.Popen(['explorer.exe',str(path)],shell=False)
    else:
        raise ValueError('Nieznany sposób uruchamiania.')
    return {'opened':entry.name,'kind':entry.kind,'source':entry.source,
            'launch_type':entry.launch_type, 'status':'command_sent',
            'verified_running':False, 'process_pid': process_id,
            'target':entry.value if entry.launch_type!='shortcut' else 'Skrót z menu Start'}
