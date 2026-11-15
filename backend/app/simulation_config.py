"""JAMT Simulation Engine V2 — centralised simulation configuration.

This module is deliberately **data + pure functions only**.  It contains:

* ``DESTINATIONS``   – per-destination environment profile (Moon, Mars).
* ``DIFFICULTIES``   – per-difficulty operating parameters (easy / medium / hard).
* ``RESOURCE_RULES`` – per-resource consumption structure (habitat overhead vs crew demand).
* ``EMERGENCY_RULES``– per-destination emergency scenario weighting and effect scaling.

``app.simulation`` turns this configuration into mission numbers.  It never
hard-codes destination- or difficulty-specific values itself, so adding a third
destination or difficulty is a data-only change in this file.

SCIENTIFIC REFERENCES (approximate, publicly documented NASA values)
--------------------------------------------------------------------
* **Moon** – mean distance from Earth 384,400 km, one-way light time ≈ 1.3 s,
  surface gravity ≈ 0.166 g (1/6 g), day/night cycle ≈ 14 Earth days, only a
  trace exosphere instead of a breathable atmosphere.
  Sources: NASA "Moon Facts", NASA "Moon in Motion", NASA "Lunar Facts".
* **Mars** – mean distance ≈ 225 million km, one-way light time ≈ 3–22 min
  depending on planetary position, surface gravity ≈ 0.38 g, atmosphere ≈ 6 mbar
  CO2 (≈ 0.6 % of Earth's sea-level pressure), solar day (sol) ≈ 24.6 h.
  Sources: NASA "Mars Facts", NASA "Mars Exploration" communications-delay
  explainers, NASA "Mars Climate".

EDUCATIONAL ASSUMPTIONS (JAMT gameplay tuning — NOT NASA-verified values)
------------------------------------------------------------------------
Every numeric multiplier in this file that is *not* listed as a scientific
reference above is a JAMT training-game assumption.  They exist to teach the
**relative** effect of destination, crew size and difficulty, and each one is
documented in-place next to the value it controls.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Global simulation constants
# ---------------------------------------------------------------------------

#: Crew size for which the legacy flat consumption rates were calibrated.
#: ``crew_factor == 1.0`` for this crew size, so a 3-astronaut mission on a
#: "neutral" destination keeps the historic consumption numbers.
REFERENCE_CREW = 3

#: Resources tracked by the simulation, in display order.
RESOURCE_ORDER: Tuple[str, ...] = ("oxygen", "water", "food", "energy", "fuel")

#: Existing emergency taxonomy — preserved exactly as in JAMT v1.
EMERGENCY_TYPES: Tuple[str, ...] = (
    "oxygen_leakage",
    "power_failure",
    "water_shortage",
    "solar_radiation_storm",
    "equipment_malfunction",
)

#: Resource level (percent) below which a mission is considered to be in a
#: critical band.  Mirrors the frontend ``RESOURCE_THRESHOLDS.warning`` value.
CRITICAL_RESOURCE_THRESHOLD = 20.0

#: Deterministic auto-emergency rule.  When enabled, advancing a mission whose
#: resource falls into the warning band raises the matching emergency once.
#: This keeps mission progression deterministic (no dice rolls) while making
#: destination/difficulty pressure visible.
AUTO_EMERGENCY_ON_CRITICAL = True

#: Resource level (percent) that triggers the automatic emergency rule.  The
#: warning band (below 40 %) is used instead of the critical band so the crew
#: still has a chance to react before the resource runs out.
AUTO_EMERGENCY_TRIGGER_THRESHOLD = 40.0

#: Automatic alerts apply half of the scenario's normal damage.  A real fault
#: (triggered by the trainee) keeps its full effect; the automatic alert is a
#: warning that the crew can still answer.
AUTO_EMERGENCY_EFFECT_FACTOR = 0.5

#: Resource -> emergency type used by the deterministic auto-emergency rule.
CRITICAL_RESOURCE_EMERGENCY_MAP: Dict[str, str] = {
    "oxygen": "oxygen_leakage",
    "water": "water_shortage",
    "energy": "power_failure",
    "fuel": "equipment_malfunction",
}

# ---------------------------------------------------------------------------
# Resource consumption rules
# ---------------------------------------------------------------------------

# Each resource splits its daily draw into two parts:
#   * ``overhead_share`` – fixed cost of keeping the habitat alive.  It does
#     not grow with crew size (the habitat is the same size for 1 or 12 people).
#   * ``crew_share``     – cost that is genuinely driven by the number of
#     people on board, scaled linearly against ``REFERENCE_CREW``.
#
# ``crew_factor = overhead_share + crew_share * (crew_size / REFERENCE_CREW)``
#
# Because ``overhead_share + crew_share == 1.0`` for every resource, a mission
# with exactly ``REFERENCE_CREW`` astronauts keeps a factor of 1.0 and therefore
# keeps the historic consumption rate.
RESOURCE_RULES: Dict[str, Dict[str, Any]] = {
    "oxygen": {
        "label": "Oxygen",
        "base_daily_rate": 5.0,
        "overhead_share": 0.25,
        "crew_share": 0.75,
        "crew_driver": "Metabolic oxygen demand of every astronaut on board",
        "overhead_driver": "Habitat air loop, cabin pressurisation and leakage",
        "why": (
            "Oxygen is the most crew-driven resource in JAMT: three quarters of the "
            "draw is the crew breathing and the remaining quarter is the habitat "
            "air loop, which does not change with headcount."
        ),
    },
    "water": {
        "label": "Water",
        "base_daily_rate": 4.0,
        "overhead_share": 0.30,
        "crew_share": 0.70,
        "crew_driver": "Drinking, food preparation and hygiene per astronaut",
        "overhead_driver": "Recycling loop pumps, filtration and tank reserves",
        "why": (
            "Water is mostly crew demand, with a smaller fixed cost for the "
            "recycling hardware that every crew member shares."
        ),
    },
    "food": {
        "label": "Food",
        "base_daily_rate": 4.0,
        "overhead_share": 0.15,
        "crew_share": 0.85,
        "crew_driver": "Calories and meals consumed per astronaut",
        "overhead_driver": "Galley power, waste handling and packaging waste",
        "why": (
            "Food is the most strongly crew-scaled resource: almost all of it is "
            "eaten by people, while the galley overhead barely moves."
        ),
    },
    "energy": {
        "label": "Energy",
        "base_daily_rate": 4.0,
        "overhead_share": 0.60,
        "crew_share": 0.40,
        "crew_driver": "Lighting, personal electronics and cabin climate per astronaut",
        "overhead_driver": "Life-support power, batteries, thermal control and comms",
        "why": (
            "Energy is mostly habitat overhead: life support, thermal control and "
            "communications run whether one or twelve people are aboard, so crew "
            "size moves it only moderately."
        ),
    },
    "fuel": {
        "label": "Fuel",
        "base_daily_rate": 3.0,
        "overhead_share": 0.90,
        "crew_share": 0.10,
        "crew_driver": "Small per-crew share (telemetry, spares, personal equipment)",
        "overhead_driver": "Spacecraft systems, thermal control and propellant management",
        "why": (
            "Fuel models propellant and spacecraft operations, so it is the least "
            "crew-sensitive resource; adding crew barely changes the daily draw."
        ),
    },
}

# ---------------------------------------------------------------------------
# Destination profiles
# ---------------------------------------------------------------------------

DESTINATIONS: Dict[str, Dict[str, Any]] = {
    "moon": {
        "id": "moon",
        "label": "Moon",
        "tagline": "Lunar surface mission",
        "summary": (
            "Close enough for near real-time supervision, but with no atmosphere "
            "to protect the crew and an exposed surface."
        ),
        "environment": {
            "gravity_g": 0.166,
            "gravity_label": "≈ 0.166 g (1/6 of Earth)",
            "atmosphere": "Trace exosphere only — the habitat must be fully pressurised",
            "temperature": "≈ −173 °C (dark) to +127 °C (full Sun) — NASA facts (science.nasa.gov/moon/facts)",
            "day_length": "≈ 14 Earth days of sunlight per lunar cycle",
        },
        "radiation": {
            "level": "elevated",
            "label": "Elevated — no global magnetic field",
            "note": (
                "Without a magnetosphere the crew absorbs more galactic cosmic ray "
                "and solar particle radiation than on Earth, but the Moon spends "
                "about half of each cycle in shadow."
            ),
            "health_penalty_per_day": 0.3,
            "health_penalty_source": "Educational assumption (JAMT gameplay tuning)",
        },
        "communications": {
            "delay_seconds": 1.3,
            "label": "≈ 1.3 s one-way light time",
            "operational_note": "Supervision from Earth is effectively real time.",
        },
        "consumption_modifiers": {
            "oxygen": 1.0,
            "water": 1.0,
            "food": 1.0,
            "energy": 1.15,
            "fuel": 1.0,
        },
        "consumption_rationale": {
            "energy": (
                "×1.15 energy: a lunar night lasts about 14 Earth days, so the "
                "habitat carries a heavier thermal-control and lighting load."
            ),
        },
        "hazards": [
            "No breathable atmosphere outside the habitat",
            "Extreme day/night temperature swings (about 14-day cycles)",
            "Regolith dust damaging seals, filters and optics",
            "Radiation exposure without magnetic protection",
            "Sharp terrain and limited landing sites",
        ],
        "operational_challenges": [
            "Short evacuation distance — surface sorties are low latency",
            "Limited logistics: resupply windows are long",
        ],
        "emergency_weights": {
            "oxygen_leakage": 1.4,
            "power_failure": 1.0,
            "water_shortage": 0.7,
            "solar_radiation_storm": 0.8,
            "equipment_malfunction": 0.9,
        },
        "emergency_rationale": {
            "oxygen_leakage": "A pressurised habitat with many seals is the classic lunar failure mode.",
            "water_shortage": "Polar ice is reachable, so recycling pressure is lower than on Mars.",
            "solar_radiation_storm": "No magnetosphere, but the Moon spends part of each cycle in shadow.",
            "equipment_malfunction": "Dust intrusion and thermal swings stress surface equipment.",
        },
        "emergency_effect_modifiers": {
            "solar_radiation_storm": 0.8,
        },
        "base_emergency_risk": 0.35,
        "references": [
            "NASA – Moon Facts (384,400 km mean distance, 1/6 g gravity)",
            "NASA – Weather on the Moon (temperatures: +127 °C full Sun / −173 °C dark, no atmosphere)",
            "NASA – Lunar Facts (near-vacuum surface, 14-day day/night cycle)",
        ],
    },
    "mars": {
        "id": "mars",
        "label": "Mars",
        "tagline": "Red Planet expedition",
        "summary": (
            "A thin, cold atmosphere with no global magnetic field, deep-space "
            "radiation and a communications lag measured in minutes."
        ),
        "environment": {
            "gravity_g": 0.38,
            "gravity_label": "≈ 0.38 g",
            "atmosphere": "≈ 6 mbar CO2 — about 0.6 % of Earth's sea-level pressure",
            "temperature": "Average surface temperature ≈ −60 °C",
            "day_length": "≈ 24.6 h per sol",
        },
        "radiation": {
            "level": "high",
            "label": "High — thin atmosphere and no global magnetosphere",
            "note": (
                "Mars has no global magnetic field and only a thin atmosphere, so "
                "the crew receives more radiation than on the Moon during transit "
                "and on the surface."
            ),
            "health_penalty_per_day": 0.8,
            "health_penalty_source": "Educational assumption (JAMT gameplay tuning)",
        },
        "communications": {
            "delay_seconds_min": 180,
            "delay_seconds_max": 1320,
            "label": "≈ 3–22 min one-way light time (position dependent)",
            "operational_note": (
                "Every command to the crew is delayed by minutes, so procedures "
                "must be autonomous and pre-planned."
            ),
        },
        "consumption_modifiers": {
            "oxygen": 1.10,
            "water": 1.10,
            "food": 1.15,
            "energy": 1.10,
            "fuel": 1.15,
        },
        "consumption_rationale": {
            "oxygen": "×1.10 oxygen: dusty, unfiltered Martian air loads the habitat air loop.",
            "water": "×1.10 water: closed-loop recycling carries a heavier penalty than on the Moon.",
            "food": "×1.15 food: long transit plus shelf-life and resupply limits.",
            "energy": "×1.10 energy: dust on arrays and deep-night cold raise the power budget.",
            "fuel": "×1.15 fuel: longer transfer, insertion and surface ops burn more propellant.",
        },
        "hazards": [
            "Deep-space galactic cosmic ray exposure during transit",
            "Regional and global dust storms",
            "Perchlorate dust hazard for equipment and crew",
            "Communications latency of 3–22 minutes one way",
            "Longer resupply chain — parts and medicines are months away",
        ],
        "operational_challenges": [
            "Surface operations must be fully autonomous because of comms lag",
            "Landing sites are limited by terrain and dust",
        ],
        "emergency_weights": {
            "oxygen_leakage": 0.8,
            "power_failure": 1.2,
            "water_shortage": 1.3,
            "solar_radiation_storm": 2.0,
            "equipment_malfunction": 1.5,
        },
        "emergency_rationale": {
            "solar_radiation_storm": "Deep-space transit and the missing magnetosphere dominate the risk profile.",
            "water_shortage": "Closed-loop recycling has almost no resupply backup on Mars.",
            "power_failure": "Dust accumulation degrades solar arrays.",
            "equipment_malfunction": "Dust storms and a very long parts chain.",
        },
        "emergency_effect_modifiers": {
            "solar_radiation_storm": 1.25,
            "water_shortage": 1.10,
            "equipment_malfunction": 1.15,
        },
        "base_emergency_risk": 0.50,
        "references": [
            "NASA – Mars Facts (≈ 225 million km mean distance, 0.38 g gravity)",
            "NASA – Mars Exploration (3–22 min one-way communications delay)",
            "NASA – Mars Climate (≈ 6 mbar CO2 atmosphere, ≈ 24.6 h sol)",
        ],
    },
}

# ---------------------------------------------------------------------------
# Difficulty profiles
# ---------------------------------------------------------------------------

# Difficulty changes four things and nothing else, so its effect stays legible:
#   * ``consumption_multiplier``      – how fast consumables are burned.
#   * ``health_multiplier``           – how fast crew health decays.
#   * ``emergency_effect_multiplier`` – how much damage an emergency does.
#   * ``emergency_risk_multiplier``   – the mission risk indicator level.
DIFFICULTIES: Dict[str, Dict[str, Any]] = {
    "easy": {
        "id": "easy",
        "label": "Easy",
        "description": "Forgiving resource margins, rare emergencies.",
        "consumption_multiplier": 0.75,
        "health_multiplier": 0.75,
        "emergency_effect_multiplier": 0.75,
        "emergency_risk_multiplier": 0.6,
        "why": {
            "consumption_multiplier": "×0.75 consumption: a trainee mission with generous margins.",
            "health_multiplier": "×0.75 health decay: slower physiological strain for a first flight.",
            "emergency_effect_multiplier": "×0.75 emergency damage: mistakes hurt, but rarely end the mission.",
            "emergency_risk_multiplier": "×0.6 risk: fewer scenarios are flagged as likely.",
        },
    },
    "medium": {
        "id": "medium",
        "label": "Medium",
        "description": "Standard mission parameters.",
        "consumption_multiplier": 1.0,
        "health_multiplier": 1.0,
        "emergency_effect_multiplier": 1.0,
        "emergency_risk_multiplier": 1.0,
        "why": {
            "consumption_multiplier": "×1.00 consumption: the reference baseline used by JAMT v1.",
            "health_multiplier": "×1.00 health decay: baseline physiological strain.",
            "emergency_effect_multiplier": "×1.00 emergency damage: baseline scenario severity.",
            "emergency_risk_multiplier": "×1.00 risk: baseline risk assessment.",
        },
    },
    "hard": {
        "id": "hard",
        "label": "Hard",
        "description": "Tight margins, frequent emergencies.",
        "consumption_multiplier": 1.25,
        "health_multiplier": 1.25,
        "emergency_effect_multiplier": 1.25,
        "emergency_risk_multiplier": 1.5,
        "why": {
            "consumption_multiplier": "×1.25 consumption: tight reserves demand constant maintenance.",
            "health_multiplier": "×1.25 health decay: heavier strain from radiation and workload.",
            "emergency_effect_multiplier": "×1.25 emergency damage: the same fault hurts far more.",
            "emergency_risk_multiplier": "×1.5 risk: more scenarios are flagged as likely.",
        },
    },
}

DEFAULT_DESTINATION = "moon"
DEFAULT_DIFFICULTY = "medium"

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp ``value`` into the inclusive ``[low, high]`` range."""
    return max(low, min(high, value))


