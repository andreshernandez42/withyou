"""Ingesta validada de eventos oficiales. No admite registros sin fecha verificable."""
from __future__ import annotations

import json
import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.sgc import SgcEarthquakeAdapter
from app.core.config import settings
from app.models import EmergencyEvent, OfficialSourceSync
from app.services.common import audit
from app.services.events import trigger_checkins
from app.services.timeutils import utcnow, as_utc


def ingest_sgc_items(db: Session, items: list[dict], actor_id: str | None = None) -> dict:
    created, rejected = [], []
    now = utcnow()
    for item in items:
        ext_id = item.get("external_id")
        reason = None
        event_time = item.get("starts_at")
        magnitude = item.get("magnitude")
        try:
            latitude, longitude = float(item["latitude"]), float(item["longitude"])
            valid_coordinates = all(map(math.isfinite, (latitude, longitude))) and -90 <= latitude <= 90 and -180 <= longitude <= 180
        except (ValueError, TypeError, KeyError):
            valid_coordinates = False
        if not ext_id:
            reason = "missing_external_id"
        elif magnitude is None or not isinstance(magnitude, (int, float)) or not math.isfinite(magnitude) or not 0 <= magnitude <= 10:
            reason = "invalid_magnitude"
        elif magnitude < settings.earthquake_min_magnitude:
            reason = "magnitude_filter"
        elif not valid_coordinates:
            reason = "invalid_coordinates"
        elif event_time is None:
            reason = "missing_event_time"
        else:
            age = now - as_utc(event_time)
            if age < -timedelta(minutes=5):
                reason = "future_event_time"
            elif age > timedelta(minutes=settings.earthquake_max_age_minutes):
                reason = "age_filter"
        if reason:
            rejected.append({"external_id": ext_id, "reason": reason})
            continue
        if db.scalar(select(EmergencyEvent.id).where(EmergencyEvent.source == "SGC", EmergencyEvent.external_id == str(ext_id)).limit(1)):
            continue
        event = EmergencyEvent(
            source="SGC", type="EARTHQUAKE", is_test=False, status="ACTIVE",
            severity="UNKNOWN", certainty="OBSERVED", urgency="EXPECTED",
            latitude=latitude, longitude=longitude, radius_km=settings.earthquake_max_distance_km,
            magnitude=magnitude, depth_km=item.get("depth_km"), external_id=str(ext_id),
            starts_at=as_utc(event_time), raw_payload=json.dumps(item.get("raw", {}), default=str, ensure_ascii=False),
        )
        db.add(event)
        db.flush()
        affected = trigger_checkins(db, event)
        created.append({"id": event.id, "affected": len(affected)})
    result = {"fetched": len(items), "created": len(created), "rejected": rejected, "events": created}
    db.add(OfficialSourceSync(source="SGC", status="OK", last_success_at=utcnow(), records_count=len(items),
                              details=f"created={len(created)} rejected={len(rejected)}"))
    audit(db, actor_id, "SGC_SYNC", "source", None,
          metadata={"created": len(created), "fetched": len(items), "rejected": len(rejected)})
    db.commit()
    return result


async def sync_sgc_events(db: Session, actor_id: str | None = None) -> dict:
    items = await SgcEarthquakeAdapter().fetch_recent(100)
    return ingest_sgc_items(db, items, actor_id)
