"""Send one small real-provider smoke request without exposing credentials."""

from __future__ import annotations

import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.config import get_config  # noqa: E402


def main() -> None:
    config = get_config()
    started = time.perf_counter()
    status = "not-configured"
    reply = ""
    if config["llm_api_key"]:
        try:
            with httpx.Client(timeout=config["llm_timeout_seconds"]) as client:
                response = client.post(
                    f"{config['llm_base_url'].rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {config['llm_api_key']}", "Content-Type": "application/json"},
                    json={
                        "model": config["llm_model"],
                        "messages": [{"role": "user", "content": "Reply with one short greeting."}],
                        "max_tokens": 32,
                        "temperature": config["llm_temperature"],
                    },
                )
            status = str(response.status_code)
            try:
                choices = response.json().get("choices", [])
                reply = str(choices[0].get("message", {}).get("content", "")) if choices else ""
            except (ValueError, TypeError, IndexError, AttributeError):
                reply = ""
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
    elapsed = time.perf_counter() - started
    print(f"model: {config['llm_model']}")
    print(f"HTTP status: {status}")
    print(f"latency_seconds: {elapsed:.2f}")
    print(f"reply: {reply[:200]}")


if __name__ == "__main__":
    main()
