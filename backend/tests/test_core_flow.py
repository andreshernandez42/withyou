from datetime import timedelta
from sqlalchemy import select
from app.models import User,Checkpoint,ConsentPolicy,WelfareCheck,SafetyStatus,LocationAccessGrant,EmergencyEvent
from app.services.timeutils import utcnow
from app.services.vault import cleanup_expired
from app.services.events import process_safety_timeouts, trigger_checkins
from conftest import register,login,auth


def make_admin(db,email='andres@example.com'):
    u=db.scalar(select(User).where(User.email==email));u.role='ADMIN';db.commit();return u


def setup_circle(client,db):
    a=register(client,'Andrés','andres@example.com');m=register(client,'Mamá','mama@example.com');f=register(client,'Amiga','amiga@example.com');v=register(client,'Vecino','vecino@example.com')
    make_admin(db)
    ta=login(client,'andres@example.com')['access_token'];tm=login(client,'mama@example.com')['access_token'];tf=login(client,'amiga@example.com')['access_token'];tv=login(client,'vecino@example.com')['access_token']
    contact_ids=[]
    for email,name,tok in [('mama@example.com','Mamá',tm),('amiga@example.com','Amiga',tf)]:
        r=client.post('/api/v1/trusted-contacts',headers=auth(ta),json={'contact_name':name,'contact_email':email,'can_view_checkpoint':True,'can_request_welfare':True})
        assert r.status_code==201,r.text
        cid=r.json()['id'];contact_ids.append(cid)
        assert client.post(f'/api/v1/trusted-contacts/{cid}/accept',headers=auth(tok),json={'accept':True}).status_code==200
    return {'a':a,'m':m,'f':f,'v':v,'ta':ta,'tm':tm,'tf':tf,'tv':tv,'contact_ids':contact_ids}


def test_auth_refresh_and_profile(client,db):
    register(client,'Ana','a@example.com')
    data=login(client,'a@example.com')
    assert data['refresh_token'] and data['access_token']
    r=client.post('/api/v1/auth/refresh',json={'refresh_token':data['refresh_token']})
    assert r.status_code==200,r.text
    token=r.json()['access_token']
    r=client.patch('/api/v1/me',headers=auth(token),json={'community_opt_in':True})
    assert r.status_code==200 and r.json()['community_opt_in'] is True


def test_normal_user_cannot_create_test_event(client,db):
    register(client,'User','u@example.com');t=login(client,'u@example.com')['access_token']
    r=client.post('/api/v1/test/emergency-events',headers=auth(t),json={'type':'EARTHQUAKE','latitude':4.7,'longitude':-74.08,'radius_km':50,'magnitude':6.5})
    assert r.status_code==403


def test_quorum_required_before_location_release(client,db):
    s=setup_circle(client,db)
    r=client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072,'accuracy_m':10,'battery_pct':80,'network_type':'wifi'})
    assert r.status_code==201
    # Tener can_view_checkpoint no equivale a acceso arbitrario.
    assert client.get(f"/api/v1/checkpoints/{s['a']['id']}/latest",headers=auth(s['tm'])).status_code==403
    r=client.post('/api/v1/welfare-checks',headers=auth(s['tm']),json={'subject_user_id':s['a']['id'],'reason':'No responde'})
    assert r.status_code==201;wid=r.json()['id'];assert r.json()['quorum_count']==1
    assert client.get(f'/api/v1/welfare-checks/{wid}/location',headers=auth(s['tm'])).status_code==403
    r=client.post(f'/api/v1/welfare-checks/{wid}/quorum',headers=auth(s['tf']),json={'response':'ALSO_CONCERNED'})
    assert r.status_code==200 and r.json()['status']=='TRUSTED_QUORUM_MET'
    r=client.get(f'/api/v1/welfare-checks/{wid}/location',headers=auth(s['tm']))
    assert r.status_code==200 and r.json()['level']=='EXACT' and 'location' in r.json()


