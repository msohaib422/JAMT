"""Tiny TTL file cache for NASA data.

Cached responses are always marked ``cached: true`` by the services layer.
The caller may serve stale data only when the live source is unreachable.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ..ai.config import get_config


def _cache_root() -> Path:
    return Path(get_config()["nasa_cache_directory"]).resolve()


def cache_key(namespace: str, params: Dict[str, Any]) -> str:
    serialised = json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in namespace)
    return f"{safe}-{digest[:24]}.json"


def read(namespace: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return ``{"payload", "age", "fresh"}`` or ``None`` when nothing is cached."""
    path = _cache_root() / cache_key(namespace, params)
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = float(envelope.get("fetched_at", 0.0))
        payload = envelope.get("payload")
        if not isinstance(payload, (dict, list)):
            return None
        age = time.time() - fetched_at
        fresh = age <= float(get_config()["nasa_data_cache_ttl"])
        return {"payload": payload, "age": age, "fresh": fresh}
    except (OSError, ValueError, TypeError):
        return None


def write(namespace: str, params: Dict[str, Any], payload: Any) -> None:
    root = _cache_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        path = root / cache_key(namespace, params)
        path.write_text(
            json.dumps({"fetched_at": time.time(), "payload": payload}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # Cache is best-effort; a write failure must never break the API.
        return
