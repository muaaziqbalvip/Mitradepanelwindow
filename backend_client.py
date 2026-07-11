"""
backend_client.py — Talks to the SAME HF Space backend the Android app uses.

Sends: screenshot (base64 JPEG) + dots + saved prompt + PIN
Receives: {"dot": "b"} (which dot to click) or {"dot": ""} (do nothing),
          possibly with "_debug_raw" (AI's raw reasoning text) and "error".
"""

import base64
import io
import json

import requests
from PIL import Image


class BackendError(Exception):
    pass


def _image_to_base64_jpeg(image: Image.Image, quality: int = 70) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def verify_pin(backend_url: str, pin: str, timeout: int = 15) -> tuple[bool, str | None]:
    """Returns (valid, error_message_or_None)."""
    base = backend_url.rstrip("/")
    if base.endswith("/analyze"):
        base = base[: -len("/analyze")]
    url = base + "/verify_pin"

    try:
        resp = requests.post(url, json={"pin": pin}, timeout=timeout)
        data = resp.json()
        valid = bool(data.get("valid", False))
        if valid:
            return True, None
        return False, data.get("error", "Galat PIN")
    except Exception as e:
        return False, f"Network error: {e}"


def analyze(
    backend_url: str,
    groq_key: str,
    pin: str,
    dots: list[dict],
    prompt: str,
    screenshot: Image.Image,
    timeout: int = 60,
) -> dict:
    """
    Sends the screenshot + dots + prompt to the backend.
    Returns a dict like {"dot": "b", "_debug_raw": "...", "error": "..."}.
    Raises BackendError on network failure or non-2xx HTTP status.
    """
    payload = {
        "image_base64": _image_to_base64_jpeg(screenshot),
        "dots": [
            {
                "id": d["id"],
                "name": d["name"],
                "x": d["x"],
                "y": d["y"],
                "locked": d.get("locked", False),
            }
            for d in dots
        ],
        "prompt": prompt,
        "groq_key": groq_key,
        "pin": pin,
    }

    try:
        resp = requests.post(backend_url, json=payload, timeout=timeout)
    except requests.RequestException as e:
        raise BackendError(f"Network error: {e}")

    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise BackendError(f"Backend ne invalid response diya (status {resp.status_code})")

    if resp.status_code >= 400:
        raise BackendError(data.get("error", f"Backend error {resp.status_code}"))

    return data


def _base_url(backend_url: str) -> str:
    base = backend_url.rstrip("/")
    if base.endswith("/analyze"):
        base = base[: -len("/analyze")]
    return base


def send_feedback(
    backend_url: str, pin: str, description: str, result: str, dot: str, timeout: int = 15
) -> tuple[bool, str | None]:
    """Reports a trade result ('win' or 'loss') for the last analysis. Returns (success, error)."""
    url = _base_url(backend_url) + "/feedback"
    try:
        resp = requests.post(
            url,
            json={"description": description, "result": result, "dot": dot, "pin": pin},
            timeout=timeout,
        )
        if resp.status_code >= 400:
            data = resp.json()
            return False, data.get("error", f"Error {resp.status_code}")
        return True, None
    except Exception as e:
        return False, f"Network error: {e}"


def fetch_stats(backend_url: str, timeout: int = 15) -> dict:
    """Returns {"wins": int, "losses": int, "total": int, "win_rate_percent": float}."""
    url = _base_url(backend_url) + "/feedback/stats"
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.json()
    except Exception:
        return {"wins": 0, "losses": 0, "total": 0, "win_rate_percent": 0.0}
