import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os

TEST_DB=Path(__file__).parent/'test_v2.db'
if TEST_DB.exists():TEST_DB.unlink()
os.environ['DATABASE_URL']=f'sqlite:///{TEST_DB}'
os.environ['TOKEN_SECRET']='test-secret-123456789012345678901234567890'
os.environ['ALLOW_TEST_ENDPOINTS']='true'
os.environ['CELERY_ENABLED']='false'
os.environ['TRUSTED_HOSTS']='localhost,127.0.0.1,testserver'
os.environ['ALLOWED_ORIGINS']='http://localhost'
os.environ['SAFETY_CHECK_TIMEOUT_SECONDS']='1'

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base,engine,SessionLocal

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db():
    s=SessionLocal()
    try:yield s
    finally:s.close()


def register(client,name,email,password='StrongPass2026!'):
    r=client.post('/api/v1/auth/register',json={'full_name':name,'email':email,'password':password})
    assert r.status_code==201,r.text
    return r.json()


def login(client,email,password='StrongPass2026!'):
    r=client.post('/api/v1/auth/login',json={'email':email,'password':password})
    assert r.status_code==200,r.text
    return r.json()


def auth(token):return {'Authorization':f'Bearer {token}'}
