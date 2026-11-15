from datetime import datetime, timezone
from typing import Optional, List, Literal, Dict, Any
import json
import os
import uuid

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import create_engine, BigInteger, Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from .simulation import (
    apply_daily_consumption,
    apply_action,
    evaluate_mission_status,
    daily_plan,
    mission_profile,
)
from .simulation_config import (
    AUTO_EMERGENCY_EFFECT_FACTOR,
    AUTO_EMERGENCY_ON_CRITICAL,
    AUTO_EMERGENCY_TRIGGER_THRESHOLD,
    CRITICAL_RESOURCE_EMERGENCY_MAP,
    DESTINATIONS,
    DIFFICULTIES,
    EMERGENCY_TYPES,
    RESOURCE_ORDER,
    build_profile,
    scale_emergency_effects,
    select_emergency_type,
    simulation_config_payload,
)
from .ai.agent import _call_llm, run_agent
from .ai.config import get_config

app = FastAPI(title="JAMT API", version="0.2.0")

_REPORT_FEEDBACK_CACHE: Dict[tuple, str] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# The database location can be overridden with JAMT_DATABASE_URL so that
# demonstrations and automated tests never have to touch the project's
# jamt.db.  The default is unchanged: ./jamt.db next to the backend package.
# Use a Neon PostgreSQL connection string in production, e.g.
#   postgresql://user:password@host-pooler.region.aws.neon.tech/dbname?sslmode=require
DATABASE_URL = os.getenv("JAMT_DATABASE_URL", "sqlite:///./jamt.db")

# Some providers (e.g. Neon, Heroku) still hand out "postgres://" URLs; SQLAlchemy 2
# only understands "postgresql://", so normalise the scheme. Plain "postgresql://"
# is then pinned to psycopg2 — the driver that requirements.txt installs — so the
# deployment does not depend on whichever driver happens to be the default.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]

IS_SQLITE = DATABASE_URL.startswith("sqlite")

# SQLite needs check_same_thread=False for FastAPI's thread pool. PostgreSQL
# must not receive that argument, so it is applied only for SQLite.
# pool_pre_ping verifies pooled connections before use and pool_recycle retires
# them before Neon's side drops them, which keeps Vercel serverless functions
# from holding half-open sockets.
if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

Base = declarative_base()


class MissionTable(Base):
    __tablename__ = "missions"

    # BigInteger: mission ids are generated from uuid4().int & (10**10 - 1) and can
    # therefore exceed PostgreSQL's 32-bit INTEGER range. SQLite stores integers
    # dynamically, so this changes nothing locally.
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    astronaut_count = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    difficulty = Column(String, nullable=False)
    status = Column(String, default="draft")
    current_day = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    oxygen = Column(Float, default=100.0)
    fuel = Column(Float, default=100.0)
    food = Column(Float, default=100.0)
    water = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    astronaut_health = Column(Float, default=100.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AstronautTable(Base):
    __tablename__ = "astronauts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mission_id = Column(BigInteger, ForeignKey("missions.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    health = Column(Float, default=100.0)
    heart_rate = Column(Integer, default=72)
    oxygen_saturation = Column(Integer, default=98)
    body_temperature = Column(Float, default=36.5)
    health_status = Column(String, default="good")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmergencyTable(Base):
    __tablename__ = "emergencies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mission_id = Column(BigInteger, ForeignKey("missions.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    severity = Column(String, default="medium")
    description = Column(Text, default="")
    status = Column(String, default="active")
    mission_day = Column(Integer, default=0)
    effects = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


class MissionEventTable(Base):
    __tablename__ = "mission_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mission_id = Column(BigInteger, ForeignKey("missions.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, default="{}")
    mission_day = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    destination: str = Field(..., pattern="^(moon|mars)$")
    astronaut_count: int = Field(..., ge=1, le=12)
    duration: int = Field(..., ge=1, le=365)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        if isinstance(data, dict):
            if "destination" in data and isinstance(data["destination"], str):
                data["destination"] = data["destination"].strip().lower()
            if "difficulty" in data and isinstance(data["difficulty"], str):
                data["difficulty"] = data["difficulty"].strip().lower()
        return data


class MissionRead(BaseModel):
    id: int
    name: str
    destination: str
    astronaut_count: int
    duration: int
    difficulty: str
    status: str
    current_day: int
    progress: float
    oxygen: float
    fuel: float
    food: float
    water: float
    energy: float
    astronaut_health: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    emergencies: Optional[List[Dict[str, Any]]] = None
    resolved_emergencies: Optional[List[Dict[str, Any]]] = None
    # Additive field (Phase 1): destination / difficulty / crew simulation profile.
    simulation: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class ActionRequest(BaseModel):
    action: Optional[str] = None
    action_type: Optional[str] = None
    type: Optional[str] = None

    @model_validator(mode="after")
    def _normalize(self):
        value = self.action or self.action_type or self.type
        if not value:
            raise ValueError("action is required")
        action_map = {
            "activate_backup_o2": "repair",
            "isolate_leak_sector": "repair",
            "seal_habitat_breach": "repair",
            "backup_fuel_cells": "repair",
            "shed_non_essential_load": "repair",
            "storm_shelter": "rest",
            "medical_treatment": "rest",
        }
        value = action_map.get(value, value)
        if value not in {"repair", "rest", "experiment", "wait"}:
            raise ValueError("invalid action")
        self.action = value
        return self


