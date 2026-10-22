from __future__ import annotations
import json
import math
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import AuditLog, Notification


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def audit(db: Session, actor_user_id: str | None, action: str, resource_type: str | None = None,
          resource_id: str | None = None, result: str = "SUCCESS", reason: str | None = None,
          metadata: dict | None = None) -> AuditLog:
    row = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        reason=reason,
        metadata_json=json_dumps(metadata) if metadata else None,
    )
    db.add(row)
    return row


def notify(db: Session, user_id: str, type_: str, title: str, body: str, metadata: dict | None = None) -> Notification:
    row = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        metadata_json=json_dumps(metadata) if metadata else None,
    )
    db.add(row)
    return row


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
