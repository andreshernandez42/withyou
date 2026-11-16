from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import encrypt_json
from app.models import Checkpoint, ConsentPolicy, EmergencyEvent, LocationAccessGrant, Notification, SafetyStatus
from app.services import events
from app.services.timeutils import utcnow
from conftest import auth
from test_core_flow import setup_circle


def make_event(db, *, is_test):
    event = EmergencyEvent(source='TEST-SGC' if is_test else 'SGC', type='EARTHQUAKE',
                           is_test=is_test, status='ACTIVE', latitude=4.711, longitude=-74.072,
                           magnitude=6, radius_km=100, starts_at=utcnow())
    db.add(event)
    db.flush()
    events.trigger_checkins(db, event)
    db.commit()
    return event


@pytest.mark.parametrize('status', ['SAFE', 'HELP_REQUIRED', 'UNABLE_TO_EXIT'])
@pytest.mark.parametrize('is_test', [True, False])
def test_responses_isolate_simulation_side_effects(client, db, status, is_test):
    circle = setup_circle(client, db)
    cp = client.post('/api/v1/checkpoints', headers=auth(circle['ta']),
                     json={'latitude':4.711, 'longitude':-74.072}).json()
    event = make_event(db, is_test=is_test)
    response = client.post('/api/v1/safety/respond', headers=auth(circle['ta']),
                           json={'status':status, 'event_id':event.id})
    assert response.status_code == 200
    notes = db.scalars(select(Notification).where(Notification.user_id.in_([circle['m']['id'],circle['f']['id']]))).all()
    status_notes = [n for n in notes if n.type == 'STATUS_UPDATE']
    grants = db.scalars(select(LocationAccessGrant)).all()
    db.expire_all()
    checkpoint = db.get(Checkpoint, cp['id'])
    if is_test:
        assert status_notes == []
        assert grants == []
        assert checkpoint.incident_hold is False
    else:
        assert len(status_notes) == 2
        assert checkpoint.incident_hold is True
        if status != 'SAFE':
            assert len(grants) == 2


@pytest.mark.parametrize('is_test', [True, False])
def test_timeout_isolates_simulation_even_with_preauthorized_release(client, db, is_test):
    circle = setup_circle(client, db)
    client.post('/api/v1/checkpoints', headers=auth(circle['ta']), json={'latitude':4.711, 'longitude':-74.072})
    policy = db.scalar(select(ConsentPolicy).where(ConsentPolicy.user_id == circle['a']['id']))
    policy.release_on_official_event_no_response = True
    db.commit()
    event = make_event(db, is_test=is_test)
    check = db.scalar(select(SafetyStatus).where(SafetyStatus.event_id == event.id))
    check.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert events.process_safety_timeouts(db) == 1
    db.commit()
    notes = db.scalars(select(Notification).where(Notification.type == 'NO_RESPONSE')).all()
    grants = db.scalars(select(LocationAccessGrant)).all()
    assert len(notes) == (0 if is_test else 2)
    assert len(grants) == (0 if is_test else 2)
    assert check.status == 'NO_RESPONSE'
    timeout_note = db.scalar(select(Notification).where(Notification.type == 'SAFETY_CHECK_TIMEOUT'))
    assert timeout_note is not None
    import json
    assert json.loads(timeout_note.metadata_json)['is_test'] == is_test


@pytest.mark.parametrize('minutes,expected', [(59, True), (60, True), (61, False)])
def test_earthquake_uses_fresh_checkpoint_not_retention_window(monkeypatch, minutes, expected):
    now = utcnow()
    monkeypatch.setattr(events, 'utcnow', lambda: now)
    event = EmergencyEvent(type='EARTHQUAKE', status='ACTIVE', latitude=4.711, longitude=-74.072,
                           magnitude=6, radius_km=100, starts_at=now, is_test=False)
    checkpoint = Checkpoint(created_at=now - timedelta(minutes=minutes),
                            encrypted_location=encrypt_json({'lat':4.711,'lon':-74.072}))
    relevant, _, reason = events.event_is_relevant(event, checkpoint)
    assert relevant is expected
    if not expected:
        assert reason == 'stale_checkpoint'


def test_cannot_reply_to_unassigned_official_event(client, db):
    circle = setup_circle(client, db)
    event = make_event(db, is_test=False)
    response = client.post('/api/v1/safety/respond', headers=auth(circle['ta']),
                           json={'status':'HELP_REQUIRED', 'event_id':event.id})
    assert response.status_code == 404
    assert db.scalars(select(LocationAccessGrant)).all() == []
