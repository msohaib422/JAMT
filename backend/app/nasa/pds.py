"""Public PDS (Planetary Data System) client — real planetary datasets.

PDS is a *dataset metadata* registry, not a prose science source: results are
always presented as datasets (title, LID, PDS node, ingestion date, identifier
link) and are never rewritten into scientific explanations.

All 916 product bundles are retrieved once and filtered client-side by the
destination's target LID (``planet.mars`` / ``satellite.earth.moon``), which is
an exact, verifiable match — no fuzzy keyword guessing.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..ai.config import get_config
from . import cache
from .client import NasaApiUnavailable, get_json

_BUNDLE_QUERY = "(pds:Identification_Area.pds:product_class eq \"Product_Bundle\")"
_BUNDLE_FIELDS = "ops:Harvest_Info.ops:node_name,ops:Harvest_Info.ops:harvest_date_time"
_BUNDLE_LIMIT = 1000

_DESTINATION_TARGETS: Dict[str, List[str]] = {
    "moon": ["satellite.earth.moon"],
    "mars": ["planet.mars"],
}


def _base() -> str:
    return get_config()["nasa_pds_base_url"].rstrip("/")


def destination_datasets(destination: str, limit: int = 8) -> Dict[str, Any]:
    """Return real NASA PDS bundles whose targets include ``destination``.

    The bundle registry is cached for ``NASA_DATA_CACHE_TTL`` seconds; a live
    failure only falls back to an explicitly flagged cached copy.
    """
    destination = (destination or "").lower()
    if destination not in _DESTINATION_TARGETS:
        raise NasaApiUnavailable(f"unsupported destination: {destination}")

    limit = max(1, min(int(limit), 12))
    params = {"destination": destination}
    cached = cache.read("pds_bundles", params)
    try:
        payload = get_json(
            f"{_base()}/products",
            params={
                "q": _BUNDLE_QUERY,
                "limit": _BUNDLE_LIMIT,
                "fields": _BUNDLE_FIELDS,
            },
            timeout=60.0,
        )
        bundles = _validate_bundle_response(payload)
        targets = _DESTINATION_TARGETS[destination]
        matching = [
            bundle
            for bundle in bundles
            if any(target in target_id for target_id in bundle.get("target_ids", []) for target in targets)
        ]
        matching.sort(key=lambda bundle: bundle["title"])
        limit_payload = {
            "available": True,
            "cached": False,
            "retrieved": _now_iso(),
            "source": "NASA Planetary Data System (pds.nasa.gov)",
            "destination": destination,
            "total_bundles": len(bundles),
            "matching_bundles": len(matching),
            "results": matching[:limit],
        }
        cache.write("pds_bundles", params, limit_payload)
        return limit_payload
    except NasaApiUnavailable as exc:
        if cached:
            payload = cached["payload"] if isinstance(cached["payload"], dict) else {}
            return {
                **payload,
                "available": True,
                "cached": True,
                "stale": not cached["fresh"],
                "message": f"Live PDS is unavailable ({exc}); showing cached results from {payload.get('retrieved', 'an earlier fetch')}.",
            }
        raise


def _validate_bundle_response(payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        raise NasaApiUnavailable("unexpected PDS response shape")
    entries = payload.get("data") or []
    if not isinstance(entries, list):
        raise NasaApiUnavailable("unexpected PDS data shape")
    if not entries:
        summary = payload.get("summary")
        if isinstance(summary, dict) and not summary.get("hits"):
            return []
        raise NasaApiUnavailable("PDS registry returned an empty product list")

    bundles: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lid = entry.get("id")
        title = entry.get("title")
        if not lid or not title:
            continue
        props = entry.get("properties", {}) or {}
        node = (props.get("ops:Harvest_Info.ops:node_name") or [None])[0]
        ingested = (props.get("ops:Harvest_Info.ops:harvest_date_time") or [None])[0]
        bundles.append(
            {
                "name": title,
                "title": title,
                "lid": lid,
                "url": f"https://pds.nasa.gov/api/search/1/products/{lid}",
                "node": node,
                "ingested": ingested,
                "target_ids": [t.get("id", "") for t in (entry.get("targets") or []) if isinstance(t, dict)],
                "investigating": [i.get("id", "") for i in (entry.get("investigations") or []) if isinstance(i, dict)],
            }
        )
    if not bundles:
        raise NasaApiUnavailable("PDS registry entries were missing ids/titles")
    return bundles


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
