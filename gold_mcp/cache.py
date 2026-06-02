"""TTL filesystem cache to amortize Yahoo Finance calls.

Stores normalized JSON only — never raw vendor payloads. Nothing on
disk lasts longer than its TTL.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path


def _cache_dir() -> Path:
    raw = os.environ.get("GOLD_MCP_CACHE_DIR", "").strip()
    if raw:
        d = Path(raw).expanduser()
    else:
        d = Path.home() / ".cache" / "gold-mcp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _disabled() -> bool:
    return os.environ.get("GOLD_MCP_CACHE_DISABLED", "") == "1"


def _key(namespace: str, args: tuple, kwargs: dict) -> str:
    payload = json.dumps([namespace, list(args), kwargs], sort_keys=True, default=str)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{namespace}_{h}.json"


def cached(namespace: str, ttl_seconds: int):
    """TTL-cache a function returning a JSON-serializable dict."""
    def deco(fn: Callable[..., dict]) -> Callable[..., dict]:
        def wrapper(*args, **kwargs) -> dict:
            if _disabled():
                return fn(*args, **kwargs)
            path = _cache_dir() / _key(namespace, args, kwargs)
            now = time.time()
            if path.exists():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    if now - raw.get("_cached_at", 0) < ttl_seconds:
                        out = raw.get("value")
                        if isinstance(out, dict):
                            out["_from_cache"] = True
                            return out
                except (json.JSONDecodeError, OSError):
                    pass
            result = fn(*args, **kwargs)
            if isinstance(result, dict) and "error" not in result:
                try:
                    path.write_text(
                        json.dumps({"_cached_at": now, "value": result}, default=str),
                        encoding="utf-8",
                    )
                except OSError:
                    pass
            return result
        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco


def purge_expired() -> dict:
    d = _cache_dir()
    removed = 0
    kept = 0
    now = time.time()
    for f in d.glob("*.json"):
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            age = now - raw.get("_cached_at", 0)
            if age > 86_400:
                f.unlink()
                removed += 1
            else:
                kept += 1
        except (json.JSONDecodeError, OSError):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
    return {"cache_dir": str(d), "removed": removed, "kept": kept}