class EmergencyTriggerRequest(BaseModel):
    type: Optional[str] = None
    emergency_type: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def _normalize(self):
        if self.emergency_type and not self.type:
            self.type = self.emergency_type
        if self.type == "oxygen_leak":
            self.type = "oxygen_leakage"
        elif self.type == "solar_storm":
            self.type = "solar_radiation_storm"
        return self


class AgentChatRequest(BaseModel):
    mission_id: Optional[int] = None
    message: str = Field(..., min_length=1)


class AgentChatResponse(BaseModel):
    response: str
    tools_used: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []
    suggested_actions: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _health_status(value: float) -> str:
    if value >= 80:
        return "good"
    if value >= 60:
        return "stable"
    if value >= 40:
        return "warning"
    return "critical"


def create_astronauts(db: Session, mission: MissionTable) -> None:
    preset_names = ["Alex Carter", "Sarah Mitchell", "David Kim"]
    for i in range(mission.astronaut_count):
        name = preset_names[i] if i < len(preset_names) else f"Astronaut {i + 1}"
        db.add(AstronautTable(
            mission_id=mission.id,
            name=name,
            health=float(mission.astronaut_health if mission.astronaut_health is not None else 100.0),
            heart_rate=72 if i == 0 else (68 if i == 1 else 95),
            oxygen_saturation=98,
            body_temperature=36.5,
            health_status="good",
        ))


def log_event(db: Session, mission_id: int, event_type: str, message: str,
              details: Optional[Dict[str, Any]] = None, day: int = 0) -> None:
    db.add(MissionEventTable(
        mission_id=mission_id,
        event_type=event_type,
        message=message,
        details=json.dumps(details or {}),
        mission_day=day,
    ))


EMERGENCY_DEFAULTS: Dict[str, tuple] = {
    "oxygen_leakage": ("critical", "Oxygen leakage detected in the habitat module.", {"oxygen": -20.0, "astronaut_health": -5.0}),
    "power_failure": ("high", "Power failure affecting core systems.", {"energy": -25.0, "fuel": -10.0}),
    "water_shortage": ("high", "Water recycling system malfunction causing shortage.", {"water": -25.0, "astronaut_health": -3.0}),
    "solar_radiation_storm": ("critical", "Solar radiation storm increasing crew exposure.", {"astronaut_health": -15.0, "oxygen": -5.0}),
    "equipment_malfunction": ("medium", "Critical equipment malfunction reported.", {"fuel": -10.0, "energy": -10.0, "progress": -5.0}),
}

RESOLUTION_RULES: Dict[str, str] = {
    "oxygen_leakage": "repair",
    "power_failure": "repair",
    "water_shortage": "repair",
    "solar_radiation_storm": "rest",
    "equipment_malfunction": "repair",
}
RESOLUTION_HINTS: Dict[str, str] = {
    "oxygen_leakage": "Execute a repair action to restore life-support systems.",
    "power_failure": "Execute a repair action to restore power systems.",
    "water_shortage": "Execute a repair action to restore the water recycling system.",
    "solar_radiation_storm": "Execute a rest action to reduce exposure and recover.",
    "equipment_malfunction": "Execute a repair action to fix the malfunctioning equipment.",
}


def _apply_emergency_effects(mission: MissionTable, astronauts: List[AstronautTable], effects: Dict[str, float]) -> None:
    for field, delta in effects.items():
        if hasattr(mission, field):
            current = getattr(mission, field)
            if current is None:
                current = 0.0
            setattr(mission, field, _clamp(float(current) + float(delta)))
    if "astronaut_health" in effects:
        delta = float(effects["astronaut_health"])
        for astronaut in astronauts:
            astronaut.health = _clamp(astronaut.health + delta)
            astronaut.health_status = _health_status(astronaut.health)
            astronaut.heart_rate = int(_clamp(72 + (100 - astronaut.health) * 0.5, 40, 180))
            astronaut.oxygen_saturation = int(_clamp(90 + astronaut.health * 0.08, 70, 100))
            astronaut.body_temperature = round(_clamp(36.5 + (100 - astronaut.health) * 0.02, 35.0, 40.0), 1)