def _round(value: float, digits: int = 2) -> float:
    """Round for display/serialisation while keeping the value float."""
    return round(float(value), digits)


def get_destination(destination_id: Optional[str]) -> Dict[str, Any]:
    """Return the destination profile, falling back to the default profile."""
    if destination_id and destination_id in DESTINATIONS:
        return DESTINATIONS[destination_id]
    return DESTINATIONS[DEFAULT_DESTINATION]


def get_difficulty(difficulty_id: Optional[str]) -> Dict[str, Any]:
    """Return the difficulty profile, falling back to the default profile."""
    if difficulty_id and difficulty_id in DIFFICULTIES:
        return DIFFICULTIES[difficulty_id]
    return DIFFICULTIES[DEFAULT_DIFFICULTY]


def normalise_crew(crew_size: Any) -> Tuple[int, bool]:
    """Normalise a crew size.

    Returns ``(crew, is_default)``:

    * ``crew_size`` that is a positive number  -> used as-is.
    * ``crew_size`` that is ``None``/invalid   -> ``REFERENCE_CREW`` (default).
    * ``crew_size`` of ``0``                   -> ``0`` (a crew-less mission only
      pays habitat overhead, it must never divide by zero or go negative).
    """
    try:
        crew = int(crew_size)
    except (TypeError, ValueError):
        return REFERENCE_CREW, True
    if crew < 0:
        return 0, True
    return crew, False


