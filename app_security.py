"""Rate limiting, input validation, and safe error handling for the Streamlit app."""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from collections import deque
from typing import Any, Tuple

logger = logging.getLogger("youtube_intel.app")
if not logging.root.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

USER_FACING_ERROR = "Something went wrong. Please try again in a moment."

_MAX_QUERY = int(os.environ.get("APP_MAX_QUERY_CHARS", "500"))
_RATE_PER_MINUTE = int(os.environ.get("APP_LLM_RATE_PER_MINUTE", "5"))
_RATE_PER_HOUR = int(os.environ.get("APP_LLM_RATE_PER_HOUR", "50"))
_MAX_IMAGE_BYTES = int(os.environ.get("APP_MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))


def sanitize_user_query(text: str | None) -> Tuple[str | None, str | None]:
    """Strip dangerous control characters and enforce max length. Returns (value, error_message)."""
    if text is None or not str(text).strip():
        return None, "Please describe your video idea first."
    t = str(text).strip()
    if len(t) > _MAX_QUERY:
        return None, f"Description is too long (max {_MAX_QUERY} characters)."
    out: list[str] = []
    for c in t:
        if c in "\n\t":
            out.append(c)
        elif ord(c) >= 32:
            out.append(c)
    return "".join(out), None


def consume_llm_slot(session_state: Any) -> Tuple[bool, str]:
    """
    Per-browser-session rate limit for Groq calls (sliding windows).
    Tuned via APP_LLM_RATE_PER_MINUTE and APP_LLM_RATE_PER_HOUR.
    """
    now = time.monotonic()
    if "_rl_minute" not in session_state:
        session_state["_rl_minute"] = deque()
    if "_rl_hour" not in session_state:
        session_state["_rl_hour"] = deque()
    minute: deque = session_state["_rl_minute"]
    hour: deque = session_state["_rl_hour"]
    while minute and now - minute[0] > 60.0:
        minute.popleft()
    while hour and now - hour[0] > 3600.0:
        hour.popleft()
    if len(minute) >= _RATE_PER_MINUTE:
        return False, "Too many AI requests per minute. Please wait a moment and try again."
    if len(hour) >= _RATE_PER_HOUR:
        return False, "Hourly AI request limit reached. Please try again later."
    minute.append(now)
    hour.append(now)
    return True, ""


def log_exception(context: str, exc: BaseException) -> None:
    logger.error("%s: %s", context, exc, exc_info=(type(exc), exc, exc.__traceback__))


def validate_image_bytes(raw: bytes) -> Tuple[bool, str | None]:
    """Size check + PIL verify that bytes are a real JPEG/PNG."""
    if len(raw) > _MAX_IMAGE_BYTES:
        mb = _MAX_IMAGE_BYTES // (1024 * 1024)
        return False, f"Image too large (max {mb} MB)."
    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            if im.format not in ("JPEG", "PNG"):
                return False, "Image must be JPEG or PNG."
    except Exception:
        return False, "Could not read image. Use a valid JPEG or PNG file."
    return True, None


def image_bytes_to_data_url(raw: bytes) -> str:
    """Build a data URL with the correct MIME type for the Groq vision API."""
    from PIL import Image

    with Image.open(io.BytesIO(raw)) as im:
        fmt = (im.format or "JPEG").upper()
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"