def trigger_emergency_for_mission(db: Session, mission: MissionTable,
                                 requested_type: Optional[str] = None,
                                 severity: Optional[str] = None,
                                 description: Optional[str] = None,
                                 source: str = "manual",
                                 effect_factor: float = 1.0) -> EmergencyTable:
    """Raise an emergency for a mission.

    * When no (or an unknown) type is requested the scenario is chosen with a
      **deterministic weighted selection**: each destination defines how
      relevant every scenario is there, and the mission state selects the
      bucket.  The same mission state always produces the same scenario.
    * The damage of the scenario is scaled by the mission difficulty and by
      destination specific factors (see ``app.simulation_config``).
    """
    astronauts = db.query(AstronautTable).filter(AstronautTable.mission_id == mission.id).all()
    existing_count = db.query(EmergencyTable).filter(EmergencyTable.mission_id == mission.id).count()

    if requested_type and requested_type in EMERGENCY_DEFAULTS:
        emergency_type = requested_type
        selection_reason = "requested"
    else:
        emergency_type = select_emergency_type(
            mission.destination,
            seed=f"{mission.id}:{mission.current_day}:{existing_count}",
            allowed_types=EMERGENCY_TYPES,
        )
        selection_reason = "destination_weighted"

    default_severity, default_description, base_effects = EMERGENCY_DEFAULTS[emergency_type]
    final_severity = severity or default_severity
    final_description = description or default_description

    effects = scale_emergency_effects(
        base_effects,
        emergency_type,
        mission.destination,
        mission.difficulty,
        effect_factor=effect_factor,
    )

    _apply_emergency_effects(mission, astronauts, effects)
    evaluate_mission_status(mission)

    emergency = EmergencyTable(
        mission_id=mission.id,
        type=emergency_type,
        severity=final_severity,
        description=final_description,
        status="active",
        mission_day=mission.current_day,
        effects=json.dumps(effects),
    )
    db.add(emergency)
    db.flush()

    log_event(
        db,
        mission.id,
        "emergency_triggered",
        f"Emergency triggered: {emergency_type.replace('_', ' ')}",
        {
            "emergency_id": emergency.id,
            "type": emergency_type,
            "severity": final_severity,
            "effects": effects,
            "base_effects": base_effects,
            "selection": selection_reason,
            "source": source,
        },
        mission.current_day,
    )
    return emergency


def maybe_trigger_critical_emergency(db: Session, mission: MissionTable) -> Optional[EmergencyTable]:
    """Deterministic emergency rule driven by resource state.

    When a resource falls into the warning band (below 40 %) the matching
    scenario is raised once — no random dice rolls are involved, so mission
    progression stays reproducible.  Rules:

    * at most one automatic emergency per day,
    * never while another emergency is still active,
    * never twice for the same scenario in the same mission,
    * reduced severity (``AUTO_EMERGENCY_EFFECT_FACTOR``) so the crew can act.
    """
    if not AUTO_EMERGENCY_ON_CRITICAL:
        return None
    if mission.status != "active":
        return None

    active = db.query(EmergencyTable).filter(
        EmergencyTable.mission_id == mission.id,
        EmergencyTable.status == "active",
    ).count()
    if active:
        return None

    existing_types = {
        row.type for row in db.query(EmergencyTable).filter(
            EmergencyTable.mission_id == mission.id
        ).all()
    }

    for resource_type in RESOURCE_ORDER:
        level = float(getattr(mission, resource_type, 100.0) or 0.0)
        if level >= AUTO_EMERGENCY_TRIGGER_THRESHOLD:
            continue
        emergency_type = CRITICAL_RESOURCE_EMERGENCY_MAP.get(resource_type)
        if not emergency_type or emergency_type in existing_types:
            continue
        description = (
            f"Automatic alert: {resource_type} reserves fell to {level:.1f}% "
            f"(below the {AUTO_EMERGENCY_TRIGGER_THRESHOLD:.0f}% warning band)."
        )
        return trigger_emergency_for_mission(
            db,
            mission,
            requested_type=emergency_type,
            description=description,
            source="automatic",
            effect_factor=AUTO_EMERGENCY_EFFECT_FACTOR,
        )
    return None


def _update_astronauts_for_health_delta(db: Session, mission_id: int, delta: float) -> None:
    astronauts = db.query(AstronautTable).filter(AstronautTable.mission_id == mission_id).all()
    for astronaut in astronauts:
        astronaut.health = _clamp(astronaut.health + delta)
        astronaut.health_status = _health_status(astronaut.health)
        astronaut.heart_rate = int(_clamp(72 + (100 - astronaut.health) * 0.5, 40, 180))
        astronaut.oxygen_saturation = int(_clamp(90 + astronaut.health * 0.08, 70, 100))
        astronaut.body_temperature = round(_clamp(36.5 + (100 - astronaut.health) * 0.02, 35.0, 40.0), 1)


