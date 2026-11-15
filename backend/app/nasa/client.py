"""Shared HTTP plumbing for NASA public data sources.

Design rules (Phase 2):

* No fabricated responses — on any failure the caller is told the source is
  unavailable; a clearly-labelled cached copy is only served when one exists.
* Tight timeouts, one retry for transient HTTP failures, JSON validation.
* API keys are never required: NTRS and PDS are public endpoints.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

USER_AGENT = "JAMT/Phase2 (Educational NASA data integration; contact: JAMT developer)"


class NasaApiUnavailable(RuntimeError):
    """Raised when an official NASA source cannot be reached or trusted."""


def get_json(url: str, *, params: Optional[dict] = None, timeout: float = 15.0) -> Any:
    """Fetch a JSON document from a public NASA endpoint.

    Raises :class:`NasaApiUnavailable` on network errors, non-2xx responses,
    rate limiting, or malformed JSON. Never invents payloads.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_error: Optional[Exception] = None

    for attempt in range(2):
        try:
            with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
                response = client.get(url, params=params)
            if response.status_code == 429:
                raise NasaApiUnavailable("NASA rate limit reached (HTTP 429)")
            if response.status_code >= 500:
                raise NasaApiUnavailable(f"NASA source error (HTTP {response.status_code})")
            if response.status_code >= 400:
                raise NasaApiUnavailable(f"NASA request rejected (HTTP {response.status_code})")
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type and "text" not in content_type:
                raise NasaApiUnavailable(f"unexpected content-type: {content_type or 'unknown'}")
            try:
                return response.json()
            except ValueError as exc:
                raise NasaApiUnavailable("malformed JSON from NASA source") from exc
        except NasaApiUnavailable as exc:
            last_error = exc
            if attempt == 0 and ("error" in str(exc) or "rate limit" in str(exc)):
                continue
            raise
        except httpx.TimeoutException as exc:
            last_error = exc
            if attempt == 0:
                continue
            raise NasaApiUnavailable("timed out contacting NASA source") from exc
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt == 0:
                continue
            raise NasaApiUnavailable(f"NASA connection error: {exc.__class__.__name__}") from exc

    raise NasaApiUnavailable(str(last_error) if last_error else "NASA source unavailable")
