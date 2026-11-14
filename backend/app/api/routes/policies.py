from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,ConsentPolicy
from app.schemas.api import PolicyIn
from app.services.common import audit

router=APIRouter(tags=["policies"])

def out(r:ConsentPolicy)->dict:
    return {"id":r.id,"name":r.name,"event_type":r.event_type,"requires_official_event":r.requires_official_event,
            "quorum_required":r.quorum_required,"allow_coarse_location":r.allow_coarse_location,
            "allow_exact_location":r.allow_exact_location,"allow_recent_route":r.allow_recent_route,
            "allow_community_check":r.allow_community_check,
            "release_on_official_event_no_response":r.release_on_official_event_no_response,
            "release_after_quorum":r.release_after_quorum,"access_ttl_minutes":r.access_ttl_minutes,"active":r.active}

@router.get('/policies')
def list_policies(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return [out(r) for r in db.scalars(select(ConsentPolicy).where(ConsentPolicy.user_id==user.id).order_by(ConsentPolicy.created_at.desc())).all()]

@router.post('/policies',status_code=201)
def create(payload:PolicyIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=ConsentPolicy(user_id=user.id,**payload.model_dump())
    db.add(row);db.flush();audit(db,user.id,'POLICY_CREATE','policy',row.id);db.commit();return out(row)

@router.put('/policies/{policy_id}')
def replace(policy_id:str,payload:PolicyIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(ConsentPolicy,policy_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Política no encontrada')
    for k,v in payload.model_dump().items(): setattr(row,k,v)
    audit(db,user.id,'POLICY_UPDATE','policy',row.id);db.commit();return out(row)

@router.delete('/policies/{policy_id}')
def disable(policy_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(ConsentPolicy,policy_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Política no encontrada')
    row.active=False;audit(db,user.id,'POLICY_DISABLE','policy',row.id);db.commit();return {"id":row.id,"active":False}