def emergency_to_dict(emergency: EmergencyTable) -> Dict[str, Any]:
    try:
        effects = json.loads(emergency.effects or "{}")
    except (json.JSONDecodeError, TypeError):
        effects = {}
    actions = []
    if emergency.type == "oxygen_leakage":
        actions = ["repair", "rest"]
    elif emergency.type == "power_failure":
        actions = ["repair", "wait"]
    elif emergency.type == "water_shortage":
        actions = ["repair", "rest"]
    elif emergency.type == "solar_radiation_storm":
        actions = ["rest", "experiment"]
    else:
        actions = ["repair", "rest", "experiment"]
    required_action = RESOLUTION_RULES.get(emergency.type, "repair")
    resolution_hint = RESOLUTION_HINTS.get(emergency.type, f"Execute a '{required_action}' action to resolve this emergency.")
    return {
        "id": emergency.id,
        "type": emergency.type,
        "severity": emergency.severity,
        "description": emergency.description,
        "status": emergency.status,
        "mission_day": emergency.mission_day,
        "created_at": emergency.created_at.isoformat() if emergency.created_at else None,
        "resolved_at": emergency.resolved_at.isoformat() if emergency.resolved_at else None,
        "actions": actions,
        "effects": effects,
        "required_action": required_action,
        "resolution_hint": resolution_hint,
    }


def astronaut_to_dict(astronaut: AstronautTable) -> Dict[str, Any]:
    return {
        "id": astronaut.id,
        "name": astronaut.name,
        "health": astronaut.health,
        "heart_rate": astronaut.heart_rate,
        "heartRate": astronaut.heart_rate,
        "oxygen_saturation": astronaut.oxygen_saturation,
        "oxygenSaturation": astronaut.oxygen_saturation,
        "body_temperature": astronaut.body_temperature,
        "bodyTemperature": astronaut.body_temperature,
        "health_status": astronaut.health_status,
        "healthStatus": astronaut.health_status,
        "status": astronaut.health_status,
    }


def event_to_dict(event: MissionEventTable) -> Dict[str, Any]:
    return {
        "id": event.id,
        "message": event.message,
        "type": event.event_type,
        "event_type": event.event_type,
        "timestamp": event.created_at.isoformat() if event.created_at else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "mission_day": event.mission_day,
        "details": event.details,
    }


def build_resources(mission: MissionTable) -> List[Dict[str, Any]]:
    result = []
    labels = {
        "oxygen": "Oxygen",
        "water": "Water",
        "food": "Food",
        "energy": "Energy",
        "fuel": "Fuel",
    }
    plan = daily_plan(mission)
    for resource_type in ["oxygen", "water", "food", "energy", "fuel"]:
        value = getattr(mission, resource_type, 100.0)
        percent = _clamp(float(value if value is not None else 100.0))
        if percent < 20:
            status = "critical"
            warning = f"{labels[resource_type]} critically low"
        elif percent < 40:
            status = "warning"
            warning = None
        else:
            status = "normal"
            warning = None
        info = plan["resources"].get(resource_type, {})
        result.append({
            "type": resource_type,
            "label": labels[resource_type],
            "percent": percent,
            "current": percent,
            "max": 100.0,
            "unit": "%",
            "status": status,
            "warning": warning,
            # Additive fields (Phase 1): why the level moves at the rate it does.
            "daily_rate": info.get("daily_rate"),
            "daily_rate_explanation": info.get("explanation"),
        })
    return result


def mission_to_dict(mission: MissionTable, db: Optional[Session] = None) -> Dict[str, Any]:
    emergencies: List[Dict[str, Any]] = []
    resolved_emergencies: List[Dict[str, Any]] = []
    if db is not None:
        rows = db.query(EmergencyTable).filter(
            EmergencyTable.mission_id == mission.id,
        ).all()
        active = [row for row in rows if row.status == "active"]
        resolved = [row for row in rows if row.status == "resolved"]
        emergencies = [emergency_to_dict(row) for row in active]
        resolved_emergencies = [emergency_to_dict(row) for row in resolved]

    return {
        "id": mission.id,
        "name": mission.name,
        "destination": mission.destination,
        "astronaut_count": mission.astronaut_count,
        "duration": mission.duration,
        "difficulty": mission.difficulty,
        "status": mission.status,
        "current_day": mission.current_day,
        "progress": float(mission.progress) if mission.progress is not None else 0.0,
        "oxygen": float(mission.oxygen) if mission.oxygen is not None else 100.0,
        "fuel": float(mission.fuel) if mission.fuel is not None else 100.0,
        "food": float(mission.food) if mission.food is not None else 100.0,
        "water": float(mission.water) if mission.water is not None else 100.0,
        "energy": float(mission.energy) if mission.energy is not None else 100.0,
        "astronaut_health": float(mission.astronaut_health) if mission.astronaut_health is not None else 100.0,
        "created_at": mission.created_at.isoformat() if mission.created_at else None,
        "updated_at": mission.updated_at.isoformat() if mission.updated_at else None,
        "emergencies": emergencies,
        "resolved_emergencies": resolved_emergencies,
        # Additive field (Phase 1): the live simulation profile for this mission.
        "simulation": mission_profile(mission),
    }


