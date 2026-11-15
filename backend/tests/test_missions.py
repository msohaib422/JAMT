class TestCreateMission:
    def test_create_mission_valid(self, ac):
        payload = {
            "name": "Apollo Training Run",
            "destination": "moon",
            "astronaut_count": 4,
            "duration": 14,
            "difficulty": "medium",
        }
        resp = ac.post("/api/missions", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Apollo Training Run"
        assert data["destination"] == "moon"
        assert data["astronaut_count"] == 4
        assert data["duration"] == 14
        assert data["difficulty"] == "medium"
        assert data["status"] == "draft"
        assert data["current_day"] == 0
        assert data["progress"] == 0.0
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_mission_invalid_destination(self, ac):
        payload = {
            "name": "Test Mission",
            "destination": "jupiter",
            "astronaut_count": 4,
            "duration": 14,
            "difficulty": "medium",
        }
        resp = ac.post("/api/missions", json=payload)
        assert resp.status_code == 422

    def test_create_mission_invalid_difficulty(self, ac):
        payload = {
            "name": "Test Mission",
            "destination": "moon",
            "astronaut_count": 4,
            "duration": 14,
            "difficulty": "impossible",
        }
        resp = ac.post("/api/missions", json=payload)
        assert resp.status_code == 422

    def test_create_mission_invalid_crew_count(self, ac):
        payload = {
            "name": "Test Mission",
            "destination": "moon",
            "astronaut_count": 15,
            "duration": 14,
            "difficulty": "medium",
        }
        resp = ac.post("/api/missions", json=payload)
        assert resp.status_code == 422

    def test_create_mission_invalid_duration(self, ac):
        payload = {
            "name": "Test Mission",
            "destination": "moon",
            "astronaut_count": 4,
            "duration": 500,
            "difficulty": "medium",
        }
        resp = ac.post("/api/missions", json=payload)
        assert resp.status_code == 422

    def test_create_mission_empty_name(self, ac):
        payload = {
            "name": "",
            "destination": "moon",
            "astronaut_count": 4,
            "duration": 14,
            "difficulty": "medium",
        }
        resp = ac.post("/api/missions", json=payload)
        assert resp.status_code == 422


class TestGetMission:
    def test_get_mission_exists(self, ac):
        payload = {
            "name": "Test Mission",
            "destination": "mars",
            "astronaut_count": 5,
            "duration": 30,
            "difficulty": "hard",
        }
        create_resp = ac.post("/api/missions", json=payload)
        mission_id = create_resp.json()["id"]

        resp = ac.get(f"/api/missions/{mission_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == mission_id
        assert data["name"] == "Test Mission"
        assert data["destination"] == "mars"

    def test_get_mission_not_found(self, ac):
        resp = ac.get("/api/missions/999999")
        assert resp.status_code == 404


class TestListMissions:
    def test_list_missions_empty(self, ac):
        resp = ac.get("/api/missions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_missions_multiple(self, ac):
        missions_data = [
            {"name": "Mission 1", "destination": "moon", "astronaut_count": 3, "duration": 7, "difficulty": "easy"},
            {"name": "Mission 2", "destination": "mars", "astronaut_count": 4, "duration": 14, "difficulty": "medium"},
            {"name": "Mission 3", "destination": "moon", "astronaut_count": 5, "duration": 30, "difficulty": "hard"},
        ]
        for m in missions_data:
            ac.post("/api/missions", json=m)

        resp = ac.get("/api/missions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["name"] == "Mission 3"
        assert data[1]["name"] == "Mission 2"
        assert data[2]["name"] == "Mission 1"
        for mission in data:
            assert "id" in mission
            assert "name" in mission
            assert "destination" in mission
            assert "status" in mission
            assert "created_at" in mission


class TestHealthCheck:
    def test_health_check(self, ac):
        resp = ac.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
