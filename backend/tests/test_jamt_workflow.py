def test_experiment_progress_survives_daily_consumption(ac):
    mission_id = _create_mission(ac, duration=10)
    assert ac.post(f"/api/missions/{mission_id}/start").status_code == 200

    experiment = ac.post(f"/api/missions/{mission_id}/actions", json={"action": "experiment"})
    assert experiment.status_code == 200
    assert experiment.json()["progress"] == 15.0

    advance = ac.post(f"/api/missions/{mission_id}/advance")
    assert advance.status_code == 200
    assert advance.json()["progress"] == 25.0


def _create_mission(ac, **overrides):
    payload = {
        "name": "Mars Expedition 01",
        "destination": "mars",
        "astronaut_count": 3,
        "duration": 5,
        "difficulty": "medium",
    }
    payload.update(overrides)
    resp = ac.post("/api/missions", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestMissionLifecycle:
    def test_complete_mars_workflow(self, ac):
        mission_id = _create_mission(ac)

        # start
        resp = ac.post(f"/api/missions/{mission_id}/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        # status
        resp = ac.get(f"/api/missions/{mission_id}/status")
        assert resp.status_code == 200

        # resources
        resp = ac.get(f"/api/missions/{mission_id}/resources")
        assert resp.status_code == 200
        resources = resp.json()
        assert {r["type"] for r in resources} == {"oxygen", "water", "food", "energy", "fuel"}

        # astronauts
        resp = ac.get(f"/api/missions/{mission_id}/astronauts")
        assert resp.status_code == 200
        astronauts = resp.json()
        assert len(astronauts) == 3
        assert astronauts[0]["name"] == "Astronaut 1"

        # advance
        resp = ac.post(f"/api/missions/{mission_id}/advance")
        assert resp.status_code == 200
        assert resp.json()["current_day"] == 1

        # trigger emergency (deterministic)
        resp = ac.post(f"/api/missions/{mission_id}/emergency", json={})
        assert resp.status_code == 200
        emergency = resp.json()
        assert emergency["status"] == "active"
        assert emergency["type"] in {
            "oxygen_leakage", "power_failure", "water_shortage",
            "solar_radiation_storm", "equipment_malfunction",
        }

        # action using frontend action_type contract
        resp = ac.post(f"/api/missions/{mission_id}/actions", json={"action_type": "repair"})
        assert resp.status_code == 200

        # history
        resp = ac.get(f"/api/missions/{mission_id}/history")
        assert resp.status_code == 200
        history = resp.json()
        assert any(e.get("event_type") == "mission_created" or e.get("type") == "mission_created" for e in history)
        assert any(e.get("event_type") == "emergency_triggered" or e.get("type") == "emergency_triggered" for e in history)

        # report
        resp = ac.get(f"/api/missions/{mission_id}/report")
        assert resp.status_code == 200
        report = resp.json()
        assert "score" in report
        assert report["outcome"] in {"active", "completed", "failed", "paused"}
        assert isinstance(report["areas_for_improvement"], list)

    def test_pause_resume(self, ac):
        mission_id = _create_mission(ac)
        ac.post(f"/api/missions/{mission_id}/start")
        resp = ac.post(f"/api/missions/{mission_id}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"
        resp = ac.post(f"/api/missions/{mission_id}/resume")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_invalid_mission_id(self, ac):
        for path in [
            "/api/missions/999999",
            "/api/missions/999999/status",
            "/api/missions/999999/resources",
            "/api/missions/999999/astronauts",
            "/api/missions/999999/history",
            "/api/missions/999999/report",
        ]:
            assert ac.get(path).status_code == 404
        assert ac.post("/api/missions/999999/start").status_code == 404
        assert ac.post("/api/missions/999999/advance").status_code == 404
        assert ac.post("/api/missions/999999/actions", json={"action": "rest"}).status_code == 404
        assert ac.post("/api/missions/999999/emergency", json={}).status_code == 404

    def test_invalid_action_rejected(self, ac):
        mission_id = _create_mission(ac)
        ac.post(f"/api/missions/{mission_id}/start")
        resp = ac.post(f"/api/missions/{mission_id}/actions", json={"action": "fly"})
        assert resp.status_code == 422

    def test_action_requires_active_mission(self, ac):
        mission_id = _create_mission(ac)
        resp = ac.post(f"/api/missions/{mission_id}/actions", json={"action": "rest"})
        assert resp.status_code == 400

    def test_emergency_requires_active_mission(self, ac):
        mission_id = _create_mission(ac)
        resp = ac.post(f"/api/missions/{mission_id}/emergency", json={})
        assert resp.status_code == 400

    def test_list_missions(self, ac):
        _create_mission(ac, name="Mission A")
        _create_mission(ac, name="Mission B")
        resp = ac.get("/api/missions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert {m["name"] for m in data} == {"Mission A", "Mission B"}

    def test_health_check(self, ac):
        resp = ac.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
