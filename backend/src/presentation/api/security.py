from __future__ import annotations

import hmac
import os
from threading import BoundedSemaphore

from fastapi import Header, HTTPException, status


def _setting(name: str) -> str:
    return os.getenv(name, "").strip()


def api_auth_required() -> bool:
    return _setting("INVENTORY_API_AUTH_REQUIRED").lower() in {"1", "true", "yes"}


def allowed_account_ids() -> set[str]:
    return {account_id.strip() for account_id in _setting("INVENTORY_ALLOWED_ACCOUNT_IDS").split(",") if account_id.strip()}


def _matches(provided: str | None, expected: str) -> bool:
    return bool(provided and expected and hmac.compare_digest(provided, expected))


def require_read_access(x_api_key: str | None = Header(default=None)) -> None:
    if not api_auth_required():
        return
    read_key = _setting("INVENTORY_READ_API_KEY")
    write_key = _setting("INVENTORY_WRITE_API_KEY")
    if not read_key or not write_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API authentication is not configured")
    if not (_matches(x_api_key, read_key) or _matches(x_api_key, write_key)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_write_access(x_api_key: str | None = Header(default=None)) -> None:
    if not api_auth_required():
        return
    write_key = _setting("INVENTORY_WRITE_API_KEY")
    if not write_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API authentication is not configured")
    if not _matches(x_api_key, write_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_allowed_accounts(account_ids: list[str]) -> None:
    allowed = allowed_account_ids()
    if not allowed:
        return
    requested = set(account_ids)
    if not requested.issubset(allowed):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="One or more AWS accounts are not allowed")


def _max_concurrent_runs() -> int:
    try:
        return max(1, min(int(_setting("MAX_CONCURRENT_INVENTORY_RUNS") or "2"), 16))
    except ValueError:
        return 2


_inventory_slots = BoundedSemaphore(_max_concurrent_runs())


def acquire_inventory_slot() -> None:
    if not _inventory_slots.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many inventory runs in progress")


def release_inventory_slot() -> None:
    _inventory_slots.release()
