"""Pruebas offline con respuestas ArcGIS controladas; no requieren acceso al SGC."""
import asyncio
from datetime import timedelta

import httpx
from sqlalchemy import select

from app.adapters.sgc import SgcEarthquakeAdapter
from app.models import EmergencyEvent, LocationAccessGrant, SafetyStatus
from app.services.events import process_safety_timeouts
from app.services.timeutils import utcnow
from conftest import auth, login, register


def test_arcgis_recent_time_filter_without_objectid_pagination(monkeypatch):
    calls = []

    def respond(request):
        calls.append(str(request.url))
        if request.url.path.endswith('/0'):
            return httpx.Response(200, json={
                'geometryType': 'esriGeometryPoint',
                'fields': [{'name': 'ESP_FECHA_LONG', 'type': 'esriFieldTypeDouble'}],
            })
        if request.url.params.get('returnIdsOnly') == 'true':
            assert 'ESP_FECHA_LONG >=' in request.url.params['where']
            assert 'resultRecordCount' not in request.url.params
            assert 'orderByFields' not in request.url.params
            return httpx.Response(200, json={'objectIds': [11]})
        assert request.url.params.get('outSR') == '4326'
        return httpx.Response(200, json={'features': [{
            'attributes': {
                'OBJECTID': 11, 'ESP_MAGNITUD': 5.6,
                'ESP_PROFUNDIDAD': 19,
                'ESP_FECHA_LONG': int(utcnow().timestamp() * 1000),
            }, 'geometry': {'x': -74.08, 'y': 4.71},
        }]})

    original = httpx.AsyncClient
    def make_client(*args, **kwargs):
        return original(transport=httpx.MockTransport(respond), **kwargs)
    monkeypatch.setattr('app.adapters.sgc.httpx.AsyncClient', make_client)
    rows = asyncio.run(SgcEarthquakeAdapter().fetch_recent())
    assert len(rows) == 1
    assert rows[0]['magnitude'] == 5.6
    assert rows[0]['starts_at'] is not None
    assert len(calls) == 3


def test_arcgis_error_never_returns_fake_events(monkeypatch):
    original = httpx.AsyncClient
    def make_client(*args, **kwargs):
        return original(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={'error': {'code': 400, 'message': 'Bad layer'}})), **kwargs)
    monkeypatch.setattr('app.adapters.sgc.httpx.AsyncClient', make_client)
    try:
        asyncio.run(SgcEarthquakeAdapter().fetch_recent())
        assert False, 'No debe aceptar respuestas ArcGIS con error'
    except ValueError as error:
        assert 'ArcGIS' in str(error)


def test_sgc_ingest_recent_event_and_deduplicate(client, db, monkeypatch):
    register(client, 'Tester', 'tester-sgc@example.com')
    from app.models import User
    tester = db.scalar(select(User).where(User.email == 'tester-sgc@example.com'))
    tester.role = 'TESTER'
    db.commit()
    token = login(client, 'tester-sgc@example.com')['access_token']
    client.post('/api/v1/checkpoints', headers=auth(token),
                json={'latitude': 4.71, 'longitude': -74.08})

    async def recent(self, limit=100):
        return [{
            'external_id': 'real-sgc-100', 'magnitude': 6.2, 'depth_km': 12,
            'latitude': 4.71, 'longitude': -74.08,
            'starts_at': utcnow() - timedelta(minutes=2), 'raw': {'source': 'fixture'},
        }]

    monkeypatch.setattr(SgcEarthquakeAdapter, 'fetch_recent', recent)
    first = client.post('/api/v1/events/sync/sgc', headers=auth(token))
    assert first.status_code == 200, first.text
    assert first.json()['created'] == 1
    assert first.json()['events'][0]['affected'] == 1
    second = client.post('/api/v1/events/sync/sgc', headers=auth(token))
    assert second.status_code == 200
    assert second.json()['created'] == 0
    events = client.get('/api/v1/events', headers=auth(token)).json()
    assert len(events) == 1 and events[0]['source'] == 'SGC' and not events[0]['is_test']


def test_sgc_rejects_missing_old_and_future_dates(client, db, monkeypatch):
    register(client, 'Tester', 'tester-sgc@example.com')
    from app.models import User
    tester = db.scalar(select(User).where(User.email == 'tester-sgc@example.com'))
    tester.role = 'TESTER'; db.commit()
    token = login(client, 'tester-sgc@example.com')['access_token']

    async def events(self, limit=100):
        return [
            {'external_id': 'no-time', 'magnitude': 6.2, 'latitude': 4.7, 'longitude': -74.1, 'starts_at': None},
            {'external_id': 'old', 'magnitude': 6.2, 'latitude': 4.7, 'longitude': -74.1, 'starts_at': utcnow() - timedelta(days=2)},
            {'external_id': 'future', 'magnitude': 6.2, 'latitude': 4.7, 'longitude': -74.1, 'starts_at': utcnow() + timedelta(hours=2)},
        ]

    monkeypatch.setattr(SgcEarthquakeAdapter, 'fetch_recent', events)
    response = client.post('/api/v1/events/sync/sgc', headers=auth(token))
    assert response.status_code == 200
    assert response.json()['created'] == 0
    assert {r['reason'] for r in response.json()['rejected']} == {
        'missing_event_time', 'age_filter', 'future_event_time',
    }


def test_test_event_never_releases_location_to_regular_contacts(client, db):
    from test_core_flow import setup_circle
    group = setup_circle(client, db)
    client.post('/api/v1/checkpoints', headers=auth(group['ta']),
                json={'latitude': 4.71, 'longitude': -74.08})
    event = client.post('/api/v1/test/emergency-events', headers=auth(group['ta']),
        json={'type': 'EARTHQUAKE', 'latitude': 4.71, 'longitude': -74.08,
              'radius_km': 40, 'magnitude': 6.4}).json()['event_id']
    status = db.scalar(select(SafetyStatus).where(SafetyStatus.event_id == event))
    status.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    process_safety_timeouts(db)
    db.commit()
    assert db.scalars(select(LocationAccessGrant).where(
        LocationAccessGrant.source_type == 'EMERGENCY_EVENT',
        LocationAccessGrant.source_id == event)).all() == []
    normal_notes = client.get('/api/v1/notifications', headers=auth(group['tm'])).json()
    assert not any(note['type'] == 'NO_RESPONSE' for note in normal_notes)


def test_sgc_status_endpoint_requires_authentication(client):
    assert client.get('/api/v1/official/sgc/status').status_code == 401
    register(client, 'User', 'status@example.com')
    token = login(client, 'status@example.com')['access_token']
    response = client.get('/api/v1/official/sgc/status', headers=auth(token))
    assert response.status_code == 200
    assert response.json()['source'] == 'SGC'
    assert response.json()['recent_feed_verified'] is False
