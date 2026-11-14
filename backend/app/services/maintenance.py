from __future__ import annotations
from app.services.vault import cleanup_expired
from app.services.events import process_safety_timeouts
from app.services.welfare import expire_welfare_checks
from app.services.notifications import dispatch_pending_notifications


def maintenance_tick(db) -> dict:
    expired_checkpoints = cleanup_expired(db)
    timed_out = process_safety_timeouts(db)
    expired_welfare = expire_welfare_checks(db)
    db.commit()
    notifications = dispatch_pending_notifications(db)
    return {
        "expired_checkpoints": expired_checkpoints,
        "safety_timeouts": timed_out,
        "expired_welfare_checks": expired_welfare,
        "notifications": notifications,
    }
