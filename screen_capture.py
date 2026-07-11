"""
screen_capture.py — Fast full-screen (or primary monitor) screenshot capture.
"""

import mss
from PIL import Image


def capture_primary_monitor() -> Image.Image:
    """Captures the primary monitor and returns a PIL Image."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # index 0 is "all monitors combined"; 1 is primary
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return img
