"""In-memory log hub for real-time pipeline log streaming (SSE).

Captures stdout (print + logging handler output) during pipeline stage
execution and fans each line out to every active SSE subscriber, with a
bounded ring buffer for late-joining clients.
"""
from __future__ import annotations

import asyncio
import sys
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Set

MAX_LINES = 500


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LogHub:
    """Thread-safe-ish broadcaster of pipeline log lines."""

    def __init__(self, max_lines: int = MAX_LINES):
        self._lines: Deque[dict] = deque(maxlen=max_lines)
        self._subscribers: Set[asyncio.Queue] = set()

    def emit(self, level: str, message: str) -> None:
        line = {"ts": _stamp(), "level": level.upper(), "message": message}
        self._lines.append(line)
        for q in list(self._subscribers):
            try:
                q.put_nowait(line)
            except Exception:
                pass

    def history(self, limit: int = MAX_LINES) -> list[dict]:
        return list(self._lines)[-limit:]

    async def subscribe(self):
        """Async generator yielding historical + live log lines."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        try:
            for line in self._lines:
                yield line
            while True:
                yield await q.get()
        finally:
            self._subscribers.discard(q)

    def clear(self) -> None:
        self._lines.clear()


hub = LogHub()


class _Tee:
    """Redirect writes to both the real stdout and the LogHub."""

    def __init__(self, real):
        self._real = real

    def write(self, s: str) -> int:
        stripped = s.rstrip("\n")
        if stripped.strip():
            hub.emit("INFO", stripped)
        try:
            return self._real.write(s)
        except ValueError:
            return len(s)

    def flush(self) -> None:
        try:
            self._real.flush()
        except ValueError:
            pass

    def isatty(self) -> bool:
        return False

    @property
    def encoding(self) -> str:
        return getattr(self._real, "encoding", "utf-8")


class StdoutTee:
    """Context manager temporarily redirecting sys.stdout to the log hub."""

    def __enter__(self):
        self._orig = sys.stdout
        sys.stdout = _Tee(self._orig)
        return sys.stdout

    def __exit__(self, *exc):
        sys.stdout.flush()
        sys.stdout = self._orig
        return False