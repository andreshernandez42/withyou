from __future__ import annotations
import json
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models import (
    User, TrustedContact, ConsentPolicy, EmergencyEvent, SafetyStatus, WelfareCheck,
    Notification, DisappearanceCase, InstitutionalReference, CommunityVerification,
    PersonalSafetySession,
)
from app.schemas.api import (
    RegisterIn, LoginIn, ContactCreate, ContactAccept, PolicyIn, CheckpointIn, TestEventIn,
    SafetyResponseIn, WelfareRequestIn, WelfareConfirmIn, CommunityVerificationIn,
    CaseCreateIn, InstitutionalReferenceIn, SafetyModeIn,
)
from app.services.common import utcnow, audit, notify
from app.services.vault import create_checkpoint, latest_checkpoint, checkpoint_public
from app.services.events import trigger_checkins
from app.services.welfare import request_welfare, confirm_quorum
from app.services.policy import contact_relation, default_policy
from app.adapters.sirdec import SirdecOpenDataAdapter
from app.adapters.sgc import SgcEarthquakeAdapter
from app.adapters.ideam import IdeamAdapter

router = APIRouter()

@router.get('/health')
def health():
    return {"status":"ok","service":settings.app_name,"env":settings.env}

@router.post('/auth/register')
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, 'El correo ya está registrado')
    user = User(full_name=payload.full_name, email=payload.email.lower(), password_hash=hash_password(payload.password), is_minor=payload.is_minor)
    db.add(user); db.flush()
    db.add(ConsentPolicy(user_id=user.id, quorum_required=2, allow_exact_location=True))
    audit(db, user.id, 'USER_REGISTER', 'user', user.id)
    db.commit()
    return {"id":user.id,"full_name":user.full_name,"email":user.email,"is_minor":user.is_minor}

@router.post('/auth/login')
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Credenciales inválidas')
    token = create_access_token(user.id, user.email)
    audit(db, user.id, 'LOGIN', 'user', user.id); db.commit()
    return {"access_token":token,"token_type":"bearer","user":{"id":user.id,"full_name":user.full_name,"email":user.email,"is_minor":user.is_minor}}

@router.get('/me')
def me(user: User = Depends(current_user)):
    return {"id":user.id,"full_name":user.full_name,"email":user.email,"is_minor":user.is_minor,"status":user.status}

@router.get('/users')
def users(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.id != user.id, User.status == 'ACTIVE')).all()
    return [{"id":r.id,"full_name":r.full_name,"email":r.email,"is_minor":r.is_minor} for r in rows]

@router.post('/trusted-contacts')
def create_contact(payload: ContactCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    target = db.scalar(select(User).where(User.email == payload.contact_email.lower()))
    row = TrustedContact(owner_user_id=user.id, contact_user_id=target.id if target else None,
                         contact_name=payload.contact_name, contact_email=payload.contact_email.lower(),
                         status='PENDING', can_receive_sos=payload.can_receive_sos,
                         can_view_checkpoint=payload.can_view_checkpoint, can_request_welfare=payload.can_request_welfare,
                         quorum_weight=payload.quorum_weight)
    db.add(row); db.flush()
    if target:
        notify(db,target.id,'CONTACT_INVITE',f'{user.full_name} te agregó a su círculo de confianza','Acepta o rechaza la invitación.',{"contact_id":row.id})
    audit(db,user.id,'TRUSTED_CONTACT_CREATE','trusted_contact',row.id)
    db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"contact_name":row.contact_name,"contact_email":row.contact_email}

@router.get('/trusted-contacts')
def list_contacts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(TrustedContact).where(TrustedContact.owner_user_id == user.id)).all()
    return [{"id":r.id,"contact_user_id":r.contact_user_id,"contact_name":r.contact_name,"contact_email":r.contact_email,"status":r.status,
             "can_receive_sos":r.can_receive_sos,"can_view_checkpoint":r.can_view_checkpoint,"can_request_welfare":r.can_request_welfare,"quorum_weight":r.quorum_weight} for r in rows]

@router.get('/trusted-contacts/invitations')
def invitations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(TrustedContact).where(TrustedContact.contact_user_id == user.id, TrustedContact.status == 'PENDING')).all()
    return [{"id":r.id,"owner_user_id":r.owner_user_id,"contact_name":r.contact_name,"contact_email":r.contact_email} for r in rows]