def ensure_schema() -> None:
    # Safe and idempotent on both engines: creates only missing tables.
    # It never drops or alters existing data.
    Base.metadata.create_all(bind=engine)

    if IS_SQLITE:
        # Safe, backward-compatible migration for databases created by older builds.
        # PRAGMA is SQLite-specific; PostgreSQL gets its columns from create_all()
        # above. Never run this against PostgreSQL.
        with engine.begin() as conn:
            columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(missions)")]
            for column in ("oxygen", "fuel", "food", "water", "energy", "astronaut_health"):
                if column not in columns:
                    conn.exec_driver_sql(f"ALTER TABLE missions ADD COLUMN {column} FLOAT DEFAULT 100.0")
                    conn.exec_driver_sql(f"UPDATE missions SET {column} = 100.0 WHERE {column} IS NULL")

    # Backfill astronaut records for missions that do not have them yet.
    db = SessionLocal()
    try:
        missions = db.query(MissionTable).all()
        for mission in missions:
            count = db.query(AstronautTable).filter(AstronautTable.mission_id == mission.id).count()
            if count == 0:
                create_astronauts(db, mission)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/missions", status_code=201, response_model=MissionRead)
def create_mission(mission: MissionCreate, db: Session = Depends(get_db)):
    mission_id = (uuid.uuid4().int & (10**10 - 1))

    db_mission = MissionTable(
        id=mission_id,
        name=mission.name,
        destination=mission.destination,
        astronaut_count=mission.astronaut_count,
        duration=mission.duration,
        difficulty=mission.difficulty,
        status="draft",
        current_day=0,
        progress=0.0,
        oxygen=100.0,
        fuel=100.0,
        food=100.0,
        water=100.0,
        energy=100.0,
        astronaut_health=100.0,
    )
    db.add(db_mission)
    db.commit()
    db.refresh(db_mission)

    create_astronauts(db, db_mission)
    log_event(db, db_mission.id, "mission_created", f"Mission '{db_mission.name}' created.",
              {"destination": db_mission.destination, "duration": db_mission.duration}, 0)
    db.commit()

    return mission_to_dict(db_mission, db)


@app.get("/api/missions", response_model=List[MissionRead])
def list_missions(db: Session = Depends(get_db)):
    missions = db.query(MissionTable).order_by(MissionTable.created_at.desc()).all()
    return [mission_to_dict(m, db) for m in missions]


@app.get("/api/missions/{mission_id}", response_model=MissionRead)
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission_to_dict(mission, db)


@app.post("/api/missions/{mission_id}/start", response_model=MissionRead)
def start_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft missions can be started")

    mission.status = "active"
    mission.current_day = 0
    mission.progress = 0.0
    mission.oxygen = 100.0
    mission.fuel = 100.0
    mission.food = 100.0
    mission.water = 100.0
    mission.energy = 100.0
    mission.astronaut_health = 100.0

    # Ensure astronaut records exist.
    if db.query(AstronautTable).filter(AstronautTable.mission_id == mission.id).count() == 0:
        create_astronauts(db, mission)
    for astronaut in db.query(AstronautTable).filter(AstronautTable.mission_id == mission.id).all():
        astronaut.health = 100.0
        astronaut.health_status = "good"
        astronaut.heart_rate = 72
        astronaut.oxygen_saturation = 98
        astronaut.body_temperature = 36.5

    db.commit()
    db.refresh(mission)

    log_event(db, mission.id, "mission_started", f"Mission '{mission.name}' started.", {}, mission.current_day)
    db.commit()

    return mission_to_dict(mission, db)


@app.post("/api/missions/{mission_id}/advance", response_model=MissionRead)
@app.post("/api/missions/{mission_id}/simulate", response_model=MissionRead)
def advance_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != "active":
        raise HTTPException(status_code=400, detail="Only active missions can advance")

    mission.current_day += 1

    # The plan is calculated once so the mission row and every astronaut row
    # are updated with exactly the same, destination/difficulty aware numbers.
    plan = daily_plan(mission)
    apply_daily_consumption(mission)

    health_delta = -float(plan["health"]["daily_decay"])
    _update_astronauts_for_health_delta(db, mission.id, health_delta)

    previous_status = mission.status
    evaluate_mission_status(mission)
    db.commit()
    db.refresh(mission)

    log_event(db, mission.id, "day_advanced", f"Advanced to day {mission.current_day}.",
              {
                  "progress": mission.progress,
                  "oxygen": mission.oxygen,
                  "daily_consumption": {
                      resource_type: info["daily_rate"]
                      for resource_type, info in plan["resources"].items()
                  },
                  "health_decay": plan["health"]["daily_decay"],
              },
              mission.current_day)

    if previous_status != mission.status:
        if mission.status == "completed":
            log_event(db, mission.id, "mission_completed", "Mission completed successfully.", {}, mission.current_day)
        elif mission.status == "failed":
            log_event(db, mission.id, "mission_failed", "Mission failed due to critical depletion.", {}, mission.current_day)

    # Deterministic emergency rule: a resource in the critical band raises the
    # matching scenario once (no randomness, so runs stay reproducible).
    if mission.status == "active":
        emergency = maybe_trigger_critical_emergency(db, mission)
        if emergency is not None:
            if mission.status == "failed":
                log_event(db, mission.id, "mission_failed", "Mission failed due to critical depletion.", {}, mission.current_day)
            db.commit()
            db.refresh(mission)

    db.commit()
    db.refresh(mission)

    return mission_to_dict(mission, db)


