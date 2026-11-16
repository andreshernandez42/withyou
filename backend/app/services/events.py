from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import decrypt_json
from app.models import User, Checkpoint, EmergencyEvent, SafetyStatus, TrustedContact, WelfareCheck
from app.services.common import haversine_km, notify, audit
from app.services.timeutils import utcnow, as_utc
from app.services.vault import latest_checkpoint, set_incident_hold
from app.services.policy import default_policy, grant_for_emergency_contacts


def event_is_current(event: EmergencyEvent) -> bool:
    if event.status not in {"ACTIVE", "UPDATED"}:
        return False
    if event.ends_at and as_utc(event.ends_at) < utcnow():
        return False
    if event.type.upper() == "EARTHQUAKE":
        age = utcnow() - as_utc(event.starts_at or event.created_at)
        if age > timedelta(minutes=settings.earthquake_max_age_minutes) and not event.is_test:
            return False
    return True


def event_is_relevant(event: EmergencyEvent, cp: Checkpoint) -> tuple[bool, float | None, str]:
    if not event_is_current(event):
        return False, None, "event_not_current"
    if event.type.upper() == "EARTHQUAKE":
        if utcnow() - as_utc(cp.created_at) > timedelta(minutes=settings.earthquake_checkpoint_max_age_minutes):
            return False, None, "stale_checkpoint"
    loc = decrypt_json(cp.encrypted_location)
    if not loc or event.latitude is None or event.longitude is None:
        return False, None, "missing_geometry"
    distance = haversine_km(loc["lat"], loc["lon"], event.latitude, event.longitude)
    radius = event.radius_km or settings.earthquake_max_distance_km
    if event.type.upper() == "EARTHQUAKE":
        if event.magnitude is None:
            return False, distance, "magnitude_unknown"
        if event.magnitude < settings.earthquake_min_magnitude:
            return False, distance, "below_magnitude_threshold"
    if distance > radius:
        return False, distance, "outside_area"
    return True, distance, "relevant"


def trigger_checkins(db: Session, event: EmergencyEvent) -> list[str]:
    affected: list[str] = []
    users = db.scalars(select(User).where(User.status == "ACTIVE", User.is_minor == False)).all()  # noqa: E712
    for user in users:
        # Una simulación nunca debe dirigirse a usuarios normales.
        if event.is_test and user.role not in {'TESTER', 'ADMIN'}:
            continue
        cp = latest_checkpoint(db, user.id)
        if not cp:
            continue
        relevant, distance, reason = event_is_relevant(event, cp)
        if not relevant:
            continue
        existing = db.scalar(select(SafetyStatus).where(
            SafetyStatus.user_id == user.id,
            SafetyStatus.event_id == event.id,
        ).limit(1))
        if existing:
            continue
        status = SafetyStatus(
            user_id=user.id,
            event_id=event.id,
            status="CHECK_REQUESTED",
            expires_at=utcnow() + timedelta(seconds=settings.safety_check_timeout_seconds),
        )
        db.add(status); db.flush()
        notify(
            db, user.id, "SAFETY_CHECK", "¿Estás bien?",
            f"Se detectó un evento {event.type.lower()} relevante cerca de tu última ubicación.",
            metadata={"event_id": event.id, "distance_km": round(distance or 0, 2), "is_test": event.is_test},
        )
        if not event.is_test:
            set_incident_hold(db, cp, user.id, f"Evento {event.id}")
        affected.append(user.id)
    audit(db, None, "EVENT_TRIGGER_CHECKINS", "event", event.id,
          metadata={"affected_users": affected, "is_test": event.is_test})
    return affected


def process_safety_timeouts(db: Session) -> int:
    now = utcnow()
    rows = db.scalars(select(SafetyStatus).where(
        SafetyStatus.status == "CHECK_REQUESTED",
        SafetyStatus.expires_at.is_not(None),
        SafetyStatus.expires_at <= now,
    )).all()
    processed = 0
    for row in rows:
        row.status = "NO_RESPONSE"
        if row.welfare_check_id:
            check=db.get(WelfareCheck,row.welfare_check_id)
            if check and check.status in {'CHECK_REQUESTED','TRUSTED_QUORUM_PENDING'}:
                check.status='NO_RESPONSE'
        event = db.get(EmergencyEvent, row.event_id) if row.event_id else None
        notify(db, row.user_id, "SAFETY_CHECK_TIMEOUT", "Estado aún no confirmado",
               "No se recibió respuesta al check-in. Esto no significa que la persona esté desaparecida.",
               {"event_id": row.event_id})
        # Notifica a contactos, sin revelar ubicación todavía salvo política preautorizada.
        contacts = db.scalars(select(TrustedContact).where(
            TrustedContact.owner_user_id == row.user_id,
            TrustedContact.status == "ACCEPTED",
            TrustedContact.revoked_at.is_(None),
            TrustedContact.can_receive_sos == True,  # noqa: E712
            TrustedContact.contact_user_id.is_not(None),
        )).all()
        for c in contacts:
            if event and event.is_test:
                continue
            notify(db, c.contact_user_id, "NO_RESPONSE", "Estado aún no confirmado",
                   "No se recibió respuesta al check-in de un contacto de confianza.",
                   {"subject_user_id": row.user_id, "event_id": row.event_id})
        policy = default_policy(db, row.user_id, event.type if event else None)
        if event and not event.is_test and policy and policy.release_on_official_event_no_response:
            grant_for_emergency_contacts(
                db, row.user_id, "EMERGENCY_EVENT", event.id,
                "Sin respuesta tras evento relevante preautorizado", event.type,
            )
        processed += 1
        audit(db, None, "SAFETY_CHECK_TIMEOUT", "safety_status", row.id,
              metadata={"user_id": row.user_id, "event_id": row.event_id})
    return processed