@router.post('/trusted-contacts/{contact_id}/accept')
def accept_contact(contact_id: str, payload: ContactAccept, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(TrustedContact, contact_id)
    if not row or row.contact_user_id != user.id:
        raise HTTPException(404, 'Invitación no encontrada')
    row.status = 'ACCEPTED' if payload.accept else 'REJECTED'
    audit(db,user.id,'TRUSTED_CONTACT_DECISION','trusted_contact',row.id,metadata={"accepted":payload.accept}); db.commit()
    return {"id":row.id,"status":row.status}

@router.get('/policies')
def policies(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows=db.scalars(select(ConsentPolicy).where(ConsentPolicy.user_id==user.id)).all()
    return [{"id":r.id,"name":r.name,"event_type":r.event_type,"quorum_required":r.quorum_required,"allow_exact_location":r.allow_exact_location,"allow_recent_route":r.allow_recent_route,"active":r.active} for r in rows]

@router.post('/policies')
def create_policy(payload: PolicyIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row=ConsentPolicy(user_id=user.id,**payload.model_dump())
    db.add(row); db.flush(); audit(db,user.id,'POLICY_CREATE','policy',row.id); db.commit();
    return {"id":row.id,**payload.model_dump()}

@router.post('/checkpoints')
def post_checkpoint(payload: CheckpointIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row=create_checkpoint(db,user.id,payload); db.commit(); db.refresh(row)
    return checkpoint_public(row, include_exact=True)

@router.get('/checkpoints/me/latest')
def my_latest(user: User = Depends(current_user), db: Session = Depends(get_db)):
    cp=latest_checkpoint(db,user.id)
    if not cp: raise HTTPException(404,'Sin checkpoints')
    return checkpoint_public(cp,include_exact=True)

@router.get('/checkpoints/{subject_user_id}/latest')
def contact_latest(subject_user_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rel=contact_relation(db,subject_user_id,user.id)
    if not rel or not rel.can_view_checkpoint:
        audit(db,user.id,'CHECKPOINT_READ','checkpoint',None,result='DENIED',reason='policy_not_satisfied',metadata={"subject":subject_user_id}); db.commit()
        raise HTTPException(403,'La política no autoriza consultar ubicación')
    cp=latest_checkpoint(db,subject_user_id)
    if not cp: raise HTTPException(404,'Sin checkpoints')
    audit(db,user.id,'CHECKPOINT_READ','checkpoint',cp.id,metadata={"subject":subject_user_id}); db.commit()
    return checkpoint_public(cp,include_exact=True)

@router.post('/test/emergency-events')
def test_event(payload: TestEventIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not settings.allow_test_endpoints: raise HTTPException(404,'Endpoints de prueba deshabilitados')
    row=EmergencyEvent(**payload.model_dump(),is_test=True,raw_payload=json.dumps(payload.model_dump(),default=str))
    db.add(row); db.flush(); affected=trigger_checkins(db,row); audit(db,user.id,'TEST_EVENT_CREATE','event',row.id); db.commit();
    return {"event_id":row.id,"is_test":True,"affected_users":affected}

@router.get('/events')
def list_events(limit:int=Query(20,ge=1,le=100), user: User = Depends(current_user), db: Session=Depends(get_db)):
    rows=db.scalars(select(EmergencyEvent).order_by(EmergencyEvent.created_at.desc()).limit(limit)).all()
    return [{"id":r.id,"source":r.source,"type":r.type,"severity":r.severity,"magnitude":r.magnitude,"depth_km":r.depth_km,"latitude":r.latitude,"longitude":r.longitude,"radius_km":r.radius_km,"is_test":r.is_test,"starts_at":r.starts_at} for r in rows]

@router.post('/events/sync/sgc')
async def sync_sgc(user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        items=await SgcEarthquakeAdapter().fetch_recent(50)
    except Exception as e:
        raise HTTPException(502,f'No fue posible consultar SGC: {e}')
    created=[]
    for item in items:
        if item.get('magnitude') is not None and item['magnitude'] < settings.earthquake_min_magnitude:
            continue
        if item.get('external_id') and db.scalar(select(EmergencyEvent).where(EmergencyEvent.source=='SGC',EmergencyEvent.external_id==item['external_id'])):
            continue
        row=EmergencyEvent(source='SGC',type='EARTHQUAKE',severity='UNKNOWN',certainty='OBSERVED',urgency='EXPECTED',
                           latitude=item['latitude'],longitude=item['longitude'],radius_km=settings.earthquake_max_distance_km,
                           magnitude=item.get('magnitude'),depth_km=item.get('depth_km'),external_id=item.get('external_id'),
                           raw_payload=json.dumps(item.get('raw',{}),default=str))
        db.add(row); db.flush(); trigger_checkins(db,row); created.append(row.id)
    audit(db,user.id,'SGC_SYNC','source',None,metadata={"created":len(created),"fetched":len(items)}); db.commit()
    return {"fetched":len(items),"created":len(created),"event_ids":created}

@router.post('/safety/respond')
def safety_respond(payload: SafetyResponseIn, user: User=Depends(current_user), db:Session=Depends(get_db)):
    row=SafetyStatus(user_id=user.id,event_id=payload.event_id,welfare_check_id=payload.welfare_check_id,status=payload.status,message=payload.message)
    db.add(row); db.flush()
    contacts=db.scalars(select(TrustedContact).where(TrustedContact.owner_user_id==user.id,TrustedContact.status=='ACCEPTED',TrustedContact.can_receive_sos==True,TrustedContact.contact_user_id.is_not(None))).all()
    title={'SAFE':'Confirmación de bienestar','HELP_REQUIRED':'Necesita ayuda','UNABLE_TO_EXIT':'No puede salir'}[payload.status]
    for c in contacts:
        notify(db,c.contact_user_id,'STATUS_UPDATE',title,f'{user.full_name}: {payload.status}',{"subject_user_id":user.id,"status":payload.status})
    if payload.welfare_check_id:
        check=db.get(WelfareCheck,payload.welfare_check_id)
        if check:
            check.status='LOCATED_SAFE' if payload.status=='SAFE' else 'LOCATED_HELP_REQUIRED'
    audit(db,user.id,'SAFETY_RESPONSE','safety_status',row.id,metadata={"status":payload.status}); db.commit()
    return {"id":row.id,"status":row.status}

@router.post('/welfare-checks')
def welfare_request(payload: WelfareRequestIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try: row=request_welfare(db,user.id,payload.subject_user_id,payload.reason)
    except PermissionError as e: raise HTTPException(403,str(e))
    db.commit(); return {"id":row.id,"status":row.status,"quorum_required":row.quorum_required,"quorum_count":row.quorum_count}

@router.get('/welfare-checks')
def welfare_list(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(WelfareCheck).where((WelfareCheck.subject_user_id==user.id)|(WelfareCheck.requester_user_id==user.id)).order_by(WelfareCheck.requested_at.desc())).all()
    return [{"id":r.id,"subject_user_id":r.subject_user_id,"requester_user_id":r.requester_user_id,"status":r.status,"reason":r.reason,"quorum_required":r.quorum_required,"quorum_count":r.quorum_count,"requested_at":r.requested_at} for r in rows]

@router.post('/welfare-checks/{check_id}/quorum')
def welfare_quorum(check_id:str,payload:WelfareConfirmIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    check=db.get(WelfareCheck,check_id)
    if not check: raise HTTPException(404,'Solicitud no encontrada')
    try: row=confirm_quorum(db,check,user.id,payload.response)
    except PermissionError as e: raise HTTPException(403,str(e))
    db.commit(); return {"id":row.id,"status":row.status,"quorum_required":row.quorum_required,"quorum_count":row.quorum_count}

@router.post('/welfare-checks/{check_id}/community-verification')
def community_verify(check_id:str,payload:CommunityVerificationIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    check=db.get(WelfareCheck,check_id)
    if not check: raise HTTPException(404,'Solicitud no encontrada')
    row=CommunityVerification(welfare_check_id=check_id,verifier_user_id=user.id,**payload.model_dump())
    db.add(row); db.flush();
    if payload.result=='LOCATED_SAFE': check.status='LOCATED_SAFE'
    elif payload.result=='LOCATED_HELP_REQUIRED': check.status='LOCATED_HELP_REQUIRED'
    audit(db,user.id,'COMMUNITY_VERIFICATION','welfare_check',check_id,metadata=payload.model_dump()); db.commit()
    return {"verification_id":row.id,"case_status":check.status}

@router.post('/cases')
def create_case(payload:CaseCreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rel=contact_relation(db,payload.subject_user_id,user.id)
    if not rel: raise HTTPException(403,'Solo un contacto autorizado puede abrir una solicitud de verificación de paradero')
    row=DisappearanceCase(subject_user_id=payload.subject_user_id,opened_by_user_id=user.id,status='OPEN',notes=payload.notes)
    db.add(row); db.flush(); audit(db,user.id,'CASE_CREATE','case',row.id,metadata={"subject":payload.subject_user_id}); db.commit()
    return {"id":row.id,"status":row.status,"note":"Caso de la plataforma; no equivale a denuncia, MBU ni registro SIRDEC."}

@router.get('/cases')
def list_cases(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(DisappearanceCase).where((DisappearanceCase.subject_user_id==user.id)|(DisappearanceCase.opened_by_user_id==user.id)).order_by(DisappearanceCase.created_at.desc())).all()
    return [{"id":r.id,"subject_user_id":r.subject_user_id,"opened_by_user_id":r.opened_by_user_id,"status":r.status,"notes":r.notes,"created_at":r.created_at} for r in rows]

@router.post('/cases/{case_id}/institutional-reference')
def add_reference(case_id:str,payload:InstitutionalReferenceIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    case=db.get(DisappearanceCase,case_id)
    if not case or (case.opened_by_user_id!=user.id and case.subject_user_id!=user.id): raise HTTPException(404,'Caso no encontrado')
    row=InstitutionalReference(case_id=case_id,**payload.model_dump())
    db.add(row); case.status='INSTITUTIONAL_REFERENCE_ADDED'; db.flush(); audit(db,user.id,'INSTITUTIONAL_REFERENCE_ADD','case',case_id,metadata={"source":payload.source}); db.commit()
    return {"id":row.id,"case_status":case.status}

@router.post('/personal-safety/start')
def safety_start(payload:SafetyModeIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    until=utcnow()+timedelta(minutes=payload.boost_minutes)
    row=PersonalSafetySession(user_id=user.id,status='ACTIVE',sampling_boost_until=until,notify_contacts_json=json.dumps(payload.notify_contact_ids))
    db.add(row); db.flush()
    for cid in payload.notify_contact_ids:
        c=db.get(TrustedContact,cid)
        if c and c.owner_user_id==user.id and c.status=='ACCEPTED' and c.contact_user_id:
            notify(db,c.contact_user_id,'PERSONAL_SAFETY',f'{user.full_name} activó modo de seguridad','La persona percibe una situación de vulnerabilidad inmediata. No implica agresión confirmada.',{"session_id":row.id})
    audit(db,user.id,'PERSONAL_SAFETY_START','safety_session',row.id); db.commit()
    return {"id":row.id,"status":row.status,"sampling_boost_until":row.sampling_boost_until}

@router.post('/personal-safety/{session_id}/stop')
def safety_stop(session_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(PersonalSafetySession,session_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Sesión no encontrada')
    row.status='CLOSED'; row.ended_at=utcnow(); audit(db,user.id,'PERSONAL_SAFETY_STOP','safety_session',row.id); db.commit()
    return {"id":row.id,"status":row.status}

@router.get('/notifications')
def notifications(user:User=Depends(current_user),db:Session=Depends(get_db),pending_only:bool=False):
    q=select(Notification).where(Notification.user_id==user.id)
    if pending_only: q=q.where(Notification.status=='PENDING')
    rows=db.scalars(q.order_by(Notification.created_at.desc()).limit(100)).all()
    return [{"id":r.id,"type":r.type,"title":r.title,"body":r.body,"channel":r.channel,"status":r.status,"metadata":json.loads(r.metadata_json) if r.metadata_json else {},"created_at":r.created_at} for r in rows]

@router.post('/notifications/{notification_id}/read')
def mark_read(notification_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(Notification,notification_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Notificación no encontrada')
    row.status='READ'; db.commit(); return {"id":row.id,"status":row.status}

@router.get('/official/sirdec/preview')
async def sirdec_preview(limit:int=Query(20,ge=1,le=200),offset:int=Query(0,ge=0),user:User=Depends(current_user)):
    try: return await SirdecOpenDataAdapter().preview(limit,offset)
    except Exception as e: raise HTTPException(502,f'No fue posible consultar Datos Abiertos/SIRDEC: {e}')

@router.get('/official/sirdec/public-portal')
def sirdec_portal(user:User=Depends(current_user)):
    return SirdecOpenDataAdapter().public_portal()

@router.get('/official/ideam/status')
async def ideam_status(user:User=Depends(current_user)):
    try: return await IdeamAdapter().fetch()
    except Exception as e: raise HTTPException(502,f'No fue posible consultar IDEAM configurado: {e}')
