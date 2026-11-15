import logging

import httpx
import pytest

from app import main
from app.ai import agent


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeClient:
    def __init__(self, outcomes, calls):
        self.outcomes = iter(outcomes)
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def install_fake_client(monkeypatch, outcomes):
    calls = []
    outcome_iterator = iter(outcomes)
    monkeypatch.setattr(agent.httpx, "Client", lambda **kwargs: FakeClient(outcome_iterator, calls))
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    return calls


def success_response(content):
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


def test_llm_success_is_used_as_response(monkeypatch):
    install_fake_client(monkeypatch, [success_response("Normal completion")])
    result = agent.run_agent(None, "What is NASA studying for long missions?")
    assert result["response"] == "Normal completion"


def test_llm_think_block_is_stripped(monkeypatch):
    install_fake_client(monkeypatch, [success_response("<think>private reasoning</think>Final answer")])
    assert agent._call_llm("question") == "Final answer"


@pytest.mark.parametrize(
    "outcome",
    [
        FakeResponse(401, {}),
        FakeResponse(500, {}),
        httpx.TimeoutException("timeout"),
        FakeResponse(200, ValueError("malformed")),
        FakeResponse(200, {"choices": []}),
    ],
)
def test_llm_failures_use_deterministic_fallback(monkeypatch, outcome):
    install_fake_client(monkeypatch, [outcome, outcome])
    result = agent.run_agent(None, "How do astronauts handle solar radiation storms?")
    assert "Here are the relevant passages from the currently indexed official NASA publications" in result["response"]


def test_llm_429_retries_once(monkeypatch):
    calls = install_fake_client(monkeypatch, [FakeResponse(429, {}), success_response("Recovered")])
    assert agent._call_llm("question") == "Recovered"
    assert len(calls) == 2


def test_no_key_never_calls_httpx(monkeypatch):
    calls = []
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setattr(agent.httpx, "Client", lambda **kwargs: calls.append(kwargs))
    assert agent._call_llm("question") is None
    assert calls == []


def test_key_is_not_logged_or_returned(monkeypatch, caplog):
    secret = "test-only-secret-value"
    install_fake_client(monkeypatch, [FakeResponse(401, {})])
    monkeypatch.setenv("LLM_API_KEY", secret)
    with caplog.at_level(logging.WARNING):
        result = agent.run_agent(None, "How do astronauts handle radiation?")
    assert secret not in caplog.text
    assert secret not in result["response"]
    assert all(secret not in str(value) for value in result.values())


def test_report_uses_static_feedback_when_llm_fails(ac, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(main, "_call_llm", lambda prompt: None)
    main._REPORT_FEEDBACK_CACHE.clear()
    payload = {
        "name": "Report Test",
        "destination": "mars",
        "astronaut_count": 2,
        "duration": 5,
        "difficulty": "easy",
    }
    created = ac.post("/api/missions", json=payload)
    report = ac.get(f"/api/missions/{created.json()['id']}/report")
    assert report.status_code == 200
    data = report.json()
    assert data["feedback"] == data["educational_feedback"]
    assert "balancing resource consumption" in data["feedback"]
