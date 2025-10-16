import time
import threading


_lock = threading.Lock()
_last_seen = {}

# Consider a user online if we saw a heartbeat within this many seconds
ONLINE_TTL_SECONDS = 35


def set_online(username: str):
    """Mark a user as online by updating last seen timestamp."""
    if not username:
        return
    now = time.time()
    with _lock:
        _last_seen[username] = now


def is_online(username: str) -> bool:
    """Return True if the user has a recent heartbeat within the TTL."""
    if not username:
        return False
    cutoff = time.time() - ONLINE_TTL_SECONDS
    with _lock:
        ts = _last_seen.get(username)
    return bool(ts and ts >= cutoff)


def online_usernames():
    """Return a set of usernames considered online now (best-effort)."""
    cutoff = time.time() - ONLINE_TTL_SECONDS
    with _lock:
        return {u for u, ts in _last_seen.items() if ts >= cutoff}
