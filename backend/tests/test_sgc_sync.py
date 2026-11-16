"""Ingestion regressions using real persistence and HTTP boundary substitutes."""
import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import httpx
from sqlalchemy import select, func
from app.models import EmergencyEvent, OfficialSourceSync, SafetyStatus, User
from app.services.sgc_sync import persist_sgc_items, sync_sgc_once
from app.services.timeutils import utcnow
from conftest import register, login, auth


def event(**changes):
    row = dict(external_id='sgc-official-1', magnitude=5.9, depth_km=10,
               latitude=4.7, longitude=-74.1, starts_at=utcnow(), raw={'official': True})
    row.update(changes)
    return row


def test_sync_idempotent_and_revision_updates(db):
    first = event()
    assert persist_sgc_items([first])['created'] == 1
    assert persist_sgc_items([first])['created'] == 0
    assert persist_sgc_items([dict(first, magnitude=6.1)])['updated'] == 1
    assert db.scalar(select(func.count(EmergencyEvent.id))) == 1
    assert db.scalar(select(EmergencyEvent)).magnitude == 6.1


def test_invalid_events_never_create_alerts(db):
    bad = [event(external_id=None), event(magnitude=float('nan')),
           event(starts_at=None), event(starts_at=utcnow()-timedelta(hours=2)),
           event(starts_at=utcnow()+timedelta(hours=2)), event(latitude=999)]
    result = persist_sgc_items(bad)
    assert result['created'] == 0
    assert {r['reason'] for r in result['rejected']} == {
        'missing_event_id', 'magnitude_filter', 'missing_event_time',
        'age_filter', 'future_event_time', 'invalid_geometry'}


def test_sync_failure_preserves_events_and_records_error(db, monkeypatch):
    persist_sgc_items([event()])
    monkeypatch.setattr('app.services.sgc_sync.SgcEarthquakeAdapter.fetch_recent',
                        AsyncMock(side_effect=httpx.ReadTimeout('upstream timeout')))
    try:
        asyncio.run(sync_sgc_once())
    except httpx.ReadTimeout:
        pass
    else:
        raise AssertionError('Failure must be explicit, not a false successful empty feed')
    assert db.scalar(select(func.count(EmergencyEvent.id))) == 1
    assert db.scalar(select(OfficialSourceSync).where(OfficialSourceSync.status == 'ERROR'))


def test_official_sgc_alert_reaches_user_once(client, db, monkeypatch):
    user = register(client, 'Ana', 'seismic@example.com')
    token = login(client, 'seismic@example.com')['access_token']
    headers = auth(token)
    assert client.post('/api/v1/checkpoints', headers=headers,
                       json={'latitude':4.7, 'longitude':-74.1}).status_code == 201
    monkeypatch.setattr('app.services.sgc_sync.SgcEarthquakeAdapter.fetch_recent',
                        AsyncMock(return_value=[event()]))
    assert asyncio.run(sync_sgc_once())['created'] == 1
    assert asyncio.run(sync_sgc_once())['created'] == 0
    pending = client.get('/api/v1/safety/pending', headers=headers)
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    assert db.scalar(select(func.count(SafetyStatus.id)).where(SafetyStatus.user_id == user['id'])) == 1


def test_sync_endpoint_admin_only_and_generic_error(client, db, monkeypatch):
    register(client, 'Admin', 'admin-sync@example.com')
    token = login(client, 'admin-sync@example.com')['access_token']
    headers = auth(token)
    assert client.post('/api/v1/events/sync/sgc', headers=headers).status_code == 403
    user = db.scalar(select(User).where(User.email == 'admin-sync@example.com'))
    user.role = 'TESTER'; db.commit()
    assert client.post('/api/v1/events/sync/sgc', headers=headers).status_code == 403
    user.role = 'ADMIN'; db.commit()
    monkeypatch.setattr('app.services.sgc_sync.SgcEarthquakeAdapter.fetch_recent', AsyncMock(return_value=[event()]))
    assert client.post('/api/v1/events/sync/sgc', headers=headers).status_code == 200
    monkeypatch.setattr('app.services.sgc_sync.SgcEarthquakeAdapter.fetch_recent', AsyncMock(side_effect=ValueError('secret internal detail')))
    failure = client.post('/api/v1/events/sync/sgc', headers=headers)
    assert failure.status_code == 502
    assert 'secret internal detail' not in failure.text
