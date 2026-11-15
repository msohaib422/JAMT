"""Backend API tools used by the JAMT AI agent.

The agent never touches SQLite directly; all mission state comes from HTTP APIs.
"""

from typing import Any, Dict, List, Optional

import httpx

from .config import get_config


def _base_url() -> str:
    return get_config()["backend_api_url"].rstrip("/")


def _get(path: str) -> Dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
        if resp.status_code == 404:
            return {"ok": False, "error": "Mission not found", "status_code": 404}
        if resp.status_code >= 400:
            return {"ok": False, "error": resp.text, "status_code": resp.status_code}
        return {"ok": True, "data": resp.json()}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"Backend connection error: {exc}"}


def get_mission_status(mission_id: int) -> Dict[str, Any]:
    result = _get(f"/api/missions/{mission_id}")
    if not result["ok"]:
        return result
    # Also fetch active emergencies via status endpoint if available.
    status_result = _get(f"/api/missions/{mission_id}/status")
    data = result["data"]
    if status_result["ok"]:
        status_data = status_result["data"]
        if isinstance(status_data, dict):
            if "emergencies" in status_data:
                data = {**data, "emergencies": status_data["emergencies"]}
            elif "mission" in status_data and isinstance(status_data["mission"], dict):
                data = {**status_data["mission"], "emergencies": status_data.get("emergencies", data.get("emergencies", []))}
    return {"ok": True, "mission": data}


def get_resource_levels(mission_id: int) -> Dict[str, Any]:
    result = _get(f"/api/missions/{mission_id}/resources")
    if not result["ok"]:
        return result
    return {"ok": True, "resources": result["data"]}


def get_astronaut_health(mission_id: int) -> Dict[str, Any]:
    result = _get(f"/api/missions/{mission_id}/astronauts")
    if not result["ok"]:
        return result
    return {"ok": True, "astronauts": result["data"]}


def get_mission_history(mission_id: int, limit: int = 20) -> Dict[str, Any]:
    result = _get(f"/api/missions/{mission_id}/history")
    if not result["ok"]:
        return result
    events = result["data"]
    if isinstance(events, list):
        events = events[-limit:]
    return {"ok": True, "history": events}


def get_available_actions(mission_id: int) -> Dict[str, Any]:
    # Backend does not expose a dedicated actions endpoint; derive safe,
    # contract-backed actions from the known simulation capabilities.
    status = get_mission_status(mission_id)
    if not status["ok"]:
        return status
    mission = status["mission"]
    actions: List[Dict[str, Any]] = [
        {"type": "repair", "title": "Repair Systems", "description": "Repair equipment and stabilize systems.", "reason": "Restores functionality but consumes resources."},
        {"type": "rest", "title": "Crew Rest", "description": "Allow crew to recover health.", "reason": "Improves astronaut health and reduces fatigue."},
        {"type": "experiment", "title": "Run Experiment", "description": "Advance mission progress.", "reason": "Consumes resources but increases progress."},
        {"type": "wait", "title": "Wait and Monitor", "description": "Hold position and conserve resources.", "reason": "No extra consumption beyond daily rates."},
    ]
    emergencies = mission.get("emergencies") or []
    if emergencies:
        actions.insert(0, {"type": "repair", "title": "Emergency Repair", "description": "Prioritize emergency response repair.", "reason": "Active emergency requires immediate attention."})
    return {"ok": True, "actions": actions, "mission_status": mission.get("status")}


def calculate_resource_consumption(mission_id: int) -> Dict[str, Any]:
    status = get_mission_status(mission_id)
    resources = get_resource_levels(mission_id)
    if not status["ok"]:
        return status
    if not resources["ok"]:
        return resources
    mission = status["mission"]
    try:
        from app.simulation import DAILY_CONSUMPTION
    except Exception:
        DAILY_CONSUMPTION = {}
    estimates = {}
    for r in resources["resources"]:
        rtype = r["type"]
        rate = float(DAILY_CONSUMPTION.get(rtype, 0.0))
        percent = float(r.get("percent", 0.0))
        days = (percent / rate) if rate > 0 else None
        estimates[rtype] = {
            "current_percent": percent,
            "daily_consumption_percent": rate,
            "estimated_days_remaining": (round(days, 1) if days is not None else None),
        }
    return {
        "ok": True,
        "mission_day": mission.get("current_day"),
        "duration": mission.get("duration"),
        "estimates": estimates,
        "note": "Estimates use backend consumption rates; backend remains authoritative.",
    }


def execute_mission_action(mission_id: int, action: str, approved: bool = False) -> Dict[str, Any]:
    if not approved:
        return {"ok": False, "error": "Action execution requires explicit trainee approval."}
    if action not in {"repair", "rest", "experiment", "wait"}:
        return {"ok": False, "error": f"Unsupported action: {action}"}
    url = f"{_base_url()}/api/missions/{mission_id}/actions"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json={"action": action})
        if resp.status_code >= 400:
            return {"ok": False, "error": resp.text, "status_code": resp.status_code}
        return {"ok": True, "result": resp.json()}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"Backend connection error: {exc}"}
