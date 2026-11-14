import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,LocationAccessGrant,AuditLog,Checkpoint
from app.services.timeutils import utcnow, as_utc
from app.services.common import audit

router=APIRouter(tags=['privacy'])

@router.get('/privacy/location-grants')
def grants(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(LocationAccessGrant).where(LocationAccessGrant.subject_user_id==user.id).order_by(LocationAccessGrant.created_at.desc()).limit(100)).all()
    return [{"id":r.id,"grantee_user_id":r.grantee_user_id,"level":r.level,"reason":r.reason,"source_type":r.source_type,"source_id":r.source_id,"expires_at":r.expires_at,"revoked_at":r.revoked_at,"active":r.revoked_at is None and as_utc(r.expires_at)>utcnow()} for r in rows]

@router.delete('/privacy/location-grants/{grant_id}')
def revoke_grant(grant_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(LocationAccessGrant,grant_id)
    if not row or row.subject_user_id!=user.id:raise HTTPException(404,'Autorización no encontrada')
    row.revoked_at=utcnow();audit(db,user.id,'LOCATION_GRANT_REVOKE','location_access_grant',row.id);db.commit();return {"id":row.id,"revoked":True}

@router.get('/privacy/access-history')
def access_history(user:User=Depends(current_user),db:Session=Depends(get_db)):
    # Muestra accesos que el titular puede auditar sin exponer coordenadas en el log.
    rows=db.scalars(select(AuditLog).where(
        AuditLog.action.in_(['CHECKPOINT_READ','WELFARE_LOCATION_READ','LOCATION_GRANT_CREATE','LOCATION_GRANT_REVOKE'])
    ).order_by(AuditLog.created_at.desc()).limit(200)).all()
    result=[]
    for r in rows:
        metadata={}
        if r.metadata_json:
            try: metadata=json.loads(r.metadata_json)
            except (TypeError,ValueError,json.JSONDecodeError): metadata={}
        subject=metadata.get('subject_user_id') or metadata.get('subject')
        if r.actor_user_id==user.id or subject==user.id:
            result.append({"id":r.id,"actor_user_id":r.actor_user_id,"action":r.action,"resource_type":r.resource_type,"resource_id":r.resource_id,"result":r.result,"reason":r.reason,"created_at":r.created_at})
    return result

@router.get('/checkpoints/me/holds')
def holds(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(Checkpoint).where(Checkpoint.user_id==user.id,Checkpoint.incident_hold==True).order_by(Checkpoint.created_at.desc())).all()  # noqa:E712
    return [{"id":r.id,"created_at":r.created_at,"hold_reason":r.hold_reason,"hold_expires_at":r.hold_expires_at} for r in rows]
