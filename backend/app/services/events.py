from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import decrypt_json
from app.models import User, Checkpoint, EmergencyEvent, SafetyStatus
from app.services.common import haversine_km, notify, audit
from app.services.vault import latest_checkpoint, set_incident_hold


def event_is_relevant(event: EmergencyEvent, cp: Checkpoint) -> tuple[bool, float | None]:
    loc = decrypt_json(cp.encrypted_location)
    if not loc or event.latitude is None or event.longitude is None:
        return False, None
    distance = haversine_km(loc["lat"], loc["lon"], event.latitude, event.longitude)
    radius = event.radius_km or settings.earthquake_max_distance_km
    if event.type.upper() == "EARTHQUAKE":
        if event.magnitude is not None and event.magnitude < settings.earthquake_min_magnitude:
            return False, distance
    return distance <= radius, distance


def trigger_checkins(db: Session, event: EmergencyEvent) -> list[str]:
    affected: list[str] = []
    users = db.scalars(select(User).where(User.status == "ACTIVE", User.is_minor == False)).all()
    for user in users:
        cp = latest_checkpoint(db, user.id)
        if not cp:
            continue
        relevant, distance = event_is_relevant(event, cp)
        if not relevant:
            continue
        existing = db.scalar(select(SafetyStatus).where(
            SafetyStatus.user_id == user.id,
            SafetyStatus.event_id == event.id,
        ).limit(1))
        if existing:
            continue
        status = SafetyStatus(user_id=user.id, event_id=event.id, status="CHECK_REQUESTED")
        db.add(status)
        notify(
            db,
            user.id,
            "SAFETY_CHECK",
            "¿Estás bien?",
            f"Se detectó un evento {event.type.lower()} relevante cerca de tu ubicación.",
            metadata={"event_id": event.id, "distance_km": round(distance or 0, 2)},
        )
        set_incident_hold(db, cp, user.id, f"Evento {event.id}")
        affected.append(user.id)
    audit(db, None, "EVENT_TRIGGER_CHECKINS", "event", event.id, metadata={"affected_users": affected})
    return affected
