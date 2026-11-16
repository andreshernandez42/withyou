from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,Checkpoint
from app.schemas.api import CheckpointIn
from app.services.common import audit
from app.services.vault import create_checkpoint,latest_checkpoint,checkpoint_public,valid_checkpoint_filter
from app.services.policy import active_location_grant

router=APIRouter(tags=["vault"])

@router.post('/checkpoints',status_code=201)
def post_checkpoint(payload:CheckpointIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try: row=create_checkpoint(db,user.id,payload)
    except PermissionError as e: raise HTTPException(403,str(e))
    except ValueError as e: raise HTTPException(400,str(e))
    db.commit();db.refresh(row);return checkpoint_public(row,'EXACT')

@router.get('/checkpoints/me/latest')
def my_latest(user:User=Depends(current_user),db:Session=Depends(get_db)):
    cp=latest_checkpoint(db,user.id)
    if not cp: raise HTTPException(404,'Sin checkpoints vigentes')
    return checkpoint_public(cp,'EXACT')

@router.get('/checkpoints/me/history')
def my_history(limit:int=20,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(Checkpoint).where(
        Checkpoint.user_id==user.id,
        valid_checkpoint_filter()
    ).order_by(Checkpoint.created_at.desc()).limit(max(1,min(limit,100)))).all()
    return [checkpoint_public(r,'EXACT') for r in rows]

@router.get('/checkpoints/{subject_user_id}/latest')
def contact_latest(subject_user_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if subject_user_id==user.id:
        cp=latest_checkpoint(db,user.id)
        if not cp: raise HTTPException(404,'Sin checkpoints vigentes')
        return checkpoint_public(cp,'EXACT')
    grant=active_location_grant(db,subject_user_id,user.id)
    if not grant:
        audit(db,user.id,'CHECKPOINT_READ','checkpoint',None,result='DENIED',reason='active_grant_required',metadata={"subject":subject_user_id});db.commit()
        raise HTTPException(403,'No existe autorización contextual vigente para consultar la ubicación')
    cp=latest_checkpoint(db,subject_user_id)
    if not cp: raise HTTPException(404,'Sin checkpoints vigentes')
    audit(db,user.id,'CHECKPOINT_READ','checkpoint',cp.id,metadata={"subject":subject_user_id,"grant_id":grant.id,"level":grant.level});db.commit()
    return checkpoint_public(cp,grant.level)
