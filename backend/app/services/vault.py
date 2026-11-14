from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select, delete, or_
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import encrypt_json, decrypt_json
from app.models import Checkpoint, Device
from app.services.timeutils import utcnow, as_utc
from app.services.common import audit


def create_checkpoint(db: Session, user_id: str, payload) -> Checkpoint:
    created = payload.created_at or utcnow()
    if as_utc(created) > utcnow() + timedelta(minutes=5):
        raise ValueError("created_at no puede estar en el futuro")
    if payload.device_id:
        device = db.get(Device, payload.device_id)
        if not device or device.user_id != user_id or not device.active:
            raise PermissionError("Dispositivo inválido")
    location = {"lat": payload.latitude, "lon": payload.longitude}
    row = Checkpoint(
        user_id=user_id,
        device_id=payload.device_id,
        created_at=created,
        synced_at=utcnow(),
        encrypted_location=encrypt_json(location),
        coarse_lat=round(payload.latitude, 2),
        coarse_lon=round(payload.longitude, 2),
        accuracy_m=payload.accuracy_m,
        battery_pct=payload.battery_pct,
        network_type=payload.network_type,
        movement_state=payload.movement_state,
        expires_at=created + timedelta(hours=settings.checkpoint_ttl_hours),
    )
    db.add(row); db.flush()
    audit(db, user_id, "CHECKPOINT_CREATE", "checkpoint", row.id,
          metadata={"accuracy_m": payload.accuracy_m, "network": payload.network_type})
    return row


def latest_checkpoint(db: Session, user_id: str, include_expired: bool = False) -> Checkpoint | None:
    q = select(Checkpoint).where(Checkpoint.user_id == user_id)
    if not include_expired:
        q = q.where(or_(Checkpoint.expires_at > utcnow(), Checkpoint.incident_hold == True))  # noqa: E712
    return db.scalar(q.order_by(Checkpoint.created_at.desc()).limit(1))


def checkpoint_public(row: Checkpoint, level: str = "COARSE") -> dict:
    result = {
        "id": row.id,
        "created_at": row.created_at,
        "synced_at": row.synced_at,
        "age_seconds": max(0, int((utcnow() - as_utc(row.created_at)).total_seconds())),
        "accuracy_m": row.accuracy_m,
        "battery_pct": row.battery_pct,
        "network_type": row.network_type,
        "movement_state": row.movement_state,
        "expires_at": row.expires_at,
        "incident_hold": row.incident_hold,
        "level": level,
    }
    if level == "EXACT":
        result["location"] = decrypt_json(row.encrypted_location)
    elif level == "COARSE":
        result["location"] = {"lat": row.coarse_lat, "lon": row.coarse_lon}
    return result


def set_incident_hold(db: Session, row: Checkpoint, actor_user_id: str | None, reason: str) -> None:
    row.incident_hold = True
    row.hold_reason = reason
    row.hold_actor_user_id = actor_user_id
    row.hold_expires_at = utcnow() + timedelta(hours=settings.incident_hold_hours)
    audit(db, actor_user_id, "CHECKPOINT_HOLD", "checkpoint", row.id,
          metadata={"reason": reason, "until": row.hold_expires_at})


def release_incident_hold(db: Session, row: Checkpoint, actor_user_id: str | None, reason: str) -> None:
    row.incident_hold = False
    row.hold_expires_at = None
    row.hold_reason = None
    audit(db, actor_user_id, "CHECKPOINT_HOLD_RELEASE", "checkpoint", row.id, metadata={"reason": reason})


def cleanup_expired(db: Session) -> int:
    now = utcnow()
    stmt = delete(Checkpoint).where(
        Checkpoint.expires_at < now,
        or_(Checkpoint.incident_hold == False, Checkpoint.hold_expires_at < now),  # noqa: E712
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0
