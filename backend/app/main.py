from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app import models  # noqa: F401
from app.services.vault import cleanup_expired

async def cleanup_loop():
    while True:
        await asyncio.sleep(settings.cleanup_interval_seconds)
        db=SessionLocal()
        try: cleanup_expired(db)
        except Exception: db.rollback()
        finally: db.close()

@asynccontextmanager
async def lifespan(app:FastAPI):
    Base.metadata.create_all(bind=engine)
    task=asyncio.create_task(cleanup_loop())
    yield
    task.cancel()

app=FastAPI(title=settings.app_name,version='0.1.0',lifespan=lifespan,description='MVP académico para continuidad personal, bienestar y localización mínima.')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(router,prefix=settings.api_prefix)

@app.get('/')
def root():
    return {"name":settings.app_name,"docs":"/docs","health":f"{settings.api_prefix}/health"}
