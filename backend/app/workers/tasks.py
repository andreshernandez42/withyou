from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.maintenance import maintenance_tick

@celery_app.task(name='app.workers.tasks.maintenance_task')
def maintenance_task():
    db=SessionLocal()
    try:
        return maintenance_tick(db)
    finally:
        db.close()


@celery_app.task(name='app.workers.tasks.sgc_poll_task', max_retries=2)
def sgc_poll_task():
    """Sondeo oficial, protegido contra ejecución simultánea con Redis."""
    import asyncio
    import logging
    from redis import Redis
    from app.core.config import settings
    from app.services.sgc_sync import sync_sgc_events

    if not settings.sgc_poll_enabled:
        return {"status": "disabled"}
    redis = Redis.from_url(settings.redis_url)
    lock = redis.lock('withyou:sgc:poll', timeout=90, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        return {"status": "already_running"}
    try:
        db = SessionLocal()
        try:
            return asyncio.run(sync_sgc_events(db))
        except Exception:
            db.rollback()
            logging.getLogger(__name__).exception('SGC polling failed; no alerts created')
            raise
        finally:
            db.close()
    finally:
        try:
            lock.release()
        except Exception:
            logging.getLogger(__name__).warning('SGC poll lock already expired')
