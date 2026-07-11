"""
storage.py — Persistent settings & dots storage for AI Touch Desktop.

Mirrors the Android app's AppStore: keeps the backend URL, Groq key, PIN,
saved instruction prompt, and the list of user-placed "touching dots" in a
simple JSON file in the user's home directory.
"""

import json
import os
import uuid

APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".ai_touch_desktop")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")

DEFAULT_BACKEND_URL = "https://muaaznamtosonahoga1-miaitoch.hf.space/analyze"

_DEFAULTS = {
    "backend_url": DEFAULT_BACKEND_URL,
    "groq_key": "",
    "pin": "",
    "pin_verified": False,
    "prompt": "",
    "dots": [],  # list of {id, name, x, y, size, locked}
}


def _ensure_dir():
    os.makedirs(APP_DATA_DIR, exist_ok=True)


def load_settings() -> dict:
    _ensure_dir()
    if not os.path.exists(SETTINGS_FILE):
        return dict(_DEFAULTS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    except Exception:
        return dict(_DEFAULTS)


def save_settings(settings: dict):
    _ensure_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def new_dot(name: str, x: int, y: int, size: int = 48) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": name[:2] if name else "?",
        "x": x,
        "y": y,
        "size": size,
        "locked": False,
    }
