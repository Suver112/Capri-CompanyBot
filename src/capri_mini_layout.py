"""Pure, deterministic layout policy for Capri's small desktop companion.

No Qt imports: preview, settings and tests share the same definitions.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MiniGeometry:
    width: int
    height: int
    avatar_width: int
    avatar_height: int
    orientation: str  # 'vertical' or 'horizontal'
    show_bubble: bool
    show_history: bool
    show_wave: bool
    show_label: bool


LAYOUTS = {
    'orb': 'Floating Orb',
    'micro': 'Micro Companion',
    'edge': 'Edge Sprite',
    'portrait': 'Portrait Dock',
    'morph': 'Morph Mini',
}


def normalized_layout(value: str) -> str:
    return value if value in LAYOUTS else 'morph'


def normalized_scale(value: object) -> int:
    """Persisted mini UI scale in logical Qt pixels, clamped for usability."""
    try:
        return max(80, min(150, int(value)))
    except (TypeError, ValueError, OverflowError):
        return 100


def scaled_geometry(geometry: MiniGeometry, scale: int) -> MiniGeometry:
    factor = normalized_scale(scale) / 100.0
    def scaled(n: int) -> int:
        return max(1, round(n * factor))
    return MiniGeometry(
        width=max(140, scaled(geometry.width)),
        height=max(180, scaled(geometry.height)),
        avatar_width=scaled(geometry.avatar_width),
        avatar_height=scaled(geometry.avatar_height),
        orientation=geometry.orientation,
        show_bubble=geometry.show_bubble,
        show_history=geometry.show_history,
        show_wave=geometry.show_wave,
        show_label=geometry.show_label,
    )

def mini_geometry(layout: str, *, speaking: bool = False,
                  chat_open: bool = False, scale: int = 100) -> MiniGeometry:
    """Choose real widget dimensions, not just a scaled full-window layout."""
    layout = normalized_layout(layout)
    def size(*args):
        return scaled_geometry(MiniGeometry(*args), scale)
    if layout == 'morph':
        if chat_open:
            return size(610, 392, 128, 150, 'horizontal', True, True, False, True)
        if speaking:
            return size(362, 226, 124, 144, 'horizontal', True, False, False, True)
        return size(220, 258, 176, 180, 'vertical', False, False, False, False)
    if layout == 'orb':
        if speaking:
            return size(342, 226, 122, 144, 'horizontal', True, False, False, True)
        return size(220, 258, 176, 180, 'vertical', False, False, False, False)
    if layout == 'micro':
        return size(356, 226, 124, 145, 'horizontal', True, False, False, True)
    if layout == 'edge':
        if speaking:
            return size(326, 225, 112, 145, 'horizontal', True, False, False, True)
        return size(145, 247, 112, 146, 'vertical', False, False, False, False)
    return size(268, 399, 214, 222, 'vertical', True, False, True, True)


def mini_excerpt(text: str, max_length: int = 120) -> str:
    """Presentation-only excerpt; never mutate the actual assistant response."""
    text = ' '.join(str(text or '').split())
    if len(text) <= max_length:
        return text
    return text[:max(1, max_length - 1)].rstrip() + '…'


def modern_mini_geometry(layout: str, *, speaking: bool = False,
                         chat_open: bool = False, scale: int = 100) -> MiniGeometry:
    """Unified dimensions for Basic/Holocall/Silverhand.

    Top header, round avatar, optional transcript/history and FOUR icon
    controls fit at all permitted scales; no view-specific widget overrides.
    The proportions are determined before Qt lays out the widgets.
    """
    layout = normalized_layout(layout)
    sizes = {
        # (width, height, avatar width, avatar height, orientation,
        #  show bubble, show history, show wave, show status)
        'morph': {
            'idle': (310, 418, 238, 244, 'vertical', False, False, False, True),
            'speaking': (350, 495, 238, 244, 'vertical', True, False, False, True),
            'chat': (430, 560, 208, 218, 'vertical', False, True, False, True),
        },
        'orb': {
            'idle': (264, 355, 205, 212, 'vertical', False, False, False, True),
            'speaking': (395, 300, 155, 176, 'horizontal', True, False, False, True),
            'chat': (410, 493, 198, 210, 'vertical', False, True, False, True),
        },
        'micro': {
            'idle': (393, 252, 124, 148, 'horizontal', True, False, False, True),
            'speaking': (393, 252, 124, 148, 'horizontal', True, False, False, True),
            'chat': (421, 470, 190, 200, 'vertical', False, True, False, True),
        },
        'edge': {
            'idle': (213, 317, 135, 160, 'vertical', False, False, False, True),
            'speaking': (385, 277, 128, 157, 'horizontal', True, False, False, True),
            'chat': (398, 478, 176, 185, 'vertical', False, True, False, True),
        },
        'portrait': {
            'idle': (308, 508, 232, 240, 'vertical', True, False, True, True),
            'speaking': (308, 508, 232, 240, 'vertical', True, False, True, True),
            'chat': (408, 592, 206, 215, 'vertical', False, True, True, True),
        },
    }
    state = 'chat' if chat_open else 'speaking' if speaking else 'idle'
    return scaled_geometry(MiniGeometry(*sizes[layout][state]), scale)
