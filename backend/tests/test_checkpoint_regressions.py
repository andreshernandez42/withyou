from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import Checkpoint
from app.services import vault
from app.services.timeutils import as_utc, utcnow
from conftest import auth, login, register


@pytest.fixture
def owner(client):
    person = register(client, 'Checkpoint owner', 'checkpoint@example.com')
    headers = auth(login(client, 'checkpoint@example.com')['access_token'])
    return person, headers


@pytest.mark.parametrize('hold_offset', [-1, 0, None])
def test_expired_hold_is_never_readable_before_cleanup(client, db, owner, monkeypatch, hold_offset):
    person, headers = owner
    created = client.post('/api/v1/checkpoints', headers=headers,
                          json={'latitude': 4.71, 'longitude': -74.07}).json()
    now = utcnow()
    monkeypatch.setattr(vault, 'utcnow', lambda: now)
    checkpoint = db.get(Checkpoint, created['id'])
    checkpoint.expires_at = now - timedelta(hours=1)
    checkpoint.incident_hold = True
    checkpoint.hold_expires_at = None if hold_offset is None else now + timedelta(seconds=hold_offset)
    db.commit()

    assert client.get('/api/v1/checkpoints/me/latest', headers=headers).status_code == 404
    assert client.get('/api/v1/checkpoints/me/history', headers=headers).json() == []
    assert vault.cleanup_expired(db) == 1
    assert db.scalar(select(Checkpoint).where(Checkpoint.id == created['id'])) is None


def test_live_hold_preserves_location_until_release(client, db, owner, monkeypatch):
    person, headers = owner
    created = client.post('/api/v1/checkpoints', headers=headers,
                          json={'latitude': 4.71, 'longitude': -74.07}).json()
    now = utcnow()
    monkeypatch.setattr(vault, 'utcnow', lambda: now)
    checkpoint = db.get(Checkpoint, created['id'])
    checkpoint.expires_at = now - timedelta(hours=1)
    checkpoint.incident_hold = True
    checkpoint.hold_expires_at = now + timedelta(hours=1)
    db.commit()

    response = client.get('/api/v1/checkpoints/me/latest', headers=headers)
    assert response.status_code == 200
    assert response.json()['location'] == {'lat': 4.71, 'lon': -74.07}
    assert len(client.get('/api/v1/checkpoints/me/history', headers=headers).json()) == 1
    assert vault.cleanup_expired(db) == 0
    vault.release_incident_hold(db, checkpoint, person['id'], 'Resolved')
    db.commit()
    assert client.get('/api/v1/checkpoints/me/latest', headers=headers).status_code == 404


def test_expired_offline_upload_is_rejected_without_persisting(client, db, owner):
    _, headers = owner
    old = utcnow() - timedelta(hours=settings.checkpoint_ttl_hours, minutes=1)
    response = client.post('/api/v1/checkpoints', headers=headers,
                           json={'latitude': 4.71, 'longitude': -74.07, 'created_at': old.isoformat()})
    assert response.status_code == 400
    assert db.scalars(select(Checkpoint)).all() == []


def test_offline_upload_keeps_original_ttl_and_survives_new_session(client, db, owner):
    _, headers = owner
    captured = utcnow() - timedelta(hours=2)
    response = client.post('/api/v1/checkpoints', headers=headers,
                           json={'latitude': 4.711234, 'longitude': -74.071234, 'created_at': captured.isoformat()})
    assert response.status_code == 201
    persisted = db.get(Checkpoint, response.json()['id'])
    assert as_utc(persisted.expires_at) == captured + timedelta(hours=settings.checkpoint_ttl_hours)
    assert '4.711234' not in persisted.encrypted_location
    db.expire_all()
    restored = client.get('/api/v1/checkpoints/me/latest', headers=headers).json()
    assert restored['id'] == response.json()['id']
    assert restored['location'] == {'lat': 4.711234, 'lon': -74.071234}
