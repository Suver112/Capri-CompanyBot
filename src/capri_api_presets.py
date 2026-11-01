"""Small, vendor-verified API provider presets for Capri's setup screen.

No secrets, imports of Qt, network traffic or local model downloads.
Models are editable, because provider availability/pricing changes over time.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    code: str
    label: str
    endpoint: str
    models: tuple[str, ...]
    help: str


PROVIDERS = (
    Provider('nvidia', 'NVIDIA API Catalog',
             'https://integrate.api.nvidia.com/v1/chat/completions',
             ('openai/gpt-oss-20b',),
             'Klucz z build.nvidia.com. Limity i dostępność zależą od konta.'),
    Provider('deepseek', 'DeepSeek API',
             'https://api.deepseek.com/chat/completions',
             ('deepseek-flash', 'deepseek-v4-pro'),
             'Płatność wg cennika DeepSeek; sprawdź model i środki.'),
    Provider('openai', 'OpenAI API',
             'https://api.openai.com/v1/chat/completions',
             ('gpt-6-luna', 'gpt-6.1-terra'),
             'Klucz z platform.openai.com; osobne płatności API.'),
    Provider('anthropic', 'Anthropic Claude API',
             'https://api.anthropic.com/v1/messages',
             ('claude-haiku-5-5',),
             'Bezpośredni Anthropic Messages API; wymaga klucza Anthropic.'),
    Provider('openrouter', 'OpenRouter',
             'https://openrouter.ai/api/v1/chat/completions',
             ('openai/gpt-4o-mini',),
             'Wybierz dostępny model z katalogu OpenRouter.'),
    Provider('custom', 'Własny endpoint (OpenAI-compatible)',
             '', (),
             'Wpisz pełny endpoint Chat Completions HTTPS lub localhost HTTP.'),
)

BY_CODE = {p.code: p for p in PROVIDERS}


def provider(code: str) -> Provider:
    return BY_CODE.get(code, BY_CODE['custom'])


def default_model(code: str) -> str:
    values = provider(code).models
    return values[0] if values else ''


def credential_kind(code: str) -> str:
    return 'chat:' + provider(code).code
