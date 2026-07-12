"""
click_executor.py — Performs a REAL mouse click at a dot's position.

Uses raw Windows SendInput (via ctypes) instead of pyautogui's click, with
proper physical-style timing (move -> settle -> button down -> hold ->
button up). This matters because many browser-based trading platforms
(Chrome/Edge) silently ignore or block purely synthetic clicks that arrive
too fast or via higher-level automation APIs — a real mouse click has a
brief down/up gap that this replicates.

Falls back to pyautogui if the low-level approach isn't available for any
reason (e.g. running on a non-Windows OS during development/testing).
"""

import platform
import time

_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    import ctypes

    # --- Windows SendInput setup (mouse_event-equivalent, but modern) ---
    PUL = ctypes.POINTER(ctypes.c_ulong)

    class MouseInput(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", PUL),
        ]

    class Input_I(ctypes.Union):
        _fields_ = [("mi", MouseInput)]

    class Input(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

    INPUT_MOUSE = 0
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_ABSOLUTE = 0x8000

    def _send_input(*inputs):
        n = len(inputs)
        arr = (Input * n)(*inputs)
        ctypes.windll.user32.SendInput(n, ctypes.pointer(arr), ctypes.sizeof(Input))

    def _screen_size():
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    def _move_cursor_to(x: int, y: int):
        # SetCursorPos is more reliable than SendInput-based absolute moves
        # for actually repositioning the visible cursor before clicking.
        ctypes.windll.user32.SetCursorPos(int(x), int(y))

    def _mouse_down():
        inp = Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)))
        _send_input(inp)

    def _mouse_up():
        inp = Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)))
        _send_input(inp)

    def _real_click(x: int, y: int):
        """
        Moves the actual OS cursor to (x, y), then sends a proper button
        down -> short hold -> button up sequence via SendInput. This is
        much closer to a genuine hardware click than a single synthetic
        'click' event, and is what browser-based sites are far less likely
        to filter out.
        """
        _move_cursor_to(x, y)
        time.sleep(0.05)  # let the cursor position settle before pressing
        _mouse_down()
        time.sleep(0.07)  # brief hold, like a real physical click
        _mouse_up()

else:
    def _real_click(x: int, y: int):
        raise RuntimeError("Low-level click only implemented for Windows")


def click_dot(dot: dict):
    """Moves the mouse to the dot's center and performs a real left-click."""
    half = dot.get("size", 48) // 2
    x = int(dot["x"] + half)
    y = int(dot["y"] + half)

    if _IS_WINDOWS:
        try:
            _real_click(x, y)
            return
        except Exception:
            pass  # fall through to pyautogui fallback below

    # Fallback (non-Windows, or if the low-level path failed for some reason).
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.moveTo(x, y, duration=0.08)
    time.sleep(0.05)
    pyautogui.mouseDown(x, y)
    time.sleep(0.07)
    pyautogui.mouseUp(x, y)
