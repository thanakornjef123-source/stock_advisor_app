# -*- coding: utf-8 -*-
"""
Local persistence.

Streamlit keeps everything in session state, which is wiped on refresh. The
watchlist, saved screens and portfolio holdings are things a user builds up over
time, so they are written to a JSON file next to the application instead.

Single-user, single-machine, no accounts — appropriate for a locally run tool.
"""
import json
import os
import threading
from datetime import datetime

import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(BASE, "user_data.json")
_LOCK = threading.Lock()


def _shared_deployment() -> bool:
    """
    True when the app is serving more than one person.

    Writing to a single file is right for a tool running on your own machine.
    On a hosted deployment every visitor shares that file, so one person's
    holdings would show up in everyone else's session. In that case persistence
    is switched off and state stays in the browser session only.

    Set SET_TERMINAL_PERSIST=1 to force saving on, or 0 to force it off.
    """
    override = os.environ.get("SET_TERMINAL_PERSIST")
    if override is not None:
        return override.strip() not in ("1", "true", "True", "yes")
    if BASE.startswith("/mount/src"):                        # Streamlit Cloud
        return True
    if os.environ.get("STREAMLIT_SHARING_MODE"):
        return True
    if os.environ.get("SPACE_ID") or os.environ.get("DYNO"):  # Spaces, Heroku
        return True
    return False


SHARED = _shared_deployment()

DEFAULT = {"watchlist": [], "holdings": [], "saved_screens": {}, "result": None}


def _read() -> dict:
    if SHARED or not os.path.exists(PATH):
        return json.loads(json.dumps(DEFAULT))
    try:
        with open(PATH, encoding="utf-8") as fh:
            d = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(DEFAULT))
    for k, v in DEFAULT.items():
        d.setdefault(k, v)
    return d


def _write(d: dict) -> None:
    """Write via a temporary file so a crash never leaves a truncated store."""
    if SHARED:
        return                     # never write a shared file on a hosted app
    with _LOCK:
        tmp = PATH + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=1, default=str)
            os.replace(tmp, PATH)
        except OSError:
            pass                      # a read-only folder must not break the app


def load_into_session() -> None:
    """Called once per session to restore whatever was saved last time."""
    if st.session_state.get("_store_loaded"):
        return
    d = _read()
    st.session_state.setdefault("watchlist", list(d["watchlist"]))
    st.session_state.setdefault("holdings", list(d["holdings"]))
    st.session_state.setdefault("saved_screens", dict(d["saved_screens"]))
    if d.get("result") and "result" not in st.session_state:
        st.session_state["result"] = d["result"]
    st.session_state["_store_loaded"] = True


def save() -> None:
    """Persist the parts of session state worth keeping."""
    _write({
        "watchlist": st.session_state.get("watchlist", []),
        "holdings": st.session_state.get("holdings", []),
        "saved_screens": st.session_state.get("saved_screens", {}),
        "result": st.session_state.get("result"),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    })


def clear() -> None:
    _write(json.loads(json.dumps(DEFAULT)))
    for k in ("watchlist", "holdings", "saved_screens", "result"):
        st.session_state.pop(k, None)
    st.session_state["_store_loaded"] = False


def where() -> str:
    return "this browser session only" if SHARED else PATH


def status_note() -> str:
    if SHARED:
        return ("Shared deployment: your watchlist and holdings stay in this "
                "browser session and are not written to the server, so they "
                "clear when you close the tab.")
    return f"Saved on this machine at {PATH} — your positions survive a refresh."