@app.post("/api/missions/{mission_id}/pause", response_model=MissionRead)
def pause_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != "active":
        raise HTTPException(status_code=400, detail="Only active missions can be paused")
    mission.status = "paused"
    db.commit()
    db.refresh(mission)
    log_event(db, mission.id, "mission_paused", "Mission paused.", {}, mission.current_day)
    db.commit()
    return mission_to_dict(mission, db)


@app.post("/api/missions/{mission_id}/resume", response_model=MissionRead)
def resume_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != "paused":
        raise HTTPException(status_code=400, detail="Only paused missions can be resumed")
    mission.status = "active"
    db.commit()
    db.refresh(mission)
    log_event(db, mission.id, "mission_resumed", "Mission resumed.", {}, mission.current_day)
    db.commit()
    return mission_to_dict(mission, db)


@app.post("/api/missions/{mission_id}/actions", response_model=MissionRead)
def mission_action(mission_id: int, action_req: ActionRequest, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != "active":
        raise HTTPException(status_code=400, detail="Actions are only allowed on active missions")

    action = action_req.action
    if action is None:
        raise HTTPException(status_code=422, detail="action is required")

    apply_action(mission, action)

    delta = 0.0
    effects = {}
    # Re-derive delta from simulation constants.
    from .simulation import ACTION_EFFECTS
    effects = ACTION_EFFECTS.get(action, {})
    delta = float(effects.get("astronaut_health", 0.0))
    if delta:
        _update_astronauts_for_health_delta(db, mission.id, delta)

    evaluate_mission_status(mission)
    db.commit()
    db.refresh(mission)

    log_event(db, mission.id, "action_executed", f"Action executed: {action}.",
              {"action": action, "effects": effects}, mission.current_day)

    if mission.status == "completed":
        log_event(db, mission.id, "mission_completed", "Mission completed successfully.", {}, mission.current_day)
    elif mission.status == "failed":
        log_event(db, mission.id, "mission_failed", "Mission failed due to critical depletion.", {}, mission.current_day)
    db.commit()

    return mission_to_dict(mission, db)


@app.get("/api/missions/{mission_id}/status", response_model=MissionRead)
def mission_status(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission_to_dict(mission, db)


@app.get("/api/missions/{mission_id}/resources")
def mission_resources(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return build_resources(mission)


@app.get("/api/missions/{mission_id}/astronauts")
def mission_astronauts(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    astronauts = db.query(AstronautTable).filter(AstronautTable.mission_id == mission_id).all()
    if not astronauts:
        create_astronauts(db, mission)
        db.commit()
        astronauts = db.query(AstronautTable).filter(AstronautTable.mission_id == mission_id).all()
    return [astronaut_to_dict(a) for a in astronauts]


@app.post("/api/missions/{mission_id}/emergency")
def trigger_emergency(mission_id: int, payload: Optional[EmergencyTriggerRequest] = None,
                     db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != "active":
        raise HTTPException(status_code=400, detail="Emergencies can only be triggered on active missions")

    if payload is None:
        payload = EmergencyTriggerRequest()

    emergency_type = payload.type
    if emergency_type not in EMERGENCY_DEFAULTS:
        emergency_type = None

    emergency = trigger_emergency_for_mission(
        db,
        mission,
        requested_type=emergency_type,
        severity=payload.severity,
        description=payload.description,
    )
    db.commit()
    db.refresh(mission)
    db.refresh(emergency)

    return emergency_to_dict(emergency)


@app.post("/api/missions/{mission_id}/emergencies/{emergency_id}/resolve")
def resolve_emergency(mission_id: int, emergency_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != "active":
        raise HTTPException(status_code=400, detail="Emergencies can only be resolved on active missions")

    emergency = db.query(EmergencyTable).filter(EmergencyTable.id == emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    if emergency.mission_id != mission_id:
        raise HTTPException(status_code=404, detail="Emergency not found for this mission")
    if emergency.status == "resolved":
        raise HTTPException(status_code=400, detail="Emergency is already resolved")

    required_action = RESOLUTION_RULES.get(emergency.type, "repair")
    events = db.query(MissionEventTable).filter(
        MissionEventTable.mission_id == mission_id,
        MissionEventTable.event_type == "action_executed",
    ).all()
    found = False
    for event in events:
        try:
            details = json.loads(event.details or "{}")
        except (json.JSONDecodeError, TypeError):
            details = {}
        action = details.get("action")
        event_created = event.created_at
        emergency_created = emergency.created_at
        if event_created is None or emergency_created is None or event_created >= emergency_created:
            if action == required_action:
                found = True
                break

    if not found:
        raise HTTPException(
            status_code=400,
            detail=f"Execute the required '{required_action}' action before resolving this emergency.",
        )

    emergency.status = "resolved"
    emergency.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(mission)
    db.refresh(emergency)

    log_event(
        db,
        mission.id,
        "emergency_resolved",
        f"Emergency resolved: {emergency.type.replace('_', ' ')}",
        {"emergency_id": emergency.id, "type": emergency.type, "required_action": required_action},
        mission.current_day,
    )
    db.commit()

    return {
        "emergency": emergency_to_dict(emergency),
        "mission": mission_to_dict(mission, db),
    }


@app.get("/api/missions/{mission_id}/history")
def mission_history(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    events = db.query(MissionEventTable).filter(
        MissionEventTable.mission_id == mission_id
    ).order_by(MissionEventTable.created_at.asc()).all()
    return [event_to_dict(e) for e in events]


@app.get("/api/missions/{mission_id}/report")
def mission_report(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(MissionTable).filter(MissionTable.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    astronauts = db.query(AstronautTable).filter(AstronautTable.mission_id == mission_id).all()
    emergencies = db.query(EmergencyTable).filter(EmergencyTable.mission_id == mission_id).all()
    events = db.query(MissionEventTable).filter(MissionEventTable.mission_id == mission_id).order_by(
        MissionEventTable.created_at.asc()).all()

    resource_values = [mission.oxygen, mission.water, mission.food, mission.energy, mission.fuel]
    avg_resource = sum(float(v or 0.0) for v in resource_values) / len(resource_values)
    avg_health = (sum(float(a.health or 0.0) for a in astronauts) / len(astronauts)) if astronauts else float(mission.astronaut_health or 0.0)

    emergency_count = len(emergencies)
    emergency_penalty = min(30.0, emergency_count * 8.0)

    if mission.status == "completed":
        score = 60.0 + 0.25 * avg_resource + 0.15 * avg_health - emergency_penalty
    elif mission.status == "failed":
        score = min(40.0, 0.3 * avg_resource + 0.2 * avg_health)
    else:
        score = 45.0 + 0.2 * avg_resource + 0.15 * avg_health - emergency_penalty
    score = _clamp(score, 0.0, 100.0)

    actions = [e for e in events if e.event_type == "action_executed"]
    successful_actions = []
    for event in actions:
        try:
            details = json.loads(event.details or "{}")
        except (json.JSONDecodeError, TypeError):
            details = {}
        action_name = details.get("action")
        if action_name:
            successful_actions.append(str(action_name))

    decisions = [e.message for e in events if e.event_type in {"action_executed", "day_advanced", "emergency_triggered"}]

    improvements = []
    if mission.oxygen < 40:
        improvements.append("Improve oxygen conservation and leak response.")
    if mission.water < 40:
        improvements.append("Stabilize water recycling and rationing.")
    if mission.food < 40:
        improvements.append("Manage food consumption more efficiently.")
    if mission.energy < 40:
        improvements.append("Reduce energy consumption and restore power systems.")
    if mission.fuel < 40:
        improvements.append("Optimize fuel usage during mission operations.")
    if avg_health < 70:
        improvements.append("Prioritize crew rest and health recovery.")
    if emergency_count > 0:
        improvements.append("Review emergency detection and response procedures.")
    if not improvements:
        improvements.append("Maintain current resource and crew management practices.")

    metrics = {
        "resource_management": f"{avg_resource:.0f}/100",
        "emergency_response": (f"{sum(1 for e in emergencies if e.status == 'resolved')}/{emergency_count} resolved"
                              if emergency_count else "No emergencies"),
        "astronaut_safety": f"{avg_health:.0f}/100",
    }

    static_feedback = (
        "Focus on balancing resource consumption with mission progress. "
        "Review emergency procedures, crew health management, and resource conservation strategies."
    )

    outcome = mission.status
    if mission.status == "completed":
        outcome = "completed"
    elif mission.status == "failed":
        outcome = "failed"

    ai_feedback = static_feedback
    if get_config()["llm_api_key"]:
        cache_key = (mission.id, mission.status, mission.current_day)
        ai_feedback = _REPORT_FEEDBACK_CACHE.get(cache_key, "")
        if not ai_feedback:
            report_prompt = (
                "Create a 3-5 sentence educational mission summary using only this report data. "
                "Mention the outcome, score, resource management, emergencies, and exactly one improvement tip. "
                "Do not add facts or numbers that are not present.\n\n"
                f"REPORT DATA: {json.dumps({
                    'outcome': outcome,
                    'score': round(score, 2),
                    'resource_management': metrics['resource_management'],
                    'emergency_response': metrics['emergency_response'],
                    'astronaut_safety': metrics['astronaut_safety'],
                    'emergencies_encountered': emergency_count,
                    'areas_for_improvement': improvements,
                    'duration': mission.current_day,
                })}"
            )
            generated_feedback = _call_llm(report_prompt)
            if generated_feedback:
                ai_feedback = generated_feedback
                _REPORT_FEEDBACK_CACHE[cache_key] = generated_feedback
            else:
                ai_feedback = static_feedback

    return {
        "mission_name": mission.name,
        "mission_id": mission.id,
        "outcome": outcome,
        "mission_outcome": outcome,
        "result": outcome,
        "score": round(score, 2),
        "final_score": round(score, 2),
        "training_score": round(score, 2),
        "duration": mission.current_day,
        "mission_duration": mission.current_day,
        "metrics": metrics,
        "performance": metrics,
        "decisions": decisions,
        "decisions_made": decisions,
        "successful_actions": successful_actions,
        "successes": successful_actions,
        "unsuccessful_actions": [],
        "failures": [],
        "areas_for_improvement": improvements,
        "improvements": improvements,
        "ai_feedback": ai_feedback,
        "feedback": ai_feedback,
        "educational_feedback": ai_feedback,
        "emergencies_encountered": emergency_count,
    }


@app.get("/api/config/simulation")
def simulation_config():
    """Expose the simulation configuration (destinations, difficulties, rules).

    Additive endpoint — it does not change any existing mission contract.
    """
    return simulation_config_payload()


@app.get("/api/config/simulation/preview")
def simulation_preview(
    destination: str = Query(..., pattern=f"^({'|'.join(DESTINATIONS)})$"),
    difficulty: str = Query(..., pattern=f"^({'|'.join(DIFFICULTIES)})$"),
    crew: int = Query(..., ge=0, le=12),
    duration: int = Query(0, ge=0, le=365),
):
    """Preview the consumption profile for a planned mission configuration.

    Uses exactly the same calculations as a live mission, so the numbers shown
    before launch are the numbers the simulation will apply.
    """
    full_supplies = {resource_type: 100.0 for resource_type in RESOURCE_ORDER}
    return build_profile(
        destination_id=destination,
        difficulty_id=difficulty,
        crew_size=crew,
        current_resources=full_supplies,
        current_day=0,
        duration=duration,
    )


@app.post("/api/agent/chat", response_model=AgentChatResponse)
def agent_chat(payload: AgentChatRequest):
    result = run_agent(payload.mission_id, payload.message)
    return result


from .nasa import destination_datasets, search_documents
from .nasa.client import NasaApiUnavailable


@app.get("/api/nasa/status")
def nasa_status():
    """Configuration snapshot for the NASA integration (no network calls)."""
    config = get_config()
    from .ai.rag import document_inventory, NASA_KNOWLEDGE

    return {
        "available": bool(config["nasa_data_enabled"]),
        "enabled": config["nasa_data_enabled"],
        "ntrs_base_url": config["nasa_ntrs_base_url"],
        "pds_base_url": config["nasa_pds_base_url"],
        "cache_ttl_seconds": config["nasa_data_cache_ttl"],
        "cache_directory": config["nasa_cache_directory"],
        "authentication": "none required for NTRS and PDS (public services)",
        "knowledge_documents_indexed": len({doc["ntrs_id"] for doc in document_inventory()}),
        "knowledge_chunks_indexed": len(NASA_KNOWLEDGE),
    }


@app.get("/api/nasa/sources")
def nasa_sources():
    """List the official NASA publications indexed in the knowledge base."""
    from .ai.rag import document_inventory

    documents = document_inventory()
    return {
        "available": bool(documents),
        "source": "NASA Technical Reports Server (ntrs.nasa.gov)",
        "documents": documents,
        "total_documents": len(documents),
        "notes": (
            "Every passage in the JAMT knowledge base is extracted from one of these "
            "NASA Technical Reports Server publications. Document provenance (NTRS id, "
            "title, publication date, original link) is preserved per chunk."
        ),
    }


@app.get("/api/nasa/datasets")
def nasa_datasets(destination: str = Query(..., pattern="^(moon|mars)$"),
                  limit: int = Query(8, ge=1, le=12)):
    """Real NASA Planetary Data System bundles for a destination."""
    config = get_config()
    if not config["nasa_data_enabled"]:
        return {"available": False, "enabled": False, "message": "NASA data integration is disabled (NASA_DATA_ENABLED=false).",
                "destination": destination}
    try:
        return destination_datasets(destination, limit)
    except NasaApiUnavailable as exc:
        return {"available": False, "message": f"NASA PDS is currently unavailable: {exc}", "destination": destination}


@app.get("/api/nasa/reports")
def nasa_reports(q: str = Query(..., min_length=2, max_length=200),
                 limit: int = Query(5, ge=1, le=10)):
    """Search official NASA technical reports (NTRS)."""
    config = get_config()
    if not config["nasa_data_enabled"]:
        return {"available": False, "enabled": False, "message": "NASA data integration is disabled (NASA_DATA_ENABLED=false).",
                "query": q}
    try:
        return search_documents(q, limit)
    except NasaApiUnavailable as exc:
        return {"available": False, "message": f"NASA Technical Reports Server is currently unavailable: {exc}", "query": q}


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Initialize schema on import (unchanged production behaviour).
# JAMT_SKIP_DB_INIT=1 prevents this from touching a database, which is used by
# the automated test suite so the project's jamt.db is never written to.
if os.getenv("JAMT_SKIP_DB_INIT", "").strip().lower() not in {"1", "true", "yes"}:
    ensure_schema()
