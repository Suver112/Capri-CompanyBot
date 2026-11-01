"""Original Windows window-perch coordinates for Capri's existing mini overlay.

No hooks, no screenshots, no manipulation of other windows. Uses only the
foreground window rectangle, and runs solely when user explicitly enables it.
"""
from __future__ import annotations
from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class TargetWindow:
    handle: int
    left: int
    top: int
    right: int
    bottom: int


def active_window(own_handle: int = 0) -> TargetWindow | None:
    if sys.platform != 'win32':
        return None
    import ctypes
    from ctypes import wintypes
    user = ctypes.windll.user32
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsIconic.argtypes = [wintypes.HWND]
    handle = user.GetForegroundWindow()
    if not handle or handle == own_handle or not user.IsWindowVisible(handle) or user.IsIconic(handle):
        return None
    rect = wintypes.RECT()
    if not user.GetWindowRect(handle, ctypes.byref(rect)):
        return None
    candidate = TargetWindow(int(handle), rect.left, rect.top, rect.right, rect.bottom)
    if candidate.right - candidate.left < 300 or candidate.bottom - candidate.top < 180:
        return None
    return candidate


def perch_position(target: TargetWindow, overlay_width: int, overlay_height: int,
                   screen: tuple[int, int, int, int]) -> tuple[int, int]:
    """Place avatar near target window's upper-right, clamped to visible work area."""
    left, top, right, bottom = screen
    x = target.right - overlay_width - min(100, (target.right-target.left)//5)
    y = target.top - max(0, overlay_height - 20)
    if y < top:  # Maximized windows: hover at the top, never disappear above screen.
        y = target.top + 10
    return (max(left, min(right-overlay_width, x)),
            max(top, min(bottom-overlay_height, y)))


def cursor_position() -> tuple[int, int] | None:
    if sys.platform != 'win32':
        return None
    import ctypes
    from ctypes import wintypes
    point = wintypes.POINT()
    return (point.x, point.y) if ctypes.windll.user32.GetCursorPos(ctypes.byref(point)) else None