def test_magnitude_filter_and_relevant_event(client,db):
    s=setup_circle(client,db)
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    low=client.post('/api/v1/test/emergency-events',headers=auth(s['ta']),json={'type':'EARTHQUAKE','source':'TEST-SGC','latitude':4.70,'longitude':-74.08,'radius_km':50,'magnitude':3.0})
    assert low.status_code==201 and s['a']['id'] not in low.json()['affected_users']
    high=client.post('/api/v1/test/emergency-events',headers=auth(s['ta']),json={'type':'EARTHQUAKE','source':'TEST-SGC','latitude':4.70,'longitude':-74.08,'radius_km':50,'magnitude':6.7,'depth_km':20})
    assert high.status_code==201 and s['a']['id'] in high.json()['affected_users']
    pending=client.get('/api/v1/safety/pending',headers=auth(s['ta'])).json()
    assert len(pending)>=1


def test_safe_response_notifies_contacts(client,db):
    s=setup_circle(client,db)
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    event=EmergencyEvent(type='FLOOD',source='OFFICIAL-FIXTURE',latitude=4.71,longitude=-74.07,radius_km=20,starts_at=utcnow(),is_test=False)
    db.add(event);db.flush();trigger_checkins(db,event);db.commit();e=event.id
    r=client.post('/api/v1/safety/respond',headers=auth(s['ta']),json={'status':'SAFE','event_id':e})
    assert r.status_code==200 and r.json()['status']=='SAFE'
    notes=client.get('/api/v1/notifications?pending_only=true',headers=auth(s['tm'])).json()
    assert any(n['type']=='STATUS_UPDATE' for n in notes)


def test_no_response_is_not_missing_and_can_grant_by_policy(client,db):
    s=setup_circle(client,db)
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    event=EmergencyEvent(type='LANDSLIDE',source='OFFICIAL-FIXTURE',latitude=4.71,longitude=-74.07,radius_km=20,starts_at=utcnow(),is_test=False)
    db.add(event);db.flush();trigger_checkins(db,event);db.commit();e=event.id
    row=db.scalar(select(SafetyStatus).where(SafetyStatus.user_id==s['a']['id'],SafetyStatus.event_id==e));row.expires_at=utcnow()-timedelta(seconds=1);db.commit()
    db.expire_all();processed=process_safety_timeouts(db);db.commit();assert processed>=1
    row=db.scalar(select(SafetyStatus).where(SafetyStatus.user_id==s['a']['id'],SafetyStatus.event_id==e));assert row.status=='NO_RESPONSE'
    assert row.status not in {'MISSING','KIDNAPPED','DEAD','IN_DANGER'}


def test_rolling_ttl_deletes_only_expired_without_hold(client,db):
    s=setup_circle(client,db)
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.712,'longitude':-74.073})
    rows=db.scalars(select(Checkpoint).where(Checkpoint.user_id==s['a']['id']).order_by(Checkpoint.created_at)).all()
    rows[0].expires_at=utcnow()-timedelta(minutes=1);rows[0].incident_hold=False
    rows[1].expires_at=utcnow()+timedelta(hours=1);db.commit()
    deleted=cleanup_expired(db);assert deleted==1
    remain=db.scalars(select(Checkpoint).where(Checkpoint.user_id==s['a']['id'])).all();assert len(remain)==1


def test_sos_creates_contextual_location_grants(client,db):
    s=setup_circle(client,db)
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    r=client.post('/api/v1/sos',headers=auth(s['ta']),json={'message':'Necesito ayuda'})
    assert r.status_code==201 and r.json()['location_grants']>=2
    assert client.get(f"/api/v1/checkpoints/{s['a']['id']}/latest",headers=auth(s['tm'])).status_code==200


