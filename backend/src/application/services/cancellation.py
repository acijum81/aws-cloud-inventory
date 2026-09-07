from __future__ import annotations

from threading import Lock


class CancellationRegistry:
    def __init__(self) -> None:
        self._cancelled: set[str] = set()
        self._lock = Lock()

    def cancel(self, run_id: str) -> None:
        with self._lock:
            self._cancelled.add(run_id)

    def is_cancelled(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._cancelled

    def clear(self, run_id: str) -> None:
        with self._lock:
            self._cancelled.discard(run_id)


cancellation_registry = CancellationRegistry()
