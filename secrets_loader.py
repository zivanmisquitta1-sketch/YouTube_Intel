"""Load secrets from environment variables first, then optional credentials.py (local dev)."""

from __future__ import annotations

import os
from typing import Optional


def _env(name: str) -> Optional[str]:
    v = os.environ.get(name)
    if v is not None and str(v).strip():
        return str(v).strip()
    # Streamlit Cloud (and local `streamlit run`) expose secrets via st.secrets, not os.environ
    try:
        import streamlit as st

        if hasattr(st, "secrets") and name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return None


def _from_credentials(attr: str) -> Optional[str]:
    try:
        import credentials
    except ImportError:
        return None
    if not hasattr(credentials, attr):
        return None
    val = getattr(credentials, attr)
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    return val.strip() if isinstance(val, str) else str(val)


def _require(env_name: str, cred_attr: str) -> str:
    v = _env(env_name)
    if v is not None:
        return v
    v = _from_credentials(cred_attr)
    if v is not None:
        return v
    raise RuntimeError(
        f"Missing {env_name}. Set the environment variable or add {cred_attr} to credentials.py."
    )


def get_mongo_connection_string() -> str:
    return _require("MONGO_CONNECTION_STRING", "MONGO_CONNECTION_STRING")


def get_youtube_api_key() -> str:
    return _require("YOUTUBE_API_KEY", "YOUTUBE_API_KEY")


def get_groq_api_key() -> str:
    return _require("GROQ_API_KEY", "GROQ_API_KEY")


def get_openai_api_key() -> str:
    return _require("OPENAI_API_KEY", "OPENAI_API_KEY")


def get_gemini_api_key() -> str:
    return _require("GEMINI_API_KEY", "GEMINI_API_KEY")