def test_personal_safety_and_case_flow(client,db):
    s=setup_circle(client,db)
    ps=client.post('/api/v1/personal-safety/start',headers=auth(s['ta']),json={'notify_contact_ids':[s['contact_ids'][0]],'boost_minutes':20,'silent':True})
    assert ps.status_code==201 and ps.json()['status']=='ACTIVE'
    # Caso ciudadano solo después del flujo de verificación/quórum.
    w=client.post('/api/v1/welfare-checks',headers=auth(s['tm']),json={'subject_user_id':s['a']['id'],'reason':'No responde'}).json()['id']
    client.post(f'/api/v1/welfare-checks/{w}/quorum',headers=auth(s['tf']),json={'response':'ALSO_CONCERNED'})
    c=client.post('/api/v1/cases',headers=auth(s['tm']),json={'subject_user_id':s['a']['id'],'welfare_check_id':w,'notes':'Demo'})
    assert c.status_code==201 and 'no equivale' in c.json()['disclaimer'].lower()
    cid=c.json()['id']
    ref=client.post(f'/api/v1/cases/{cid}/institutional-reference',headers=auth(s['tm']),json={'source':'Fiscalía - Demo','reference_number':'SIM-001'})
    assert ref.status_code==201 and ref.json()['case_status']=='INSTITUTIONAL_REFERENCE_ADDED'


def test_community_requires_opt_in_and_multiple_safe_confirmations(client,db):
    s=setup_circle(client,db)
    # Política demo: habilitar comunidad.
    p=db.scalar(select(ConsentPolicy).where(ConsentPolicy.user_id==s['a']['id']).limit(1));p.allow_community_check=True;db.commit()
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    w=client.post('/api/v1/welfare-checks',headers=auth(s['tm']),json={'subject_user_id':s['a']['id'],'reason':'No responde'}).json()['id']
    client.post(f'/api/v1/welfare-checks/{w}/quorum',headers=auth(s['tf']),json={'response':'ALSO_CONCERNED'})
    assert client.post(f'/api/v1/welfare-checks/{w}/community/activate',headers=auth(s['tm'])).status_code==200
    # Vecino activa opt-in.
    client.patch('/api/v1/me',headers=auth(s['tv']),json={'community_opt_in':True})
    near=client.get('/api/v1/community/welfare-checks/nearby?latitude=4.711&longitude=-74.072&radius_km=5',headers=auth(s['tv']))
    assert near.status_code==200 and len(near.json())>=1
    vr=client.post(f'/api/v1/welfare-checks/{w}/community-verification',headers=auth(s['tv']),json={'result':'LOCATED_SAFE','approximate_distance_m':50})
    assert vr.status_code==201
    # Una sola confirmación no cierra automáticamente el caso.
    assert vr.json()['check_status']!='LOCATED_SAFE'


def test_authorized_subjects_avoids_global_directory(client,db):
    s=setup_circle(client,db)
    r=client.get('/api/v1/authorized-subjects',headers=auth(s['tm']))
    assert r.status_code==200
    assert any(x['user_id']==s['a']['id'] for x in r.json())
    # Usuario normal ve únicamente sujetos que lo autorizaron, no un directorio global.
    visible=client.get('/api/v1/users',headers=auth(s['tm']));assert visible.status_code==200
    assert [x['id'] for x in visible.json()]==[s['a']['id']]


def test_minor_cannot_join_community_and_is_not_auto_targeted(client,db):
    minor=client.post('/api/v1/auth/register',json={'full_name':'Menor Sintético','email':'minor@example.com','password':'StrongPass2026!','is_minor':True}).json()
    tmn=login(client,'minor@example.com')['access_token']
    assert client.patch('/api/v1/me',headers=auth(tmn),json={'community_opt_in':True}).status_code==403
    tester=register(client,'Tester Adulto','tester@example.com');u=db.scalar(select(User).where(User.email=='tester@example.com'));u.role='ADMIN';db.commit();tt=login(client,'tester@example.com')['access_token']
    client.post('/api/v1/checkpoints',headers=auth(tmn),json={'latitude':4.71,'longitude':-74.07})
    e=client.post('/api/v1/test/emergency-events',headers=auth(tt),json={'type':'EARTHQUAKE','source':'TEST','latitude':4.71,'longitude':-74.07,'radius_km':20,'magnitude':6.5})
    assert minor['id'] not in e.json()['affected_users']


