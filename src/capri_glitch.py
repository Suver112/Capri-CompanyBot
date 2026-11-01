"""Small, frame-stable chromatic glitch fragments for Capri's anger visuals.

Pure geometry/color calculations live here so tests need no GUI runtime.
The painter and optional out-of-window transparent Qt layer are in main.py.
"""
from __future__ import annotations

from dataclasses import dataclass
import random

# RGBA: saturated red, electric blue, off-white, near-black.
PALETTE = {
    "red": (255, 30, 44),
    "blue": (40, 127, 255),
    "white": (242, 248, 255),
    "black": (2, 4, 10),
}

THEME_PALETTES = {
    'capri': PALETTE,
    'holocall': {'red': (255, 76, 130), 'blue': (42, 225, 220),
                 'white': (235, 255, 251), 'black': (12, 24, 31)},
    'silverhand': {'red': (213, 230, 95), 'blue': (93, 149, 234),
                   'white': (244, 248, 200), 'black': (11, 20, 32)},
}


def theme_palette(theme: str) -> dict:
    return THEME_PALETTES.get(theme, PALETTE)


@dataclass(frozen=True)
class GlitchStrip:
    x: int
    y: int
    width: int
    height: int
    r: int
    g: int
    b: int
    alpha: int


def _palette(rng: random.Random) -> list[str]:
    """Most frames have only one/two colors, never a mandatory four-color loop."""
    number = rng.choices([1, 2, 3, 4], weights=[28, 48, 21, 3])[0]
    colors = ["red", "blue", "white", "black"]
    weights = [5, 3, 2, 2]
    picked = []
    for _ in range(number):
        chosen = rng.choices(colors, weights=weights)[0]
        picked.append(chosen)
        k = colors.index(chosen)
        colors.pop(k)
        weights.pop(k)
    return picked


def fragments(width: int, height: int, frame: int, intensity: float,
              theme: str = 'capri') -> list[GlitchStrip]:
    """Irregular fragmented streaks, small to medium, within overlay bounds.

    Capped at <44% of overlay width (the old code painted near-full-width bands).
    Reproducible per frame, changing on subsequent frames. No permanent patterns.
    """
    width, height = max(0, int(width)), max(0, int(height))
    intensity = max(0.0, min(1.0, float(intensity)))
    if width < 4 or height < 4 or intensity < .006:
        return []
    rng = random.Random((frame * 73856093) ^ (width * 19349663) ^ (height * 83492791))
    choices = _palette(rng)
    palette = theme_palette(theme)
    count = max(1, round((8 + rng.randint(0, 11)) * intensity))
    max_width = max(7, min(width - 2, 310, round(width * .43)))
    output = []
    for _ in range(count):
        # Most strips are tiny, a few are moderately long.
        extent = rng.random() ** 2.0
        length = min(max_width, max(5, round(5 + (max_width - 5) * extent)))
        length = min(length, width)
        thickness = rng.choices([1, 2, 3, 4, 6, 8, 10], [6, 12, 11, 8, 5, 3, 1])[0]
        thickness = min(thickness, height)
        x = rng.randrange(width - length + 1)
        y = rng.randrange(height - thickness + 1)
        r, g, b = palette[rng.choice(choices)]
        opacity = round(min(255, (95 + rng.randint(0, 105)) * intensity))
        output.append(GlitchStrip(x, y, length, thickness, r, g, b, opacity))
    return output


def edge_fragments(width: int, height: int, frame: int,
                   intensity: float, margin: int = 12,
                   theme: str = 'capri') -> list[GlitchStrip]:
    """Tiny streaks crossing the overlay boundary by at most `margin` pixels.

    Coordinates are relative to the separate Qt transparent surface whose
    top-left is (owner.x - margin, owner.y - margin). The actual UI isn't resized.
    """
    width, height = int(width), int(height)
    intensity = max(0.0, min(1.0, float(intensity)))
    margin = max(1, int(margin))
    if width < 60 or height < 60 or intensity < .09:
        return []
    rng = random.Random((frame * 1000003) ^ (width * 17) ^ (height * 47) ^ 0xA917)
    choices = _palette(rng)
    palette = theme_palette(theme)
    number = rng.randint(0, 3) + (1 if intensity > .55 else 0)
    if rng.random() > intensity:
        number = max(0, number - 1)
    out = []
    for _ in range(number):
        side = rng.choice(('left', 'right', 'top', 'bottom'))
        r, g, b = palette[rng.choice(choices)]
        alpha = round((100 + rng.randint(0, 110)) * intensity)
        if side in ('left', 'right'):
            # Deliberately straddle only a few pixels of the main window.
            wide = rng.randint(6, margin + 5)
            thick = rng.randint(2, 7)
            xx = margin - rng.randint(2, min(margin, 9)) if side == 'left' else margin + width - rng.randint(0, 3)
            yy = margin + rng.randrange(height - thick + 1)
        else:
            wide = rng.randint(9, min(76, width - 1))
            thick = rng.randint(2, margin + 5)
            xx = margin + rng.randrange(width - wide + 1)
            yy = margin - rng.randint(2, min(margin, 9)) if side == 'top' else margin + height - rng.randint(0, 3)
        out.append(GlitchStrip(xx, yy, wide, thick, r, g, b, alpha))
    return out
