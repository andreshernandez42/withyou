import json
from datetime import timedelta
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,PersonalSafetySession,TrustedContact
from app.schemas.api import SafetyModeIn
from app.services.common import notify,audit
from app.services.timeutils import utcnow
from app.services.vault import latest_checkpoint,set_incident_hold

router=APIRouter(tags=['personal-safety'])

@router.post('/personal-safety/start',status_code=201)
def start(payload:SafetyModeIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    until=utcnow()+timedelta(minutes=payload.boost_minutes)
    row=PersonalSafetySession(user_id=user.id,status='ACTIVE',silent=payload.silent,sampling_boost_until=until,notify_contacts_json=json.dumps(payload.notify_contact_ids))
    db.add(row);db.flush()
    cp=latest_checkpoint(db,user.id)
    if cp:set_incident_hold(db,cp,user.id,f'Personal Safety {row.id}')
    for cid in payload.notify_contact_ids:
        c=db.get(TrustedContact,cid)
        if c and c.owner_user_id==user.id and c.status=='ACCEPTED' and c.revoked_at is None and c.contact_user_id:
            notify(db,c.contact_user_id,'PERSONAL_SAFETY',f'{user.full_name} activó modo de seguridad','La persona percibe una situación de vulnerabilidad inmediata. No implica agresión confirmada.',{"session_id":row.id,"silent":payload.silent})
    audit(db,user.id,'PERSONAL_SAFETY_START','safety_session',row.id,metadata={"silent":payload.silent,"boost_minutes":payload.boost_minutes});db.commit()
    return {"id":row.id,"status":row.status,"silent":row.silent,"sampling_boost_until":row.sampling_boost_until}

@router.get('/personal-safety/active')
def active(user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.scalar(select(PersonalSafetySession).where(PersonalSafetySession.user_id==user.id,PersonalSafetySession.status=='ACTIVE').order_by(PersonalSafetySession.started_at.desc()).limit(1))
    if not row:return {"active":False}
    return {"active":True,"id":row.id,"silent":row.silent,"started_at":row.started_at,"sampling_boost_until":row.sampling_boost_until}

@router.post('/personal-safety/{session_id}/stop')
def stop(session_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(PersonalSafetySession,session_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,'Sesión no encontrada')
    row.status='CLOSED';row.ended_at=utcnow();audit(db,user.id,'PERSONAL_SAFETY_STOP','safety_session',row.id);db.commit();return {"id":row.id,"status":row.status}
