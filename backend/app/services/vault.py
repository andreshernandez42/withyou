from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select, delete, or_
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import encrypt_json, decrypt_json
from app.models import Checkpoint
from app.services.common import utcnow, audit


def create_checkpoint(db: Session, user_id: str, payload) -> Checkpoint:
    created = payload.created_at or utcnow()
    location = {"lat": payload.latitude, "lon": payload.longitude}
    row = Checkpoint(
        user_id=user_id,
        created_at=created,
        synced_at=utcnow(),
        encrypted_location=encrypt_json(location),
        coarse_lat=round(payload.latitude, 1),
        coarse_lon=round(payload.longitude, 1),
        accuracy_m=payload.accuracy_m,
        battery_pct=payload.battery_pct,
        network_type=payload.network_type,
        movement_state=payload.movement_state,
        expires_at=created + timedelta(hours=settings.checkpoint_ttl_hours),
    )
    db.add(row)
    db.flush()
    audit(db, user_id, "CHECKPOINT_CREATE", "checkpoint", row.id)
    return row


def latest_checkpoint(db: Session, user_id: str) -> Checkpoint | None:
    return db.scalar(select(Checkpoint).where(Checkpoint.user_id == user_id).order_by(Checkpoint.created_at.desc()).limit(1))


def checkpoint_public(row: Checkpoint, include_exact: bool = False) -> dict:
    result = {
        "id": row.id,
        "created_at": row.created_at,
        "synced_at": row.synced_at,
        "accuracy_m": row.accuracy_m,
        "battery_pct": row.battery_pct,
        "network_type": row.network_type,
        "movement_state": row.movement_state,
        "expires_at": row.expires_at,
        "incident_hold": row.incident_hold,
        "coarse_lat": row.coarse_lat,
        "coarse_lon": row.coarse_lon,
    }
    if include_exact:
        result["location"] = decrypt_json(row.encrypted_location)
    return result


def set_incident_hold(db: Session, row: Checkpoint, actor_user_id: str, reason: str) -> None:
    row.incident_hold = True
    row.hold_expires_at = utcnow() + timedelta(hours=settings.incident_hold_hours)
    audit(db, actor_user_id, "CHECKPOINT_HOLD", "checkpoint", row.id, metadata={"reason": reason, "until": row.hold_expires_at})


def cleanup_expired(db: Session) -> int:
    now = utcnow()
    stmt = delete(Checkpoint).where(
        Checkpoint.expires_at < now,
        or_(Checkpoint.incident_hold == False, Checkpoint.hold_expires_at < now),
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0
