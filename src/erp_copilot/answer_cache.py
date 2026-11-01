
import re
import threading
import time

TTL_SECONDS = 3600
MAX_ENTRIES = 200

_lock = threading.Lock()
_store: dict[str, tuple[float, dict]] = {}


def _key(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def get(question: str, now: float | None = None) -> dict | None:
    now = time.time() if now is None else now
    key = _key(question)
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        stored_at, answer = entry
        if now - stored_at > TTL_SECONDS:
            del _store[key]
            return None
        return dict(answer)  # a copy, so callers cannot change the cached one


def put(question: str, answer: dict, now: float | None = None) -> None:
    now = time.time() if now is None else now
    with _lock:
        _store[_key(question)] = (now, dict(answer))
        while len(_store) > MAX_ENTRIES:
            oldest = min(_store, key=lambda k: _store[k][0])
            del _store[oldest]


def clear() -> None:
    with _lock:
        _store.clear()