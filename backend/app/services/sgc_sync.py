"""Automatic SGC ingestion; external I/O never occupies the API event loop."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import threading
from datetime import timedelta

from sqlalchemy import select, text
from app.adapters.sgc import SgcEarthquakeAdapter
from app.adapters.sgc_recent import SgcRecentAdapter
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import EmergencyEvent, OfficialSourceSync
from app.services.common import audit
from app.services.events import trigger_checkins
from app.services.timeutils import utcnow, as_utc

logger = logging.getLogger(__name__)
_local_lock = threading.Lock()
_poll_lock = threading.Lock()
_STATUS_ID = "15c13694-6446-4f65-bae5-c23ae26ffac5"
# All replicas use the same transaction-scoped lock; released on rollback/crash.
_SGC_LOCK = 73842071


def update_status(db, *, failure=False, count=0):
    row = db.get(OfficialSourceSync, _STATUS_ID)
    if row is None:
        row = OfficialSourceSync(id=_STATUS_ID, source="SGC")
        db.add(row)
    if row.details != settings.sgc_source:
        row.last_success_at = None
        row.records_count = None
    row.status = "ERROR" if failure else "OK"
    if not failure:
        row.last_success_at = utcnow()
        row.records_count = count
    row.details = settings.sgc_source


def source_status(db, admin=False):
    row = db.get(OfficialSourceSync, _STATUS_ID)
    valid = row is not None and row.details == settings.sgc_source
    last = as_utc(row.last_success_at) if valid and row.last_success_at else None
    if not settings.sgc_poll_enabled:
        state = "PAUSED"
    elif not valid:
        state = "STARTING"
    elif row.status == "ERROR":
        state = "UNAVAILABLE"
    elif not last or utcnow() - last > timedelta(seconds=3 * settings.sgc_poll_interval_seconds):
        state = "DELAYED"
    else:
        state = "ACTIVE"
    result = {"source":"SGC", "state":state, "last_success_at":last}
    if admin:
        result.update(source_mode=settings.sgc_source, poll_enabled=settings.sgc_poll_enabled,
                      last_fetched=row.records_count if valid else None)
    return result


def persist_sgc_items(items: list[dict], actor_id: str | None = None) -> dict:
    """Commit events and their safety checks atomically, preserving prior data."""
    with _local_lock, SessionLocal() as db:
        try:
            if db.bind.dialect.name == 'postgresql':
                db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': _SGC_LOCK})
            created, rejected = [], []
            updated = 0
            for item in items:
                ext, mag, starts = item.get('external_id'), item.get('magnitude'), item.get('starts_at')
                reason = None
                if not ext:
                    reason = 'missing_event_id'
                elif mag is None or not math.isfinite(mag) or mag < settings.earthquake_min_magnitude:
                    reason = 'magnitude_filter'
                elif starts is None:
                    reason = 'missing_event_time'
                elif utcnow() - as_utc(starts) < -timedelta(minutes=5):
                    reason = 'future_event_time'
                elif utcnow() - as_utc(starts) > timedelta(minutes=settings.earthquake_max_age_minutes):
                    reason = 'age_filter'
                elif not (isinstance(item.get('latitude'), (int, float))
                          and isinstance(item.get('longitude'), (int, float))
                          and -90 <= item['latitude'] <= 90 and -180 <= item['longitude'] <= 180):
                    reason = 'invalid_geometry'
                if reason:
                    rejected.append({'external_id': ext, 'reason': reason})
                    continue
                row = db.scalar(select(EmergencyEvent).where(
                    EmergencyEvent.source == 'SGC', EmergencyEvent.external_id == str(ext)))
                is_new = row is None
                if is_new:
                    row = EmergencyEvent(source='SGC', external_id=str(ext), type='EARTHQUAKE',
                                         status='ACTIVE', certainty='OBSERVED', urgency='EXPECTED')
                    db.add(row)
                fields = dict(latitude=item['latitude'], longitude=item['longitude'], magnitude=mag,
                              depth_km=item.get('depth_km'), starts_at=starts,
                              radius_km=settings.earthquake_max_distance_km,
                              raw_payload=json.dumps(item.get('raw', {}), default=str, ensure_ascii=False))
                changed = is_new or any(getattr(row, key) != value for key, value in fields.items() if key != 'starts_at')
                for key, value in fields.items():
                    setattr(row, key, value)
                if not is_new and changed:
                    row.status = 'UPDATED'
                    updated += 1
                db.flush()
                # Also considers users whose first valid checkpoint arrived after ingestion.
                affected = trigger_checkins(db, row)
                if is_new:
                    created.append({'id': row.id, 'affected': len(affected)})
            update_status(db, count=len(items))
            audit(db, actor_id, 'SGC_SYNC', 'source', metadata={
                'created': len(created), 'updated': updated, 'fetched': len(items), 'rejected': len(rejected)})
            db.commit()
            return {'fetched': len(items), 'created': len(created), 'updated': updated,
                    'rejected': rejected, 'events': created}
        except Exception:
            db.rollback()
            raise


def record_failure(exc: Exception) -> None:
    with _local_lock, SessionLocal() as db:
        if db.get_bind().dialect.name == 'postgresql':
            db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': _SGC_LOCK})
        update_status(db, failure=True)
        db.commit()


async def sync_sgc_once(actor_id: str | None = None) -> dict:
    if not _poll_lock.acquire(blocking=False):
        return {"skipped": True, "fetched": 0, "created": 0, "updated": 0, "rejected": [], "events": []}
    try:
        if not settings.celery_enabled:
            return await _sync(actor_id)
        from redis.asyncio import Redis
        from redis.exceptions import LockNotOwnedError
        async with Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=3) as redis:
            lock = redis.lock('withyou:sgc:poll', timeout=120)
            if not await lock.acquire(blocking=False):
                return {"skipped": True, "fetched": 0, "created": 0, "updated": 0, "rejected": [], "events": []}
            try:
                return await _sync(actor_id)
            finally:
                try:
                    await lock.release()
                except LockNotOwnedError:
                    logger.warning("SGC synchronization lock expired")
    finally:
        _poll_lock.release()


async def _sync(actor_id: str | None) -> dict:
    try:
        adapter = SgcEarthquakeAdapter() if settings.sgc_source == "arcgis" else SgcRecentAdapter()
        items = await adapter.fetch_recent(100)
        return await asyncio.to_thread(persist_sgc_items, items, actor_id)
    except Exception as exc:
        logger.exception('SGC synchronization failed; existing events remain available')
        try:
            await asyncio.to_thread(record_failure, exc)
        except Exception:
            logger.exception('Could not record SGC synchronization failure')
        raise


async def sgc_poll_loop() -> None:
    while True:
        try:
            await sync_sgc_once()
        except Exception:
            # Failure is persisted above; the next poll retries without stopping the API.
            logger.warning('SGC poll deferred until the next interval')
        await asyncio.sleep(max(5, getattr(settings, 'sgc_poll_interval_seconds', 30)))