def crew_factor(resource_type: str, crew_size: Any) -> float:
    """Crew scaling factor for one resource.

    ``overhead_share + crew_share * (crew_size / REFERENCE_CREW)``

    The factor is never negative and never below the resource's fixed overhead.
    """
    rule = RESOURCE_RULES.get(resource_type)
    if rule is None:
        return 1.0
    crew, _ = normalise_crew(crew_size)
    factor = rule["overhead_share"] + rule["crew_share"] * (crew / REFERENCE_CREW)
    return max(0.0, factor)


# ---------------------------------------------------------------------------
# Consumption / health / risk calculations
# ---------------------------------------------------------------------------


def _format_number(value: float) -> str:
    """Human friendly number formatting used inside explanation strings."""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def resource_consumption(
    resource_type: str,
    destination_id: Optional[str],
    difficulty_id: Optional[str],
    crew_size: Any,
) -> Dict[str, Any]:
    """Calculate the daily consumption of one resource.

    Formula::

        daily_rate = base_daily_rate
                   × crew_factor(crew_size)
                   × destination_modifier
                   × difficulty_multiplier
    """
    rule = RESOURCE_RULES[resource_type]
    destination = get_destination(destination_id)
    difficulty = get_difficulty(difficulty_id)
    crew, crew_is_default = normalise_crew(crew_size)

    factor = crew_factor(resource_type, crew)
    dest_modifier = float(destination["consumption_modifiers"].get(resource_type, 1.0))
    diff_multiplier = float(difficulty["consumption_multiplier"])
    daily_rate = float(rule["base_daily_rate"]) * factor * dest_modifier * diff_multiplier
    daily_rate = max(0.0, daily_rate)

    destination_note = destination.get("consumption_rationale", {}).get(resource_type)
    driver_parts = [
        f"{int(round(rule['crew_share'] * 100))}% crew-driven ({rule['crew_driver'].lower()})",
        f"{int(round(rule['overhead_share'] * 100))}% habitat overhead ({rule['overhead_driver'].lower()})",
    ]
    explanation = (
        f"{rule['label']} draw is {' and '.join(driver_parts)}. "
        f"{_format_number(rule['base_daily_rate'])}%/day base"
        f" × {_format_number(factor)} crew factor"
        f" ({crew} astronaut{'s' if crew != 1 else ''}"
        f"{' vs ' + str(REFERENCE_CREW) + ' reference crew' if crew != REFERENCE_CREW else ''})"
        f" × {_format_number(dest_modifier)} {destination['label']} factor"
        f" × {_format_number(diff_multiplier)} {difficulty['label']} difficulty"
        f" = {_format_number(daily_rate)}% per day."
    )
    if destination_note:
        explanation += f" {destination_note}"
    if crew_is_default:
        explanation += " Crew size is missing, so the 3-astronaut reference crew was used."

    return {
        "type": resource_type,
        "label": rule["label"],
        "base_daily_rate": float(rule["base_daily_rate"]),
        "crew_factor": _round(factor, 4),
        "destination_multiplier": _round(dest_modifier, 4),
        "difficulty_multiplier": _round(diff_multiplier, 4),
        "daily_rate": _round(daily_rate, 3),
        "crew_driver": rule["crew_driver"],
        "overhead_driver": rule["overhead_driver"],
        "why": rule["why"],
        "explanation": explanation,
    }