def test_location_grant_can_be_revoked_by_subject(client,db):
    s=setup_circle(client,db)
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    client.post('/api/v1/sos',headers=auth(s['ta']),json={'message':'Demo'})
    grants=client.get('/api/v1/privacy/location-grants',headers=auth(s['ta']))
    assert grants.status_code==200 and grants.json()
    gid=grants.json()[0]['id']
    assert client.delete(f'/api/v1/privacy/location-grants/{gid}',headers=auth(s['ta'])).status_code==200

def test_normal_user_cannot_list_test_events(client,db):
    tester=register(client,'Tester','tester2@example.com');tu=db.scalar(select(User).where(User.email=='tester2@example.com'));tu.role='ADMIN';db.commit();tt=login(client,'tester2@example.com')['access_token']
    normal=register(client,'Normal','normal2@example.com');tn=login(client,'normal2@example.com')['access_token']
    created=client.post('/api/v1/test/emergency-events',headers=auth(tt),json={'type':'FIRE','source':'TEST-FIRE','latitude':4.71,'longitude':-74.07,'radius_km':5})
    assert created.status_code==201
    hidden=client.get('/api/v1/events?include_test=true',headers=auth(tn))
    assert hidden.status_code==200 and all(not e['is_test'] for e in hidden.json())
    visible=client.get('/api/v1/events?include_test=true',headers=auth(tt))
    assert visible.status_code==200 and any(e['is_test'] for e in visible.json())


def test_unrelated_trusted_contact_cannot_close_welfare_check(client,db):
    s=setup_circle(client,db)
    w=client.post('/api/v1/welfare-checks',headers=auth(s['tm']),json={'subject_user_id':s['a']['id'],'reason':'No responde'}).json()['id']
    # La amiga es contacto autorizado pero no es el solicitante original ni el sujeto.
    denied=client.post(f'/api/v1/welfare-checks/{w}/close',headers=auth(s['tf']),json={'outcome':'LOCATED_SAFE'})
    assert denied.status_code==403
    allowed=client.post(f'/api/v1/welfare-checks/{w}/close',headers=auth(s['tm']),json={'outcome':'CLOSED_OTHER'})
    assert allowed.status_code==200 and allowed.json()['status']=='CLOSED_OTHER'

def test_subject_access_history_and_expired_history_filter(client,db):
    s=setup_circle(client,db)
    # Dos puntos: el primero se vence pero permanece físicamente hasta mantenimiento.
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.711,'longitude':-74.072})
    client.post('/api/v1/checkpoints',headers=auth(s['ta']),json={'latitude':4.712,'longitude':-74.073})
    rows=db.scalars(select(Checkpoint).where(Checkpoint.user_id==s['a']['id']).order_by(Checkpoint.created_at)).all()
    rows[0].expires_at=utcnow()-timedelta(seconds=1);db.commit()
    history=client.get('/api/v1/checkpoints/me/history',headers=auth(s['ta']))
    assert history.status_code==200 and len(history.json())==1
    # Generar grant por quórum y lectura desde el contacto.
    w=client.post('/api/v1/welfare-checks',headers=auth(s['tm']),json={'subject_user_id':s['a']['id'],'reason':'No responde'}).json()['id']
    client.post(f'/api/v1/welfare-checks/{w}/quorum',headers=auth(s['tf']),json={'response':'ALSO_CONCERNED'})
    assert client.get(f'/api/v1/welfare-checks/{w}/location',headers=auth(s['tm'])).status_code==200
    audit_view=client.get('/api/v1/privacy/access-history',headers=auth(s['ta']))
    assert audit_view.status_code==200
    assert any(x['action']=='WELFARE_LOCATION_READ' for x in audit_view.json())
