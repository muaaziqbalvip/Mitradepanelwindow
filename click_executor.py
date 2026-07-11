"""
click_executor.py — Performs a real mouse click at a dot's position.
"""

import pyautogui

pyautogui.FAILSAFE = False  # don't abort if mouse hits a screen corner


def click_dot(dot: dict):
    """Moves the mouse to the dot's center and performs a real left-click."""
    half = dot.get("size", 48) // 2
    x = dot["x"] + half
    y = dot["y"] + half
    pyautogui.moveTo(x, y, duration=0.08)
    pyautogui.click(x, y)