def health_decay(destination_id: Optional[str], difficulty_id: Optional[str]) -> Dict[str, Any]:
    """Calculate the daily crew health decay.

    Formula::

        daily_decay = (base_decay + destination_radiation_penalty)
                    × difficulty_health_multiplier

    The radiation penalty is an educational assumption that reflects how much
    harder the destination environment works on the crew.
    """
    destination = get_destination(destination_id)
    difficulty = get_difficulty(difficulty_id)
    base_decay = 2.0
    radiation_penalty = float(destination["radiation"]["health_penalty_per_day"])
    diff_multiplier = float(difficulty["health_multiplier"])
    daily_decay = max(0.0, (base_decay + radiation_penalty) * diff_multiplier)

    explanation = (
        f"Crew health decays {base_decay:.1f} point/day from the training workload"
        f" plus {_format_number(radiation_penalty)} point/day of "
        f"{destination['radiation']['label'].split('—')[0].strip().lower()} radiation strain"
        f" ({destination['radiation']['health_penalty_source']}),"
        f" × {_format_number(diff_multiplier)} {difficulty['label']} difficulty"
        f" = {_format_number(daily_decay)} points per day."
    )
    return {
        "base_daily_decay": base_decay,
        "radiation_penalty": _round(radiation_penalty, 3),
        "difficulty_multiplier": _round(diff_multiplier, 4),
        "daily_decay": _round(daily_decay, 3),
        "explanation": explanation,
    }


