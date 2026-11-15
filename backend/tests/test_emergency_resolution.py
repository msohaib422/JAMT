def _create_active_mission(ac, **overrides):
    payload = {
        "name": "Resolution Test",
        "destination": "mars",
        "astronaut_count": 3,
        "duration": 5,
        "difficulty": "medium",
    }
    payload.update(overrides)
    resp = ac.post("/api/missions", json=payload)
    assert resp.status_code == 201
    mission_id = resp.json()["id"]
    resp = ac.post(f"/api/missions/{mission_id}/start")
    assert resp.status_code == 200
    return mission_id


def _trigger_emergency(ac, mission_id, emergency_type=None):
    body = {"type": emergency_type} if emergency_type else {}
    resp = ac.post(f"/api/missions/{mission_id}/emergency", json=body)
    assert resp.status_code == 200
    return resp.json()


class TestEmergencyResolution:
    def test_resolve_requires_action(self, ac):
        mission_id = _create_active_mission(ac)
        emergency = _trigger_emergency(ac, mission_id, emergency_type="oxygen_leakage")
        resp = ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        assert resp.status_code == 400

    def test_valid_resolution(self, ac):
        mission_id = _create_active_mission(ac)
        emergency = _trigger_emergency(ac, mission_id, emergency_type="oxygen_leakage")
        ac.post(f"/api/missions/{mission_id}/actions", json={"action": "repair"})
        resp = ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["emergency"]["status"] == "resolved"
        assert data["mission"]["status"] == "active"
        assert len(data["mission"]["resolved_emergencies"]) == 1

    def test_duplicate_resolution(self, ac):
        mission_id = _create_active_mission(ac)
        emergency = _trigger_emergency(ac, mission_id, emergency_type="power_failure")
        ac.post(f"/api/missions/{mission_id}/actions", json={"action": "repair"})
        first = ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        assert first.status_code == 200
        second = ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        assert second.status_code == 400

    def test_wrong_mission(self, ac):
        mission_a = _create_active_mission(ac, name="Mission A")
        mission_b = _create_active_mission(ac, name="Mission B")
        emergency = _trigger_emergency(ac, mission_a, emergency_type="oxygen_leakage")
        ac.post(f"/api/missions/{mission_a}/actions", json={"action": "repair"})
        resp = ac.post(f"/api/missions/{mission_b}/emergencies/{emergency['id']}/resolve")
        assert resp.status_code == 404

    def test_invalid_emergency_id(self, ac):
        mission_id = _create_active_mission(ac)
        resp = ac.post(f"/api/missions/{mission_id}/emergencies/999999/resolve")
        assert resp.status_code == 404

    def test_solar_storm_requires_rest(self, ac):
        mission_id = _create_active_mission(ac)
        emergency = _trigger_emergency(ac, mission_id, emergency_type="solar_radiation_storm")
        ac.post(f"/api/missions/{mission_id}/actions", json={"action": "repair"})
        resp = ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        assert resp.status_code == 400
        ac.post(f"/api/missions/{mission_id}/actions", json={"action": "rest"})
        resp = ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        assert resp.status_code == 200
        assert resp.json()["emergency"]["status"] == "resolved"

    def test_history_contains_resolution(self, ac):
        mission_id = _create_active_mission(ac)
        emergency = _trigger_emergency(ac, mission_id, emergency_type="equipment_malfunction")
        ac.post(f"/api/missions/{mission_id}/actions", json={"action": "repair"})
        ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        resp = ac.get(f"/api/missions/{mission_id}/history")
        assert resp.status_code == 200
        assert any(e.get("event_type") == "emergency_resolved" or e.get("type") == "emergency_resolved" for e in resp.json())
