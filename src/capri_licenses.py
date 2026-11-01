"""Third-party license disclosures and *optional* local Fish S2-Pro consent.

There is intentionally NO blanket first-run EULA. License texts are vendor-owned,
not a license for Capri itself. A model consent is scoped to the selected model.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from capri_paths import local_root

FISH_RESEARCH_ID = 'fish-s2-pro-research-2026-03-07'
FISH_RESEARCH_URL = 'https://huggingface.co/fishaudio/s2-pro/raw/main/LICENSE.md'
FISH_RESEARCH_PAGE = 'https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md'
FISH_COMMUNITY_URL = 'https://github.com/fishaudio/fish-speech/blob/main/LICENSE'
FISH_COMMUNITY_RAW = 'https://raw.githubusercontent.com/fishaudio/fish-speech/main/LICENSE'
NOTICE_FILES = (('Fish Speech — Community License', FISH_COMMUNITY_RAW, FISH_COMMUNITY_URL),
                ('Fish S2-Pro — Research License', FISH_RESEARCH_URL, FISH_RESEARCH_PAGE),
                ('Licencje pozostałych komponentów / Other components', '', ''))


def consent_file() -> Path:
    return local_root() / 'licenses' / 'accepted.json'


def has_fish_research_acceptance(path: Path | None = None) -> bool:
    target = path or consent_file()
    try:
        item = json.loads(target.read_text(encoding='utf-8'))
        record = item.get('fish_s2_pro_research', {})
        return record.get('id') == FISH_RESEARCH_ID and record.get('accepted') is True
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def record_fish_research_acceptance(path: Path | None = None) -> None:
    target = path or consent_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = {}
    try:
        old = json.loads(target.read_text(encoding='utf-8'))
        if isinstance(old, dict):
            previous.update(old)
    except (OSError, ValueError, TypeError):
        pass
    previous['fish_s2_pro_research'] = {
        'id': FISH_RESEARCH_ID,
        'accepted': True,
        'at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'source': FISH_RESEARCH_PAGE,
    }
    payload = json.dumps(previous, indent=2, ensure_ascii=False)
    fd, temp = tempfile.mkstemp(dir=str(target.parent), prefix='license.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(payload)
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def fetch_vendor_license(url: str, cache_file: Path, *, timeout: int = 8) -> str:
    """Retrieve exact upstream text; never synthesize or silently alter license terms."""
    if url not in (FISH_RESEARCH_URL, FISH_COMMUNITY_RAW):
        raise ValueError('Unrecognized license source')
    try:
        req = Request(url, headers={'User-Agent': 'CapriOverlay-LicenseViewer/1.0'})
        with urlopen(req, timeout=timeout) as response:
            blob = response.read(160001)
        if not 250 <= len(blob) <= 160000:
            raise ValueError('Incomplete or unexpectedly large license')
        result = blob.decode('utf-8-sig')
        if url == FISH_RESEARCH_URL and 'FISH AUDIO RESEARCH LICENSE AGREEMENT' not in result[:250]:
            raise ValueError('Wrong research license document')
        if url == FISH_COMMUNITY_RAW and 'FISH AUDIO COMMUNITY LICENSE AGREEMENT' not in result[:250]:
            raise ValueError('Wrong community license document')
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(result, encoding='utf-8')
        return result
    except (OSError, ValueError, UnicodeError):
        if cache_file.is_file():
            cached = cache_file.read_text(encoding='utf-8')
            if ('FISH AUDIO RESEARCH LICENSE AGREEMENT' if url == FISH_RESEARCH_URL else
                    'FISH AUDIO COMMUNITY LICENSE AGREEMENT') in cached[:250]:
                return cached
        raise


def should_confirm_for_engine(engine: str, *, receipt: Path | None = None) -> bool:
    """Cloud API, Windows TTS, Piper and non-Fish engines need no popup."""
    return engine == 's2cpp' and not has_fish_research_acceptance(receipt)