def emergency_risk(
    destination_id: Optional[str],
    difficulty_id: Optional[str],
    resource_levels: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Deterministic mission risk indicator (no dice rolls involved).

    ``score = destination_base_risk × difficulty_risk_multiplier (+ resource stress)``
    """
    destination = get_destination(destination_id)
    difficulty = get_difficulty(difficulty_id)
    base = float(destination["base_emergency_risk"])
    diff_multiplier = float(difficulty["emergency_risk_multiplier"])
    score = base * diff_multiplier
    stress_note = ""

    levels = resource_levels or {}
    values = [float(v) for v in levels.values() if v is not None]
    if values:
        lowest = min(values)
        if lowest < CRITICAL_RESOURCE_THRESHOLD:
            score += 0.20
            stress_note = " A resource is in the critical band, which raises the risk level."
        elif lowest < 40:
            score += 0.08
            stress_note = " A resource is running low, which slightly raises the risk level."

    score = clamp(score, 0.0, 1.0)
    if score < 0.30:
        level = "low"
    elif score < 0.50:
        level = "moderate"
    elif score < 0.70:
        level = "elevated"
    else:
        level = "high"

    explanation = (
        f"{destination['label']} baseline risk {_format_number(base)}"
        f" × {_format_number(diff_multiplier)} {difficulty['label']} difficulty"
        f" = {_format_number(score)} → {level} risk."
        f"{stress_note}"
    )
    return {
        "level": level,
        "score": _round(score, 3),
        "base_risk": _round(base, 3),
        "difficulty_multiplier": _round(diff_multiplier, 4),
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Emergency scenarios
# ---------------------------------------------------------------------------


def _stable_seed_int(seed: str) -> int:
    """Deterministic, process independent integer seed for a string."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def select_emergency_type(
    destination_id: Optional[str],
    seed: str,
    allowed_types: Sequence[str] = EMERGENCY_TYPES,
) -> str:
    """Deterministically pick an emergency type for a mission.

    The selection is a **weighted** choice: every destination defines a weight
    per emergency type describing how relevant that scenario is there.  The
    weight table is turned into a cumulative distribution and the seed (a
    stable SHA-256 based integer, never Python's salted ``hash()``) selects the
    bucket.  The same mission state therefore always produces the same
    scenario, which keeps the system reproducible and testable.
    """
    destination = get_destination(destination_id)
    weights = destination["emergency_weights"]
    candidates: List[Tuple[str, float]] = [
        (etype, max(0.01, float(weights.get(etype, 1.0))))
        for etype in allowed_types
    ]
    total = sum(weight for _, weight in candidates)
    if total <= 0:
        return allowed_types[0]

    position = (_stable_seed_int(f"{destination['id']}:{seed}") % 1_000_000) / 1_000_000 * total
    cumulative = 0.0
    for etype, weight in candidates:
        cumulative += weight
        if position < cumulative:
            return etype
    return candidates[-1][0]


