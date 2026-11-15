"""JAMT mission simulation mechanics (Simulation Engine V2).

The functions in this module are intentionally small and pure with respect to
the mission object: they read the mission's destination, difficulty and crew
size, ask :mod:`app.simulation_config` for the matching parameters and apply
the result.  No destination- or difficulty-specific value is hard-coded here.

Public contract (unchanged from JAMT v1):

* ``apply_daily_consumption(mission)`` – consume one day of supplies.
* ``apply_action(mission, action)``    – apply an astronaut action.
* ``evaluate_mission_status(mission)`  – draft/active/paused/completed/failed.

Health relationship (important, see Phase 1 report):

* ``MissionTable.astronaut_health`` is the **authoritative crew-average** health.
* ``AstronautTable.health`` is the health of one crew member.
* Both are moved by the **same delta** every day and every action, so they
  stay in step.  Individual crew rows are clamped on their own, so at the
  extreme ends (0 % / 100 %) a single crew member can sit slightly apart from
  the crew average.  Redesigning that relationship (for example deriving the
  mission value from the crew rows) needs an approved data-model change and is
  deliberately deferred.
"""

from typing import Any, Dict, Literal, Optional

from .simulation_config import (
    RESOURCE_ORDER,
    build_profile,
    health_decay,
    resource_consumption,
)

# Configurable consumption rates per day (percentage points).
# NOTE: these are the *base* rates for the reference crew of 3 astronauts.
# The effective daily rate is calculated in `daily_plan()` from the mission's
# destination, difficulty and crew size — see `app.simulation_config`.
DAILY_CONSUMPTION = {
    "oxygen": 5.0,
    "fuel": 3.0,
    "food": 4.0,
    "water": 4.0,
    "energy": 4.0,
    "astronaut_health": 2.0,
}

# Action effects (percentage changes)
ACTION_EFFECTS = {
    "repair": {"fuel": -10.0, "oxygen": -5.0, "astronaut_health": -5.0},
    "rest": {"astronaut_health": +10.0},
    "experiment": {"progress": +15.0, "oxygen": -8.0, "fuel": -5.0, "food": -6.0, "water": -6.0},
    "wait": {},  # no extra effect beyond daily consumption
}


def _get(mission, attribute: str, default: Any = None) -> Any:
    """Safe attribute read that also works with dict-like mission objects."""
    if isinstance(mission, dict):
        value = mission.get(attribute, default)
    else:
        value = getattr(mission, attribute, default)
    return default if value is None else value


def daily_plan(mission) -> Dict[str, Any]:
    """Return the calculated consumption plan for one mission day.

    The plan is the single source of truth for the numbers applied by
    :func:`apply_daily_consumption`, so the mission row and the individual
    astronaut rows are always updated with exactly the same values.
    """
    destination = _get(mission, "destination")
    difficulty = _get(mission, "difficulty")
    crew = _get(mission, "astronaut_count", 0)

    resources: Dict[str, Any] = {}
    for resource_type in RESOURCE_ORDER:
        resources[resource_type] = resource_consumption(
            resource_type, destination, difficulty, crew
        )

    health = health_decay(destination, difficulty)

    return {
        "resources": resources,
        "health": health,
        "destination": destination,
        "difficulty": difficulty,
        "crew": crew,
    }


def apply_daily_consumption(mission):
    """Consume resources for a day and update health and progress."""
    plan = daily_plan(mission)

    for resource_type, info in plan["resources"].items():
        current = float(_get(mission, resource_type, 100.0) or 0.0)
        setattr(mission, resource_type, max(current - float(info["daily_rate"]), 0.0))

    current_health = float(_get(mission, "astronaut_health", 100.0) or 0.0)
    mission.astronaut_health = max(current_health - float(plan["health"]["daily_decay"]), 0.0)

    # Advance progress without overwriting progress gained or lost elsewhere.
    duration = _get(mission, "duration", 0)
    if duration:
        try:
            duration_value = float(duration)
        except (TypeError, ValueError):
            duration_value = 0.0
        if duration_value > 0:
            current_progress = float(_get(mission, "progress", 0.0) or 0.0)
            mission.progress = max(min(current_progress + (100.0 / duration_value), 100.0), 0.0)
    return mission


def apply_action(mission, action: Literal["repair", "rest", "experiment", "wait"]):
    """Apply immediate effects of an astronaut action."""
    effects = ACTION_EFFECTS.get(action, {})
    for field, delta in effects.items():
        # Clamp each resource between 0 and 100
        current = float(_get(mission, field, 100.0) or 0.0)
        new_val = max(min(current + delta, 100.0), 0.0)
        setattr(mission, field, new_val)
    return mission


def evaluate_mission_status(mission):
    """Update mission.status based on resource health and progress."""
    # Failure if any critical resource or health depletes.
    # Unknown (NULL) values are treated as "not depleted" so a legacy row with a
    # missing value can never fail a mission by accident.
    depleted = any(
        float(_get(mission, resource_type, 100.0) or 0.0) <= 0
        for resource_type in RESOURCE_ORDER
    )
    if depleted or float(_get(mission, "astronaut_health", 100.0) or 0.0) <= 0:
        mission.status = "failed"
    # Completion if duration reached or progress 100%
    elif float(_get(mission, "current_day", 0) or 0) >= float(_get(mission, "duration", 0) or 0) or \
            float(_get(mission, "progress", 0.0) or 0.0) >= 100:
        mission.status = "completed"
    return mission


def mission_profile(mission, current_resources: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Build the simulation profile for a mission (API + dashboard payload).

    ``current_resources`` defaults to the mission's own resource levels.
    """
    resources = current_resources
    if resources is None:
        resources = {
            resource_type: float(_get(mission, resource_type, 100.0) or 0.0)
            for resource_type in RESOURCE_ORDER
        }
    return build_profile(
        destination_id=_get(mission, "destination"),
        difficulty_id=_get(mission, "difficulty"),
        crew_size=_get(mission, "astronaut_count", 0),
        current_resources=resources,
        current_day=int(_get(mission, "current_day", 0) or 0),
        duration=int(_get(mission, "duration", 0) or 0),
    )
