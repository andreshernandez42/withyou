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