def scale_emergency_effects(
    effects: Dict[str, float],
    emergency_type: str,
    destination_id: Optional[str],
    difficulty_id: Optional[str],
    effect_factor: float = 1.0,
) -> Dict[str, float]:
    """Scale the damage of an emergency by difficulty and destination.

    ``scaled = base_effect × difficulty_emergency_multiplier
               × destination_modifier × effect_factor``

    Both multipliers are documented in ``DIFFICULTIES`` and ``DESTINATIONS``.
    ``effect_factor`` is used by the automatic alert rule, which applies a
    reduced severity so the crew can still answer the situation.
    """
    destination = get_destination(destination_id)
    difficulty = get_difficulty(difficulty_id)
    diff_multiplier = float(difficulty["emergency_effect_multiplier"])
    dest_modifier = float(destination.get("emergency_effect_modifiers", {}).get(emergency_type, 1.0))
    multiplier = diff_multiplier * dest_modifier * float(effect_factor)
    scaled: Dict[str, float] = {}
    for field, value in (effects or {}).items():
        scaled[field] = _round(float(value) * multiplier, 4)
    return scaled


# ---------------------------------------------------------------------------
# Public payloads (API + UI)
# ---------------------------------------------------------------------------


def destination_public_view(destination: Dict[str, Any]) -> Dict[str, Any]:
    """Compact, UI friendly view of a destination profile."""
    return {
        "id": destination["id"],
        "label": destination["label"],
        "tagline": destination["tagline"],
        "summary": destination["summary"],
        "environment": destination["environment"],
        "radiation": {
            "level": destination["radiation"]["level"],
            "label": destination["radiation"]["label"],
            "note": destination["radiation"]["note"],
            "health_penalty_per_day": destination["radiation"]["health_penalty_per_day"],
        },
        "communications": destination["communications"],
        "hazards": list(destination["hazards"]),
        "operational_challenges": list(destination["operational_challenges"]),
        "consumption_modifiers": dict(destination["consumption_modifiers"]),
        "emergency_weights": dict(destination["emergency_weights"]),
        "base_emergency_risk": destination["base_emergency_risk"],
        "references": list(destination["references"]),
    }


