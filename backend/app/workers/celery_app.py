from celery import Celery
from app.core.config import settings

celery_app=Celery('withyou',broker=settings.redis_url,backend=settings.redis_url)
celery_app.conf.update(
    timezone='UTC',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    beat_schedule={
        'maintenance-every-minute':{
            'task':'app.workers.tasks.maintenance_task',
            'schedule':max(15,settings.cleanup_interval_seconds),
        }
    },
)
