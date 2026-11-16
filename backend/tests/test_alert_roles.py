from sqlalchemy import select
from app.models import User, Notification
from conftest import register, login, auth


def test_simulations_do_not_notify_standard_users_and_replies_are_idempotent(client, db):
    a = register(client, 'Admin', 'admin-alert@example.com')
    register(client, 'User', 'user-alert@example.com')
    user = db.get(User, a['id']); user.role = 'ADMIN'; db.commit()
    ha = auth(login(client, 'admin-alert@example.com')['access_token'])
    hu = auth(login(client, 'user-alert@example.com')['access_token'])
    for h in [ha, hu]:
        assert client.post('/api/v1/checkpoints', headers=h, json={'latitude': 4.7, 'longitude': -74.1}).status_code == 201
    result = client.post('/api/v1/test/emergency-events', headers=ha,
        json={'type': 'EARTHQUAKE', 'latitude': 4.7, 'longitude': -74.1, 'magnitude': 6})
    assert result.status_code == 201
    event = result.json()['event_id']
    assert client.get('/api/v1/safety/pending', headers=hu).json() == []
    assert client.get('/api/v1/events/' + event, headers=hu).status_code == 404
    pending = client.get('/api/v1/safety/pending', headers=ha).json()[0]
    assert pending['is_test'] is True and pending['expires_at'].endswith(('+00:00', 'Z'))
    first = client.post('/api/v1/safety/respond', headers=ha, json={'status':'SAFE', 'event_id': event})
    second = client.post('/api/v1/safety/respond', headers=ha, json={'status':'SAFE', 'event_id': event})
    assert first.status_code == second.status_code == 200
    assert first.json()['id'] == second.json()['id']
    assert client.post('/api/v1/safety/respond', headers=hu, json={'status':'SAFE', 'event_id': event}).status_code == 404
    for path in ['/audit-logs', '/metrics/summary', '/experiments/runs']:
        assert client.get('/api/v1' + path, headers=hu).status_code == 403
