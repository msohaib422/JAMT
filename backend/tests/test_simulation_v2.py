"""Phase 1 — Simulation Engine V2 test suite.

Covers destination intelligence, difficulty intelligence, crew-aware resource
consumption, health consistency, emergency integration and lifecycle
compatibility.  All tests run against the isolated in-memory database that
``backend/conftest.py`` configures — the project's ``jamt.db`` is never
written to.
"""

from types import SimpleNamespace

import pytest

from app.simulation import (
    ACTION_EFFECTS,
    apply_action,
    apply_daily_consumption,
    daily_plan,
    evaluate_mission_status,
    mission_profile,
)
from app.simulation_config import (
    AUTO_EMERGENCY_EFFECT_FACTOR,
    AUTO_EMERGENCY_TRIGGER_THRESHOLD,
    CRITICAL_RESOURCE_EMERGENCY_MAP,
    DESTINATIONS,
    DIFFICULTIES,
    EMERGENCY_TYPES,
    REFERENCE_CREW,
    RESOURCE_ORDER,
    RESOURCE_RULES,
    build_profile,
    crew_factor,
    emergency_risk,
    health_decay,
    resource_consumption,
    scale_emergency_effects,
    select_emergency_type,
)


def make_mission(**overrides):
    """A lightweight mission object for the pure simulation functions."""
    values = dict(
        destination="moon",
        difficulty="medium",
        astronaut_count=REFERENCE_CREW,
        duration=10,
        current_day=0,
        progress=0.0,
        oxygen=100.0,
        fuel=100.0,
        food=100.0,
        water=100.0,
        energy=100.0,
        astronaut_health=100.0,
        status="active",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def api_mission(ac, **overrides):
    """Create and start a mission through the public API."""
    payload = {
        "name": "V2 Test Mission",
        "destination": "moon",
        "astronaut_count": 4,
        "duration": 14,
        "difficulty": "medium",
    }
    payload.update(overrides)
    resp = ac.post("/api/missions", json=payload)
    assert resp.status_code == 201, resp.text
    mission_id = resp.json()["id"]
    resp = ac.post(f"/api/missions/{mission_id}/start")
    assert resp.status_code == 200, resp.text
    return mission_id


# ---------------------------------------------------------------------------
# 1. Destinations
# ---------------------------------------------------------------------------

class TestDestinations:
    def test_supported_destinations_are_unchanged(self):
        assert set(DESTINATIONS) == {"moon", "mars"}

    def test_every_destination_has_a_complete_profile(self):
        for destination_id, destination in DESTINATIONS.items():
            assert destination["id"] == destination_id
            assert destination["label"]
            assert destination["summary"]
            assert destination["hazards"]
            assert destination["operational_challenges"]
            assert destination["references"], "every destination must cite its references"
            assert set(destination["consumption_modifiers"]) == set(RESOURCE_ORDER)
            assert destination["radiation"]["level"] in {"low", "elevated", "high"}
            assert destination["radiation"]["health_penalty_per_day"] >= 0
            assert destination["communications"]["label"]
            assert 0.0 <= destination["base_emergency_risk"] <= 1.0
            assert set(destination["emergency_weights"]) == set(EMERGENCY_TYPES)

    def test_destination_changes_consumption(self):
        moon = resource_consumption("oxygen", "moon", "medium", REFERENCE_CREW)
        mars = resource_consumption("oxygen", "mars", "medium", REFERENCE_CREW)
        assert mars["daily_rate"] > moon["daily_rate"]
        assert mars["destination_multiplier"] != moon["destination_multiplier"]

    def test_destination_changes_health_decay(self):
        assert health_decay("moon", "medium")["daily_decay"] == pytest.approx(2.3)
        assert health_decay("mars", "medium")["daily_decay"] == pytest.approx(2.8)

    def test_destination_appears_in_the_live_profile(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="hard")
        data = ac.get(f"/api/missions/{mission_id}").json()
        simulation = data["simulation"]
        assert simulation["destination"]["id"] == "mars"
        assert simulation["difficulty"]["id"] == "hard"
        assert simulation["crew"]["size"] == 4
        assert simulation["destination"]["radiation"]["level"] == "high"
        assert simulation["destination"]["hazards"]

    def test_unknown_destination_falls_back_to_default(self):
        profile = build_profile("jupiter", "medium", REFERENCE_CREW)
        assert profile["destination"]["id"] == "moon"


# ---------------------------------------------------------------------------
# 2. Difficulty
# ---------------------------------------------------------------------------

class TestDifficulty:
    def test_supported_difficulties_are_unchanged(self):
        assert set(DIFFICULTIES) == {"easy", "medium", "hard"}

    def test_every_difficulty_changes_consumption(self):
        rates = {}
        for difficulty_id in ("easy", "medium", "hard"):
            rates[difficulty_id] = resource_consumption(
                "oxygen", "moon", difficulty_id, REFERENCE_CREW
            )["daily_rate"]
        assert rates["easy"] < rates["medium"] < rates["hard"]
        assert rates["medium"] == pytest.approx(5.0)
        assert rates["easy"] == pytest.approx(3.75)
        assert rates["hard"] == pytest.approx(6.25)

    def test_difficulty_changes_health_and_risk(self):
        assert health_decay("moon", "easy")["daily_decay"] == pytest.approx(1.725)
        assert health_decay("moon", "hard")["daily_decay"] == pytest.approx(2.875)
        assert emergency_risk("mars", "easy")["score"] < emergency_risk("mars", "hard")["score"]

    def test_difficulty_scales_emergency_damage(self):
        base = {"oxygen": -20.0}
        easy = scale_emergency_effects(base, "oxygen_leakage", "moon", "easy")
        medium = scale_emergency_effects(base, "oxygen_leakage", "moon", "medium")
        hard = scale_emergency_effects(base, "oxygen_leakage", "moon", "hard")
        assert medium["oxygen"] == pytest.approx(-20.0)
        assert easy["oxygen"] == pytest.approx(-15.0)
        assert hard["oxygen"] == pytest.approx(-25.0)

    def test_difficulty_changes_live_behaviour(self, ac):
        easy_id = api_mission(ac, name="Easy Run", difficulty="easy")
        hard_id = api_mission(ac, name="Hard Run", difficulty="hard")
        easy = ac.post(f"/api/missions/{easy_id}/advance").json()
        hard = ac.post(f"/api/missions/{hard_id}/advance").json()
        assert easy["oxygen"] > hard["oxygen"]
        assert hard["simulation"]["difficulty"]["consumption_multiplier"] == 1.25

    def test_api_rejects_unknown_difficulty(self, ac):
        resp = ac.post("/api/missions", json={
            "name": "Bad", "destination": "moon", "astronaut_count": 2,
            "duration": 5, "difficulty": "impossible",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 3. Crew-aware consumption
# ---------------------------------------------------------------------------

class TestCrewAwareConsumption:
    def test_reference_crew_keeps_the_legacy_rates(self):
        """A 3-astronaut Moon mission keeps the historic consumption numbers.

        Energy is the documented exception: the Moon applies a x1.15 factor
        because a lunar night lasts about 14 Earth days.
        """
        expected = {"oxygen": 5.0, "water": 4.0, "food": 4.0, "fuel": 3.0}
        for resource_type, rate in expected.items():
            info = resource_consumption(resource_type, "moon", "medium", REFERENCE_CREW)
            assert info["daily_rate"] == pytest.approx(rate)
        # The Moon energy factor is intentional and documented.
        energy = resource_consumption("energy", "moon", "medium", REFERENCE_CREW)
        assert energy["daily_rate"] == pytest.approx(4.6)

    def test_documented_formula_is_applied(self):
        for destination_id in DESTINATIONS:
            for difficulty_id in DIFFICULTIES:
                for crew in (1, 3, 6, 12):
                    for resource_type in RESOURCE_ORDER:
                        rule = RESOURCE_RULES[resource_type]
                        dest = DESTINATIONS[destination_id]
                        diff = DIFFICULTIES[difficulty_id]
                        expected = (
                            rule["base_daily_rate"]
                            * (rule["overhead_share"] + rule["crew_share"] * crew / REFERENCE_CREW)
                            * dest["consumption_modifiers"][resource_type]
                            * diff["consumption_multiplier"]
                        )
                        info = resource_consumption(resource_type, destination_id, difficulty_id, crew)
                        assert info["daily_rate"] == pytest.approx(expected, abs=0.001)

    def test_crew_size_scales_resources_differently(self):
        small = resource_consumption("oxygen", "moon", "medium", 1)
        large = resource_consumption("oxygen", "moon", "medium", 12)
        assert large["crew_factor"] > small["crew_factor"]

        # Food is the most crew-driven resource...
        food_small = resource_consumption("food", "moon", "medium", 1)
        food_large = resource_consumption("food", "moon", "medium", 12)
        assert food_large["crew_factor"] - food_small["crew_factor"] > \
            large["crew_factor"] - small["crew_factor"]

        # ...and fuel is the least crew-driven one.
        fuel_small = resource_consumption("fuel", "moon", "medium", 1)
        fuel_large = resource_consumption("fuel", "moon", "medium", 12)
        assert fuel_large["crew_factor"] - fuel_small["crew_factor"] < \
            large["crew_factor"] - small["crew_factor"]

    def test_zero_crew_only_pays_habitat_overhead(self):
        for resource_type, rule in RESOURCE_RULES.items():
            factor = crew_factor(resource_type, 0)
            assert factor == pytest.approx(rule["overhead_share"])
            info = resource_consumption(resource_type, "moon", "medium", 0)
            assert info["daily_rate"] >= 0
            assert info["crew_factor"] == pytest.approx(rule["overhead_share"])

    def test_missing_crew_falls_back_to_the_reference_crew(self):
        info = resource_consumption("oxygen", "moon", "medium", None)
        assert info["crew_factor"] == pytest.approx(1.0)
        assert "reference crew" in info["explanation"]

    def test_crew_size_changes_the_live_mission(self, ac):
        small_id = api_mission(ac, name="Solo", astronaut_count=1)
        big_id = api_mission(ac, name="Full Crew", astronaut_count=12)
        small = ac.post(f"/api/missions/{small_id}/advance").json()
        big = ac.post(f"/api/missions/{big_id}/advance").json()
        assert big["oxygen"] < small["oxygen"]
        assert big["simulation"]["resources"]["oxygen"]["daily_rate"] > \
            small["simulation"]["resources"]["oxygen"]["daily_rate"]

    def test_crew_size_never_changes_fuel_dramatically(self, ac):
        solo = build_profile("mars", "medium", 1)["resources"]["fuel"]["daily_rate"]
        crew = build_profile("mars", "medium", 12)["resources"]["fuel"]["daily_rate"]
        assert crew / solo < 1.5


# ---------------------------------------------------------------------------
# 4. Boundaries, depletion, completion and failure
# ---------------------------------------------------------------------------

class TestBoundariesAndOutcomes:
    def test_resources_never_go_negative(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="hard", astronaut_count=12, duration=365)
        for _ in range(8):
            resp = ac.post(f"/api/missions/{mission_id}/advance")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            for resource_type in RESOURCE_ORDER:
                assert data[resource_type] >= 0
            if data["status"] != "active":
                break

    def test_resource_depletion_fails_the_mission(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="hard", astronaut_count=12, duration=365)
        status = "active"
        for _ in range(12):
            data = ac.post(f"/api/missions/{mission_id}/advance").json()
            status = data["status"]
            if status == "failed":
                break
        assert status == "failed"
        assert min(data[resource_type] for resource_type in RESOURCE_ORDER) == 0

    def test_mission_completes_at_the_planned_duration(self, ac):
        mission_id = api_mission(ac, destination="moon", difficulty="easy", duration=3)
        for expected_day in (1, 2, 3):
            data = ac.post(f"/api/missions/{mission_id}/advance").json()
            assert data["current_day"] == expected_day
        assert data["status"] == "completed"

    def test_progress_advances_with_the_mission_duration(self, ac):
        mission_id = api_mission(ac, duration=10)
        data = ac.post(f"/api/missions/{mission_id}/advance").json()
        assert data["progress"] == pytest.approx(10.0)

    def test_actions_keep_their_v1_effects(self):
        mission = make_mission()
        apply_action(mission, "experiment")
        assert mission.progress == pytest.approx(15.0)
        assert mission.oxygen == pytest.approx(92.0)

        mission = make_mission()
        apply_action(mission, "rest")
        assert mission.astronaut_health == pytest.approx(100.0)  # clamped to 100

        mission = make_mission()
        apply_action(mission, "repair")
        assert mission.fuel == pytest.approx(90.0)
        assert mission.oxygen == pytest.approx(95.0)

        mission = make_mission()
        apply_action(mission, "wait")
        assert mission.oxygen == pytest.approx(100.0)

    def test_action_effects_still_reach_the_crew_health(self, ac):
        mission_id = api_mission(ac)
        ac.post(f"/api/missions/{mission_id}/actions", json={"action": "rest"})
        astronauts = ac.get(f"/api/missions/{mission_id}/astronauts").json()
        assert all(a["health"] == pytest.approx(100.0) for a in astronauts)


# ---------------------------------------------------------------------------
# 5. Health consistency
# ---------------------------------------------------------------------------

class TestHealthConsistency:
    def test_mission_and_crew_health_move_together(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="hard", astronaut_count=4)
        for _ in range(3):
            ac.post(f"/api/missions/{mission_id}/advance")
        mission = ac.get(f"/api/missions/{mission_id}").json()
        astronauts = ac.get(f"/api/missions/{mission_id}/astronauts").json()
        average = sum(a["health"] for a in astronauts) / len(astronauts)
        assert mission["astronaut_health"] == pytest.approx(average)

    def test_health_decay_matches_the_configured_plan(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="medium", astronaut_count=4)
        before = ac.get(f"/api/missions/{mission_id}").json()["astronaut_health"]
        after = ac.post(f"/api/missions/{mission_id}/advance").json()["astronaut_health"]
        expected_decay = health_decay("mars", "medium")["daily_decay"]
        assert before - after == pytest.approx(expected_decay)

    def test_plan_is_the_single_source_of_truth(self):
        mission = make_mission(destination="mars", difficulty="hard", astronaut_count=6)
        plan = daily_plan(mission)
        apply_daily_consumption(mission)
        assert mission.oxygen == pytest.approx(100.0 - plan["resources"]["oxygen"]["daily_rate"])
        assert mission.astronaut_health == pytest.approx(100.0 - plan["health"]["daily_decay"])


# ---------------------------------------------------------------------------
# 6. Emergency integration
# ---------------------------------------------------------------------------

class TestEmergencyIntegration:
    def test_emergency_types_are_preserved(self):
        assert set(EMERGENCY_TYPES) == {
            "oxygen_leakage", "power_failure", "water_shortage",
            "solar_radiation_storm", "equipment_malfunction",
        }

    def test_selection_is_deterministic(self):
        for seed in ("1:0:0", "42:3:1", "7:2:0"):
            first = select_emergency_type("mars", seed)
            second = select_emergency_type("mars", seed)
            assert first == second
            assert first in EMERGENCY_TYPES

    def test_destination_weights_change_the_scenario_distribution(self):
        """The weighted selection follows the configured destination weights."""
        seeds = [f"seed-{index}" for index in range(2000)]
        moon_counts = {t: 0 for t in EMERGENCY_TYPES}
        mars_counts = {t: 0 for t in EMERGENCY_TYPES}
        for seed in seeds:
            moon_counts[select_emergency_type("moon", seed)] += 1
            mars_counts[select_emergency_type("mars", seed)] += 1

        def share(counts, emergency_type, destination):
            total = sum(DESTINATIONS[destination]["emergency_weights"].values())
            weight = DESTINATIONS[destination]["emergency_weights"][emergency_type]
            return counts[emergency_type] / len(seeds), weight / total

        for emergency_type in EMERGENCY_TYPES:
            moon_share, moon_expected = share(moon_counts, emergency_type, "moon")
            mars_share, mars_expected = share(mars_counts, emergency_type, "mars")
            assert moon_share == pytest.approx(moon_expected, abs=0.03)
            assert mars_share == pytest.approx(mars_expected, abs=0.03)

        # Mars weights radiation storms and dust faults higher than the Moon does,
        # so those scenarios must be more frequent in relative terms.
        assert mars_counts["solar_radiation_storm"] > moon_counts["solar_radiation_storm"]
        assert share(mars_counts, "equipment_malfunction", "mars")[0] > \
            share(moon_counts, "equipment_malfunction", "moon")[0]
        assert share(mars_counts, "water_shortage", "mars")[0] > \
            share(moon_counts, "water_shortage", "moon")[0]

    def test_triggered_emergency_uses_the_matching_type(self, ac):
        mission_id = api_mission(ac, destination="mars")
        for emergency_type in EMERGENCY_TYPES:
            resp = ac.post(f"/api/missions/{mission_id}/emergency", json={"type": emergency_type})
            assert resp.status_code == 200
            assert resp.json()["type"] == emergency_type

    def test_untyped_trigger_always_returns_a_known_type(self, ac):
        mission_id = api_mission(ac, destination="mars")
        resp = ac.post(f"/api/missions/{mission_id}/emergency", json={})
        assert resp.json()["type"] in EMERGENCY_TYPES

    def test_difficulty_scales_the_emergency_damage_in_the_api(self, ac):
        easy_id = api_mission(ac, name="Easy Emergency", difficulty="easy")
        hard_id = api_mission(ac, name="Hard Emergency", difficulty="hard")
        easy = ac.post(f"/api/missions/{easy_id}/emergency", json={"type": "oxygen_leakage"}).json()
        hard = ac.post(f"/api/missions/{hard_id}/emergency", json={"type": "oxygen_leakage"}).json()
        assert easy["effects"]["oxygen"] == pytest.approx(-15.0)
        assert hard["effects"]["oxygen"] == pytest.approx(-25.0)

    def test_automatic_alert_raises_a_matching_scenario(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="hard", astronaut_count=12, duration=365)
        emergency_type = None
        for _ in range(8):
            resp = ac.post(f"/api/missions/{mission_id}/advance")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data["emergencies"]:
                emergency_type = data["emergencies"][0]["type"]
                break
            if data["status"] != "active":
                break
        assert emergency_type in CRITICAL_RESOURCE_EMERGENCY_MAP.values()
        assert emergency_type in EMERGENCY_TYPES

    def test_automatic_alert_is_reduced_and_not_repeated(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="hard", astronaut_count=12, duration=365)
        emergency_ids = []
        for _ in range(8):
            resp = ac.post(f"/api/missions/{mission_id}/advance")
            if resp.status_code != 200:
                break
            data = resp.json()
            for emergency in data["emergencies"]:
                if emergency["id"] not in emergency_ids:
                    emergency_ids.append(emergency["id"])
            if data["status"] != "active":
                break
        assert emergency_ids, "the automatic alert rule should fire for this configuration"
        assert len(emergency_ids) == len(set(emergency_ids))
        # One automatic scenario per resource type per mission.
        types = [e["type"] for e in data["emergencies"]]
        assert len(types) == len(set(types))

    def test_automatic_alert_uses_the_reduced_effect_factor(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="medium", astronaut_count=8, duration=365)
        for _ in range(8):
            resp = ac.post(f"/api/missions/{mission_id}/advance")
            if resp.status_code != 200:
                break
            data = resp.json()
            if data["emergencies"]:
                effects = data["emergencies"][0]["effects"]
                assert effects["oxygen"] == pytest.approx(-20.0 * AUTO_EMERGENCY_EFFECT_FACTOR)
                break
            if data["status"] != "active":
                break

    def test_emergency_resolution_still_works(self, ac):
        mission_id = api_mission(ac, destination="mars")
        emergency = ac.post(f"/api/missions/{mission_id}/emergency", json={"type": "oxygen_leakage"}).json()
        ac.post(f"/api/missions/{mission_id}/actions", json={"action": "repair"})
        resp = ac.post(f"/api/missions/{mission_id}/emergencies/{emergency['id']}/resolve")
        assert resp.status_code == 200
        assert resp.json()["emergency"]["status"] == "resolved"


# ---------------------------------------------------------------------------
# 7. Lifecycle compatibility
# ---------------------------------------------------------------------------

class TestLifecycleCompatibility:
    def test_full_lifecycle(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="medium")

        assert ac.get(f"/api/missions/{mission_id}").json()["status"] == "active"

        data = ac.post(f"/api/missions/{mission_id}/advance").json()
        assert data["current_day"] == 1

        assert ac.post(f"/api/missions/{mission_id}/pause").json()["status"] == "paused"
        assert ac.post(f"/api/missions/{mission_id}/resume").json()["status"] == "active"

        assert ac.post(f"/api/missions/{mission_id}/actions", json={"action": "experiment"}).status_code == 200

        report = ac.get(f"/api/missions/{mission_id}/report").json()
        assert "score" in report and "areas_for_improvement" in report

    def test_paused_mission_does_not_consume_resources(self, ac):
        mission_id = api_mission(ac)
        ac.post(f"/api/missions/{mission_id}/pause")
        before = ac.get(f"/api/missions/{mission_id}").json()
        resp = ac.post(f"/api/missions/{mission_id}/advance")
        assert resp.status_code == 400
        after = ac.get(f"/api/missions/{mission_id}").json()
        assert after["current_day"] == before["current_day"]
        assert after["oxygen"] == before["oxygen"]

    def test_draft_mission_cannot_advance(self, ac):
        resp = ac.post("/api/missions", json={
            "name": "Draft", "destination": "moon", "astronaut_count": 2,
            "duration": 5, "difficulty": "easy",
        })
        mission_id = resp.json()["id"]
        assert ac.post(f"/api/missions/{mission_id}/advance").status_code == 400

    def test_legacy_mission_contract_is_unchanged(self, ac):
        mission_id = api_mission(ac)
        data = ac.get(f"/api/missions/{mission_id}").json()
        for key in ("id", "name", "destination", "astronaut_count", "duration", "difficulty",
                    "status", "current_day", "progress", "oxygen", "fuel", "food", "water",
                    "energy", "astronaut_health", "created_at", "updated_at", "emergencies",
                    "resolved_emergencies"):
            assert key in data, f"legacy field {key} disappeared"

    def test_resource_contract_is_unchanged(self, ac):
        mission_id = api_mission(ac)
        resources = ac.get(f"/api/missions/{mission_id}/resources").json()
        assert {r["type"] for r in resources} == set(RESOURCE_ORDER)
        for resource in resources:
            for key in ("type", "label", "percent", "current", "max", "unit", "status", "warning"):
                assert key in resource

    def test_simulation_is_deterministic(self, ac):
        first_id = api_mission(ac, name="Deterministic A")
        second_id = api_mission(ac, name="Deterministic B")
        for _ in range(4):
            first = ac.post(f"/api/missions/{first_id}/advance").json()
            second = ac.post(f"/api/missions/{second_id}/advance").json()
        for resource_type in RESOURCE_ORDER:
            assert first[resource_type] == pytest.approx(second[resource_type])
        assert first["astronaut_health"] == pytest.approx(second["astronaut_health"])


# ---------------------------------------------------------------------------
# 8. Configuration endpoints
# ---------------------------------------------------------------------------

class TestConfigurationEndpoints:
    def test_config_endpoint_lists_destinations_and_difficulties(self, ac):
        payload = ac.get("/api/config/simulation").json()
        assert set(payload["destinations"]) == {"moon", "mars"}
        assert set(payload["difficulties"]) == {"easy", "medium", "hard"}
        assert payload["reference_crew"] == REFERENCE_CREW
        assert payload["resources"]["oxygen"]["crew_share"] > 0

    def test_preview_endpoint_matches_the_live_mission(self, ac):
        preview = ac.get(
            "/api/config/simulation/preview",
            params={"destination": "mars", "difficulty": "hard", "crew": 5, "duration": 30},
        ).json()
        mission_id = api_mission(ac, destination="mars", difficulty="hard", astronaut_count=5, duration=30)
        live = ac.get(f"/api/missions/{mission_id}").json()["simulation"]
        assert preview["resources"]["oxygen"]["daily_rate"] == \
            live["resources"]["oxygen"]["daily_rate"]
        assert preview["health"]["daily_decay"] == live["health"]["daily_decay"]

    def test_preview_endpoint_rejects_unknown_values(self, ac):
        assert ac.get("/api/config/simulation/preview",
                      params={"destination": "venus", "difficulty": "easy", "crew": 2}).status_code == 422
        assert ac.get("/api/config/simulation/preview",
                      params={"destination": "moon", "difficulty": "nightmare", "crew": 2}).status_code == 422
        assert ac.get("/api/config/simulation/preview",
                      params={"destination": "moon", "difficulty": "easy", "crew": 99}).status_code == 422

    def test_profile_contains_explanations_with_real_numbers(self, ac):
        mission_id = api_mission(ac, destination="mars", difficulty="medium", astronaut_count=4)
        simulation = ac.get(f"/api/missions/{mission_id}").json()["simulation"]
        oxygen = simulation["resources"]["oxygen"]
        # 5.0 base x 1.25 crew factor x 1.1 Mars x 1.0 medium = 6.875 % per day
        assert oxygen["daily_rate"] == pytest.approx(6.875)
        assert "6.88" in oxygen["explanation"]
        assert "4 astronauts" in oxygen["explanation"]
        assert "Mars" in oxygen["explanation"]
        assert simulation["emergency_risk"]["explanation"]
        assert simulation["health"]["explanation"]
        assert simulation["emergency_risk"]["level"] in {"low", "moderate", "elevated", "high"}

    def test_emergency_risk_reacts_to_resource_pressure(self):
        relaxed = emergency_risk("moon", "medium", {"oxygen": 100.0})
        stressed = emergency_risk("moon", "medium", {"oxygen": 10.0})
        assert stressed["score"] > relaxed["score"]
        assert 0.0 <= stressed["score"] <= 1.0

    def test_mission_profile_helper_matches_api_payload(self):
        mission = make_mission(destination="mars", difficulty="hard", astronaut_count=6)
        profile = mission_profile(mission)
        assert profile["destination"]["id"] == "mars"
        assert profile["crew"]["size"] == 6
        assert profile["resources"]["oxygen"]["daily_rate"] > 0
