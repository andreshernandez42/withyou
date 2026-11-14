from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,WelfareCheck,CommunityVerification
from app.schemas.api import WelfareRequestIn,WelfareConfirmIn,WelfareCloseIn,CommunityVerificationIn
from app.services.welfare import request_welfare,confirm_quorum,activate_community_check,register_community_verification
from app.services.policy import active_location_grant,contact_relation
from app.services.vault import latest_checkpoint,checkpoint_public
from app.services.common import audit,haversine_km
from app.services.timeutils import utcnow

router=APIRouter(tags=['welfare'])

def out(r:WelfareCheck)->dict:
    return {"id":r.id,"subject_user_id":r.subject_user_id,"requester_user_id":r.requester_user_id,"event_id":r.event_id,"status":r.status,"reason":r.reason,
            "quorum_required":r.quorum_required,"quorum_count":r.quorum_count,"community_active":r.community_active,"requested_at":r.requested_at,"expires_at":r.expires_at}

@router.post('/welfare-checks',status_code=201)
def request(payload:WelfareRequestIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try:r=request_welfare(db,user.id,payload.subject_user_id,payload.reason)
    except PermissionError as e:raise HTTPException(403,str(e))
    db.commit();return out(r)

@router.get('/welfare-checks')
def list_checks(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(WelfareCheck).where((WelfareCheck.subject_user_id==user.id)|(WelfareCheck.requester_user_id==user.id)).order_by(WelfareCheck.requested_at.desc())).all();return [out(r) for r in rows]

@router.get('/welfare-checks/{check_id}')
def get_check(check_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(WelfareCheck,check_id)
    if not r:raise HTTPException(404,'Solicitud no encontrada')
    if user.id not in {r.subject_user_id,r.requester_user_id} and not contact_relation(db,r.subject_user_id,user.id):raise HTTPException(403,'No autorizado')
    return out(r)

@router.post('/welfare-checks/{check_id}/quorum')
def quorum(check_id:str,payload:WelfareConfirmIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(WelfareCheck,check_id)
    if not r:raise HTTPException(404,'Solicitud no encontrada')
    try:r=confirm_quorum(db,r,user.id,payload.response)
    except PermissionError as e:raise HTTPException(403,str(e))
    except ValueError as e:raise HTTPException(409,str(e))
    db.commit();return out(r)

@router.get('/welfare-checks/{check_id}/location')
def check_location(check_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(WelfareCheck,check_id)
    if not r:raise HTTPException(404,'Solicitud no encontrada')
    if r.subject_user_id==user.id:
        grant_level='EXACT'
    else:
        grant=active_location_grant(db,r.subject_user_id,user.id)
        if not grant:raise HTTPException(403,'La política aún no autoriza ubicación')
        grant_level=grant.level
    cp=latest_checkpoint(db,r.subject_user_id)
    if not cp:raise HTTPException(404,'Sin checkpoints vigentes')
    audit(db,user.id,'WELFARE_LOCATION_READ','welfare_check',r.id,metadata={"level":grant_level,"subject_user_id":r.subject_user_id});db.commit();return checkpoint_public(cp,grant_level)

@router.post('/welfare-checks/{check_id}/community/activate')
def community_activate(check_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(WelfareCheck,check_id)
    if not r:raise HTTPException(404,'Solicitud no encontrada')
    try:r=activate_community_check(db,r,user.id)
    except PermissionError as e:raise HTTPException(403,str(e))
    except ValueError as e:raise HTTPException(409,str(e))
    db.commit();return out(r)

@router.get('/community/welfare-checks/nearby')
def nearby(latitude:float=Query(...,ge=-90,le=90),longitude:float=Query(...,ge=-180,le=180),radius_km:float=Query(5,gt=0,le=50),user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.is_minor or not user.community_opt_in:raise HTTPException(403,'Debe ser adulto y activar participación comunitaria')
    rows=db.scalars(select(WelfareCheck).where(WelfareCheck.community_active==True,WelfareCheck.closed_at.is_(None))).all()  # noqa:E712
    result=[]
    for r in rows:
        if user.id in {r.subject_user_id,r.requester_user_id}:continue
        cp=latest_checkpoint(db,r.subject_user_id)
        if not cp:continue
        dist=haversine_km(latitude,longitude,cp.coarse_lat,cp.coarse_lon)
        if dist<=radius_km:
            result.append({"welfare_check_id":r.id,"approximate_distance_m":int(dist*1000),"zone":{"lat":round(cp.coarse_lat,2),"lon":round(cp.coarse_lon,2)},"status":r.status})
    return result

@router.post('/welfare-checks/{check_id}/community-verification',status_code=201)
def community_verify(check_id:str,payload:CommunityVerificationIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.is_minor or not user.community_opt_in:raise HTTPException(403,'Participación comunitaria no habilitada')
    r=db.get(WelfareCheck,check_id)
    if not r:raise HTTPException(404,'Solicitud no encontrada')
    try:vr=register_community_verification(db,r,user.id,payload.result,payload.approximate_distance_m)
    except PermissionError as e:raise HTTPException(403,str(e))
    except ValueError as e:raise HTTPException(409,str(e))
    db.commit();return {"verification_id":vr.id,"check_status":r.status}

@router.post('/welfare-checks/{check_id}/close')
def close_check(check_id:str,payload:WelfareCloseIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(WelfareCheck,check_id)
    if not r:raise HTTPException(404,'Solicitud no encontrada')
    # El cierre es una decisión del sujeto o del solicitante original; un tercero del círculo no puede cerrar por sí solo.
    if user.id not in {r.subject_user_id,r.requester_user_id}:raise HTTPException(403,'Solo el sujeto o el solicitante original puede cerrar esta verificación')
    r.status=payload.outcome;r.closed_at=utcnow();r.community_active=False;audit(db,user.id,'WELFARE_CLOSE','welfare_check',r.id,metadata={"outcome":payload.outcome});db.commit();return out(r)
