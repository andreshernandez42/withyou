import os
from pathlib import Path

TEST_DB = Path(__file__).parent / 'test.db'
if TEST_DB.exists(): TEST_DB.unlink()
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB}'
os.environ['TOKEN_SECRET'] = 'test-secret-123456'
os.environ['ALLOW_TEST_ENDPOINTS'] = 'true'

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.models import Checkpoint
from app.services.vault import cleanup_expired
from datetime import timedelta
from app.services.common import utcnow

client = TestClient(app)

def register(name,email,password='StrongPass2026!'):
    r=client.post('/api/v1/auth/register',json={'full_name':name,'email':email,'password':password})
    assert r.status_code==200, r.text
    return r.json()

def login(email,password='StrongPass2026!'):
    r=client.post('/api/v1/auth/login',json={'email':email,'password':password})
    assert r.status_code==200, r.text
    return r.json()['access_token']

def auth(t): return {'Authorization':f'Bearer {t}'}

def test_full_flow():
    with client:
        a=register('Andrés','andres@example.com')
        m=register('Mamá','mama@example.com')
        f=register('Amiga','amiga@example.com')
        x=register('Externo','externo@example.com')
        ta,tm,tf,tx=[login(e) for e in ['andres@example.com','mama@example.com','amiga@example.com','externo@example.com']]

        for email,name,tok in [('mama@example.com','Mamá',tm),('amiga@example.com','Amiga',tf)]:
            r=client.post('/api/v1/trusted-contacts',headers=auth(ta),json={'contact_name':name,'contact_email':email,'can_view_checkpoint':True})
            assert r.status_code==200, r.text
            cid=r.json()['id']
            r=client.post(f'/api/v1/trusted-contacts/{cid}/accept',headers=auth(tok),json={'accept':True})
            assert r.status_code==200, r.text

        r=client.post('/api/v1/checkpoints',headers=auth(ta),json={'latitude':4.7110,'longitude':-74.0721,'accuracy_m':12,'battery_pct':80,'network_type':'wifi','movement_state':'MOVING'})
        assert r.status_code==200, r.text
        assert 'location' in r.json()

        r=client.get(f"/api/v1/checkpoints/{a['id']}/latest",headers=auth(tx))
        assert r.status_code==403

        r=client.post('/api/v1/test/emergency-events',headers=auth(ta),json={'type':'EARTHQUAKE','source':'TEST-SGC','severity':'SEVERE','latitude':4.70,'longitude':-74.08,'radius_km':50,'magnitude':6.7,'depth_km':20})
        assert r.status_code==200, r.text
        assert a['id'] in r.json()['affected_users']
        event_id=r.json()['event_id']

        r=client.get('/api/v1/notifications?pending_only=true',headers=auth(ta))
        assert any(n['type']=='SAFETY_CHECK' for n in r.json())

        r=client.post('/api/v1/safety/respond',headers=auth(ta),json={'status':'SAFE','event_id':event_id})
        assert r.status_code==200
        r=client.get('/api/v1/notifications?pending_only=true',headers=auth(tm))
        assert any(n['type']=='STATUS_UPDATE' for n in r.json())

        r=client.post('/api/v1/welfare-checks',headers=auth(tm),json={'subject_user_id':a['id'],'reason':'No responde mensajes'})
        assert r.status_code==200, r.text
        check_id=r.json()['id']
        assert r.json()['quorum_required']==2

        r=client.post(f'/api/v1/welfare-checks/{check_id}/quorum',headers=auth(tf),json={'response':'ALSO_CONCERNED'})
        assert r.status_code==200, r.text
        assert r.json()['status']=='TRUSTED_QUORUM_MET'
        assert r.json()['quorum_count']>=2

        r=client.post('/api/v1/cases',headers=auth(tm),json={'subject_user_id':a['id'],'notes':'Caso de demostración'})
        assert r.status_code==200, r.text
        case_id=r.json()['id']
        assert 'no equivale' in r.json()['note']

        r=client.post(f'/api/v1/cases/{case_id}/institutional-reference',headers=auth(tm),json={'source':'Fiscalía - Demo','reference_number':'SIM-001','status':'REGISTERED'})
        assert r.status_code==200
        assert r.json()['case_status']=='INSTITUTIONAL_REFERENCE_ADDED'

        contacts=client.get('/api/v1/trusted-contacts',headers=auth(ta)).json()
        r=client.post('/api/v1/personal-safety/start',headers=auth(ta),json={'notify_contact_ids':[contacts[0]['id']], 'boost_minutes':20})
        assert r.status_code==200

        db=SessionLocal()
        cp=db.query(Checkpoint).filter_by(user_id=a['id']).first()
        cp.expires_at=utcnow()-timedelta(minutes=1)
        cp.incident_hold=False
        db.commit(); db.close()
        db=SessionLocal(); deleted=cleanup_expired(db); db.close()
        assert deleted>=1