def difficulty_public_view(difficulty: Dict[str, Any]) -> Dict[str, Any]:
    """Compact, UI friendly view of a difficulty profile."""
    return {
        "id": difficulty["id"],
        "label": difficulty["label"],
        "description": difficulty["description"],
        "consumption_multiplier": difficulty["consumption_multiplier"],
        "health_multiplier": difficulty["health_multiplier"],
        "emergency_effect_multiplier": difficulty["emergency_effect_multiplier"],
        "emergency_risk_multiplier": difficulty["emergency_risk_multiplier"],
        "why": dict(difficulty["why"]),
    }


def resource_public_view(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Compact, UI friendly view of a consumption rule."""
    return {
        "type": rule.get("type", ""),
        "label": rule["label"],
        "base_daily_rate": rule["base_daily_rate"],
        "overhead_share": rule["overhead_share"],
        "crew_share": rule["crew_share"],
        "crew_driver": rule["crew_driver"],
        "overhead_driver": rule["overhead_driver"],
        "why": rule["why"],
    }


def simulation_config_payload() -> Dict[str, Any]:
    """Full configuration payload served by ``GET /api/config/simulation``."""
    return {
        "reference_crew": REFERENCE_CREW,
        "resource_order": list(RESOURCE_ORDER),
        "critical_resource_threshold": CRITICAL_RESOURCE_THRESHOLD,
        "emergency_types": list(EMERGENCY_TYPES),
        "destinations": {
            key: destination_public_view(value) for key, value in DESTINATIONS.items()
        },
        "difficulties": {
            key: difficulty_public_view(value) for key, value in DIFFICULTIES.items()
        },
        "resources": {
            key: {
                "type": key,
                "label": value["label"],
                "base_daily_rate": value["base_daily_rate"],
                "overhead_share": value["overhead_share"],
                "crew_share": value["crew_share"],
                "crew_driver": value["crew_driver"],
                "overhead_driver": value["overhead_driver"],
                "why": value["why"],
            }
            for key, value in RESOURCE_RULES.items()
        },
        "notes": {
            "scientific_references": "Destination characteristics cite publicly documented NASA values.",
            "educational_assumptions": (
                "Consumption multipliers, crew-share splits, radiation penalties and "
                "emergency weights are JAMT training-game assumptions, not NASA-verified values."
            ),
        },
    }


def build_profile(
    destination_id: Optional[str],
    difficulty_id: Optional[str],
    crew_size: Any,
    current_resources: Optional[Dict[str, float]] = None,
    current_day: int = 0,
    duration: int = 0,
) -> Dict[str, Any]:
    """Build the full simulation profile used by the API and the dashboard.

    ``current_resources`` (percent values per resource) is optional; when it is
    supplied the profile also reports how many days of supplies remain and
    whether the mission duration is still achievable at the current rate.
    """
    destination = get_destination(destination_id)
    difficulty = get_difficulty(difficulty_id)
    crew, crew_is_default = normalise_crew(crew_size)

    resources: Dict[str, Any] = {}
    for resource_type in RESOURCE_ORDER:
        info = resource_consumption(resource_type, destination["id"], difficulty["id"], crew)
        if current_resources and resource_type in current_resources:
            level = float(current_resources.get(resource_type) or 0.0)
            rate = float(info["daily_rate"])
            days_left = (level / rate) if rate > 0 else None
            projected_day = (current_day + days_left) if days_left is not None else None
            remaining_days = max(0, int(duration or 0) - int(current_day or 0))
            sufficient = None
            if days_left is not None and remaining_days:
                sufficient = days_left >= remaining_days
            info = {
                **info,
                "current_level": _round(level, 2),
                "estimated_days_remaining": _round(days_left, 1) if days_left is not None else None,
                "projected_exhaustion_day": _round(projected_day, 1) if projected_day is not None else None,
                "sufficient_for_remaining_mission": sufficient,
            }
        resources[resource_type] = info

    health = health_decay(destination["id"], difficulty["id"])
    levels = {key: value.get("current_level") for key, value in resources.items() if "current_level" in value}
    risk = emergency_risk(destination["id"], difficulty["id"], levels or None)

    return {
        "destination": destination_public_view(destination),
        "difficulty": difficulty_public_view(difficulty),
        "crew": {
            "size": crew,
            "reference_crew": REFERENCE_CREW,
            "is_default": crew_is_default,
        },
        "resources": resources,
        "health": health,
        "emergency_risk": risk,
        "emergency_types": list(EMERGENCY_TYPES),
    }
