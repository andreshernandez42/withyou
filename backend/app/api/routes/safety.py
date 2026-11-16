from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,SafetyStatus,WelfareCheck,TrustedContact,SOSSession,PersonalSafetySession,EmergencyEvent
from app.schemas.api import SafetyResponseIn,SOSIn
from app.services.common import audit,notify
from app.services.policy import grant_for_emergency_contacts
from app.services.vault import latest_checkpoint,set_incident_hold
from app.services.timeutils import utcnow

router=APIRouter(tags=['safety'])

@router.get('/safety/pending')
def pending(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(SafetyStatus).where(SafetyStatus.user_id==user.id,SafetyStatus.status=='CHECK_REQUESTED').order_by(SafetyStatus.created_at.desc())).all()
    return [{"id":r.id,"event_id":r.event_id,"welfare_check_id":r.welfare_check_id,"status":r.status,"expires_at":r.expires_at,"created_at":r.created_at,
             "is_test":bool(db.get(EmergencyEvent,r.event_id).is_test) if r.event_id and db.get(EmergencyEvent,r.event_id) else False} for r in rows]

@router.post('/safety/respond')
def respond(payload:SafetyResponseIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    target=None
    if payload.event_id:
        target=db.scalar(select(SafetyStatus).where(SafetyStatus.user_id==user.id,SafetyStatus.event_id==payload.event_id,SafetyStatus.status=='CHECK_REQUESTED').order_by(SafetyStatus.created_at.desc()).limit(1))
    elif payload.welfare_check_id:
        target=db.scalar(select(SafetyStatus).where(SafetyStatus.user_id==user.id,SafetyStatus.welfare_check_id==payload.welfare_check_id,SafetyStatus.status=='CHECK_REQUESTED').order_by(SafetyStatus.created_at.desc()).limit(1))
    if not target and (payload.event_id or payload.welfare_check_id):
        raise HTTPException(404, 'No existe una verificación pendiente para responder')
    if target:
        target.status=payload.status;target.message=payload.message;target.responded_at=utcnow()
        row=target
    else:
        row=SafetyStatus(user_id=user.id,event_id=payload.event_id,welfare_check_id=payload.welfare_check_id,status=payload.status,message=payload.message,responded_at=utcnow())
        db.add(row);db.flush()
    event=db.get(EmergencyEvent,payload.event_id) if payload.event_id else None
    is_test=bool(event and event.is_test)
    contacts=db.scalars(select(TrustedContact).where(TrustedContact.owner_user_id==user.id,TrustedContact.status=='ACCEPTED',TrustedContact.revoked_at.is_(None),TrustedContact.can_receive_sos==True,TrustedContact.contact_user_id.is_not(None))).all()  # noqa:E712
    title={'SAFE':'Confirmación de bienestar','HELP_REQUIRED':'Necesita ayuda','UNABLE_TO_EXIT':'No puede salir'}[payload.status]
    for c in contacts:
        if is_test:continue
        notify(db,c.contact_user_id,'STATUS_UPDATE',title,f'{user.full_name}: {payload.status}',{"subject_user_id":user.id,"status":payload.status,"event_id":payload.event_id})
    if payload.status in {'HELP_REQUIRED','UNABLE_TO_EXIT'} and not is_test:
        grant_for_emergency_contacts(db,user.id,'SAFETY_RESPONSE',row.id,f'Respuesta explícita {payload.status}')
        cp=latest_checkpoint(db,user.id)
        if cp:set_incident_hold(db,cp,user.id,f'Respuesta de emergencia {payload.status}')
    if payload.welfare_check_id:
        check=db.get(WelfareCheck,payload.welfare_check_id)
        if check and check.subject_user_id==user.id:
            check.status='LOCATED_SAFE' if payload.status=='SAFE' else 'LOCATED_HELP_REQUIRED';check.closed_at=utcnow()
    audit(db,user.id,'SAFETY_RESPONSE','safety_status',row.id,metadata={"status":payload.status});db.commit()
    return {"id":row.id,"status":row.status}

@router.post('/sos',status_code=201)
def start_sos(payload:SOSIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    cp=latest_checkpoint(db,user.id)
    row=SOSSession(user_id=user.id,personal_safety_session_id=payload.personal_safety_session_id,message=payload.message,checkpoint_id=cp.id if cp else None)
    db.add(row);db.flush()
    if cp:set_incident_hold(db,cp,user.id,f'SOS {row.id}')
    granted=grant_for_emergency_contacts(db,user.id,'SOS',row.id,'SOS explícito del usuario')
    contacts=db.scalars(select(TrustedContact).where(TrustedContact.owner_user_id==user.id,TrustedContact.status=='ACCEPTED',TrustedContact.revoked_at.is_(None),TrustedContact.can_receive_sos==True,TrustedContact.contact_user_id.is_not(None))).all()  # noqa:E712
    for c in contacts:
        notify(db,c.contact_user_id,'SOS','SOS activado',f'{user.full_name} activó un SOS.',{"sos_id":row.id,"subject_user_id":user.id,"location_granted":c.contact_user_id in granted})
    audit(db,user.id,'SOS_START','sos',row.id,metadata={"granted":granted});db.commit();return {"id":row.id,"status":row.status,"location_grants":len(granted)}

@router.post('/sos/{sos_id}/resolve')
def resolve_sos(sos_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(SOSSession,sos_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,'SOS no encontrado')
    row.status='RESOLVED';row.resolved_at=utcnow();audit(db,user.id,'SOS_RESOLVE','sos',row.id);db.commit();return {"id":row.id,"status":row.status}
