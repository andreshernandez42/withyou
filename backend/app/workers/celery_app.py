from celery import Celery
from app.core.config import settings

celery_app=Celery('withyou',broker=settings.redis_url,backend=settings.redis_url,include=['app.workers.tasks'])
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

if getattr(settings, 'sgc_poll_enabled', True):
    celery_app.conf.beat_schedule['sgc-poll'] = {
        'task': 'app.workers.tasks.sgc_poll_task',
        'schedule': max(5, getattr(settings, 'sgc_poll_interval_seconds', 30)),
        'options': {'expires': max(5, getattr(settings, 'sgc_poll_interval_seconds', 30))},
    }
