"""Public NTRS client — real NASA technical publications.

Every field returned here is passed through from the NTRS public API together
with the original NTRS link for verification. Nothing is synthesised.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..ai.config import get_config
from . import cache
from .client import NasaApiUnavailable, get_json

def _base() -> str:
    return get_config()["nasa_ntrs_base_url"].rstrip("/")


def search_documents(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search NTRS citations for ``query``.

    Returns a validated, attribution-preserving payload:

    ``{"available": True, "cached": bool, "stale": bool|absent,
       "retrieved": iso8601, "source": "ntrs.nasa.gov", "hits": int,
       "results": [...]}``

    On failure raises :class:`NasaApiUnavailable` unless a cached payload
    (fresh or stale) exists, in which case ``available: true`` is returned
    with ``cached: true`` and a clear provenance note.
    """
    limit = max(1, min(int(limit), 10))
    params = {"q": query, "limit": limit}
    cached = cache.read("ntrs_search", params)
    try:
        payload = get_json(f"{_base()}/citations/search", params={"q": query, "limit": limit})
        items, total = _validate_search_response(payload, query)
        response = {
            "available": True,
            "cached": False,
            "retrieved": _now_iso(),
            "source": "NASA Technical Reports Server (ntrs.nasa.gov)",
            "query": query,
            "hits": total,
            "results": items,
        }
        cache.write("ntrs_search", params, response)
        return response
    except NasaApiUnavailable as exc:
        if cached:
            payload = cached["payload"]
            return {
                **(payload if isinstance(payload, dict) else {"results": payload}),
                "available": True,
                "cached": True,
                "stale": not cached["fresh"],
                "message": f"Live NTRS is unavailable ({exc}); showing cached results from {payload.get('retrieved', 'an earlier fetch')}.",
            }
        raise


def _validate_search_response(payload: Any, query: str) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        raise NasaApiUnavailable("unexpected NTRS response shape")
    stats = payload.get("stats") or {}
    total = None
    if isinstance(stats, dict) and stats.get("total") is not None:
        try:
            total = int(stats["total"])
        except (TypeError, ValueError):
            total = None
    raw = payload.get("results") or []
    if not isinstance(raw, list):
        raise NasaApiUnavailable("unexpected NTRS results shape")

    items: List[Dict[str, Any]] = []
    for entry in raw[:10]:
        if not isinstance(entry, dict):
            continue
        ntrs_id = entry.get("id")
        title = entry.get("title")
        if not ntrs_id or not title:
            continue
        pub = (entry.get("publications") or [{}])[0]
        publication_date = pub.get("publicationDate") or entry.get("created") or None
        if publication_date:
            publication_date = str(publication_date)[:10]
        downloads = entry.get("downloads") or []
        items.append(
            {
                "ntrs_id": str(ntrs_id),
                "title": title,
                "url": f"https://ntrs.nasa.gov/citations/{ntrs_id}",
                "publication_date": publication_date,
                "sti_type": entry.get("stiTypeDetails") or entry.get("stiType"),
                "distribution": entry.get("distribution"),
                "center": (entry.get("center") or {}).get("name") if isinstance(entry.get("center"), dict) else None,
                "abstract": entry.get("abstract"),
                "downloads": [
                    download.get("links", {}).get("original") or download.get("links", {}).get("pdf")
                    for download in downloads
                    if isinstance(download, dict)
                ][:3],
            }
        )
    if total is not None:
        return items, total
    return items, len(items)


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
