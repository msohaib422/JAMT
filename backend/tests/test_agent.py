import os

from app.ai import agent


def test_general_question_returns_sources(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    result = agent.run_agent(None, "How do astronauts handle solar radiation storms?")
    assert "response" in result
    assert isinstance(result["tools_used"], list)
    assert len(result["sources"]) > 0
    assert result["suggested_actions"] == []


def test_agent_chat_without_openrouter_key_returns_sources(ac, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    response = ac.post("/api/agent/chat", json={"message": "How do astronauts handle solar radiation storms?"})
    assert response.status_code == 200
    data = response.json()
    assert data["sources"]
    assert set(data) == {"response", "tools_used", "sources", "suggested_actions"}


def test_status_query_with_mocked_backend(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setattr(agent, "get_mission_status", lambda mid: {
        "ok": True,
        "mission": {
            "id": mid, "name": "Test", "destination": "mars", "status": "active",
            "current_day": 1, "duration": 5, "progress": 20.0,
            "oxygen": 95.0, "water": 96.0, "food": 96.0, "energy": 96.0, "fuel": 97.0,
            "astronaut_health": 98.0, "emergencies": [],
        },
    })
    monkeypatch.setattr(agent, "get_mission_history", lambda mid: {"ok": True, "history": []})
    result = agent.run_agent(1, "What is our mission status?")
    assert "active" in result["response"]
    assert any(t["label"] == "get_mission_status" for t in result["tools_used"])


def test_oxygen_query_suggests_actions_without_executing(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    mission = {
        "id": 1, "name": "Test", "destination": "mars", "status": "active",
        "current_day": 1, "duration": 5, "progress": 20.0,
        "oxygen": 80.0, "water": 96.0, "food": 96.0, "energy": 96.0, "fuel": 97.0,
        "astronaut_health": 98.0, "emergencies": [],
    }
    monkeypatch.setattr(agent, "get_mission_status", lambda mid: {"ok": True, "mission": mission})
    monkeypatch.setattr(agent, "get_resource_levels", lambda mid: {"ok": True, "resources": [
        {"type": "oxygen", "percent": 80.0}, {"type": "water", "percent": 96.0},
    ]})
    monkeypatch.setattr(agent, "calculate_resource_consumption", lambda mid: {"ok": True, "estimates": {}})
    monkeypatch.setattr(agent, "get_mission_history", lambda mid: {"ok": True, "history": []})
    monkeypatch.setattr(agent, "get_available_actions", lambda mid: {"ok": True, "actions": [
        {"type": "repair", "title": "Repair", "description": "d", "reason": "r"},
    ]})
    result = agent.run_agent(1, "Why is our oxygen decreasing?")
    assert len(result["suggested_actions"]) >= 1
    assert all(a["type"] in {"repair", "rest", "experiment", "wait"} for a in result["suggested_actions"])


def test_invalid_mission_returns_failure_message(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setattr(agent, "get_mission_status", lambda mid: {"ok": False, "error": "Mission not found"})
    monkeypatch.setattr(agent, "get_mission_history", lambda mid: {"ok": False, "error": "Mission not found"})
    result = agent.run_agent(999999, "What is our mission status?")
    assert "could not retrieve" in result["response"].lower() or "verify" in result["response"].lower()


def test_no_action_auto_execution(monkeypatch):
    # Ensure run_agent never calls execute_mission_action.
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    called = {"value": False}

    def fake_execute(*args, **kwargs):
        called["value"] = True
        return {"ok": True}

    monkeypatch.setattr(agent, "execute_mission_action", fake_execute, raising=False)
    monkeypatch.setattr(agent, "get_mission_status", lambda mid: {"ok": True, "mission": {
        "id": mid, "name": "Test", "destination": "mars", "status": "active",
        "current_day": 1, "duration": 5, "progress": 20.0,
        "oxygen": 80.0, "water": 96.0, "food": 96.0, "energy": 96.0, "fuel": 97.0,
        "astronaut_health": 98.0, "emergencies": [],
    }})
    monkeypatch.setattr(agent, "get_resource_levels", lambda mid: {"ok": True, "resources": []})
    monkeypatch.setattr(agent, "calculate_resource_consumption", lambda mid: {"ok": True, "estimates": {}})
    monkeypatch.setattr(agent, "get_mission_history", lambda mid: {"ok": True, "history": []})
    monkeypatch.setattr(agent, "get_available_actions", lambda mid: {"ok": True, "actions": []})
    agent.run_agent(1, "Repair the oxygen leak now")
    assert called["value"] is False
