from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.api.router import api_router
from app.core.config import settings, validate_runtime_settings
from app.core.database import Base, engine, SessionLocal
from app.middleware.security import SecurityHeadersMiddleware
from app import models  # noqa: F401
from app.services.maintenance import maintenance_tick

def run_maintenance():
    with SessionLocal() as db:
        try:
            maintenance_tick(db)
        except Exception:
            db.rollback()
            logging.getLogger(__name__).exception('Maintenance failed')


async def maintenance_loop():
    while True:
        await asyncio.sleep(settings.cleanup_interval_seconds)
        await asyncio.to_thread(run_maintenance)


@asynccontextmanager
async def lifespan(app:FastAPI):
    validate_runtime_settings()
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    tasks = []
    if not settings.celery_enabled:
        tasks.append(asyncio.create_task(maintenance_loop()))
        if getattr(settings, 'sgc_poll_enabled', True):
            from app.services.sgc_sync import sgc_poll_loop
            tasks.append(asyncio.create_task(sgc_poll_loop()))
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

app=FastAPI(
    title=settings.app_name,
    version='1.0.0-mvp',
    lifespan=lifespan,
    description='Backend del MVP académico With You: continuidad personal, bienestar, localización mínima y escalamiento controlado.',
    docs_url='/docs' if not settings.is_production else None,
    redoc_url='/redoc' if not settings.is_production else None,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=list(settings.trusted_hosts) or ['*'])
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],
    allow_headers=['Authorization','Content-Type','X-Request-ID'],
)
app.include_router(api_router,prefix=settings.api_prefix)

@app.get('/')
def root():
    return {'name':settings.app_name,'version':'1.0.0-mvp','docs':'/docs' if not settings.is_production else None,'health':f'{settings.api_prefix}/health'}

@app.get(f'{settings.api_prefix}/health')
def health():
    return {'status':'ok','service':settings.app_name,'env':settings.env,'version':'1.0.0-mvp'}

@app.get(f'{settings.api_prefix}/health/live')
def liveness():
    return {'status':'alive','service':settings.app_name,'version':'1.0.0-mvp'}

@app.get(f'{settings.api_prefix}/health/ready')
def readiness():
    # Readiness comprueba que la API puede hablar con su source of truth.
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {'status':'ready','database':'ok'}
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503,detail='database_unavailable') from exc
