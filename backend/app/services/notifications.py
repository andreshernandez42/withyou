from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Notification, Device
from app.services.timeutils import utcnow


def _firebase_app():
    if not settings.fcm_enabled or not settings.firebase_credentials_path:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(Path(settings.firebase_credentials_path)))
            firebase_admin.initialize_app(cred)
        return firebase_admin.get_app()
    except Exception:
        return None


def dispatch_pending_notifications(db: Session, limit: int = 100) -> dict:
    rows = db.scalars(select(Notification).where(Notification.status == "PENDING").order_by(Notification.created_at.asc()).limit(limit)).all()
    sent = failed = deferred = 0
    app = _firebase_app()
    for row in rows:
        devices = db.scalars(select(Device).where(Device.user_id == row.user_id, Device.active == True, Device.push_token.is_not(None))).all()  # noqa: E712
        if not settings.fcm_enabled or app is None or not devices:
            deferred += 1
            continue  # La app puede recibirla por polling IN_APP.
        try:
            from firebase_admin import messaging
            data = json.loads(row.metadata_json) if row.metadata_json else {}
            for device in devices:
                msg = messaging.Message(
                    notification=messaging.Notification(title=row.title, body=row.body),
                    data={k: str(v) for k, v in data.items()},
                    token=device.push_token,
                )
                messaging.send(msg)
            row.status = "SENT"
            row.sent_at = utcnow()
            row.delivery_attempts += 1
            sent += 1
        except Exception as exc:
            row.delivery_attempts += 1
            row.last_error = str(exc)[:1000]
            if row.delivery_attempts >= 3:
                row.status = "FAILED"
            failed += 1
    db.commit()
    return {"sent": sent, "failed": failed, "deferred_in_app": deferred}
