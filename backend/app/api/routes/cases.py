from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,DisappearanceCase,InstitutionalReference,WelfareCheck
from app.schemas.api import CaseCreateIn,CaseUpdateIn,InstitutionalReferenceIn
from app.services.policy import contact_relation
from app.services.common import audit
from app.services.timeutils import utcnow
from app.services.state_machine import can_transition_case

router=APIRouter(tags=['cases'])

def out(r:DisappearanceCase)->dict:
    return {"id":r.id,"subject_user_id":r.subject_user_id,"opened_by_user_id":r.opened_by_user_id,"welfare_check_id":r.welfare_check_id,"status":r.status,"notes":r.notes,"created_at":r.created_at,"updated_at":r.updated_at,"closed_at":r.closed_at,
            "disclaimer":"Caso ciudadano de la plataforma; no equivale a denuncia, MBU, Alerta Rosa ni registro SIRDEC."}

@router.post('/cases',status_code=201)
def create_case(payload:CaseCreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rel=contact_relation(db,payload.subject_user_id,user.id)
    if not rel or not rel.can_request_welfare:raise HTTPException(403,'Solo un contacto autorizado puede crear un caso ciudadano')
    welfare_id=payload.welfare_check_id
    check=None
    if welfare_id:
        check=db.get(WelfareCheck,welfare_id)
    else:
        check=db.scalar(select(WelfareCheck).where(
            WelfareCheck.subject_user_id==payload.subject_user_id,
            WelfareCheck.requester_user_id==user.id
        ).order_by(WelfareCheck.requested_at.desc()).limit(1))
        welfare_id=check.id if check else None
    if not check or check.subject_user_id!=payload.subject_user_id:
        raise HTTPException(409,'Debe existir una solicitud de verificación previa antes de escalar a caso ciudadano')
    if check.status not in {'TRUSTED_QUORUM_MET','COMMUNITY_CHECK_ACTIVE','COMMUNITY_HELP_REPORTED','COMMUNITY_SAFE_CONFIRMED','NO_RESPONSE','LOCATED_HELP_REQUIRED'}:
        raise HTTPException(409,'El flujo de verificación aún no justifica escalar el caso')
    row=DisappearanceCase(subject_user_id=payload.subject_user_id,opened_by_user_id=user.id,welfare_check_id=welfare_id,status='OPEN',notes=payload.notes)
    db.add(row);db.flush();audit(db,user.id,'CASE_CREATE','case',row.id,metadata={"subject":payload.subject_user_id});db.commit();return out(row)

@router.get('/cases')
def list_cases(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(DisappearanceCase).where((DisappearanceCase.subject_user_id==user.id)|(DisappearanceCase.opened_by_user_id==user.id)).order_by(DisappearanceCase.created_at.desc())).all();return [out(r) for r in rows]

@router.get('/cases/{case_id}')
def get_case(case_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(DisappearanceCase,case_id)
    if not r or user.id not in {r.subject_user_id,r.opened_by_user_id}:raise HTTPException(404,'Caso no encontrado')
    refs=db.scalars(select(InstitutionalReference).where(InstitutionalReference.case_id==r.id)).all()
    result=out(r);result['institutional_references']=[{"id":x.id,"source":x.source,"reference_number":x.reference_number,"status":x.status,"external_url":x.external_url,"reported_at":x.reported_at} for x in refs];return result

@router.patch('/cases/{case_id}')
def update_case(case_id:str,payload:CaseUpdateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(DisappearanceCase,case_id)
    if not r or user.id not in {r.subject_user_id,r.opened_by_user_id}:raise HTTPException(404,'Caso no encontrado')
    if not can_transition_case(r.status,payload.status):raise HTTPException(409,f'Transición no permitida: {r.status} → {payload.status}')
    r.status=payload.status
    if payload.notes is not None:r.notes=payload.notes
    if payload.status in {'LOCATED_SAFE','LOCATED_HELP_REQUIRED','CLOSED'}:r.closed_at=utcnow()
    audit(db,user.id,'CASE_UPDATE','case',r.id,metadata={"status":payload.status});db.commit();return out(r)

@router.post('/cases/{case_id}/institutional-reference',status_code=201)
def add_reference(case_id:str,payload:InstitutionalReferenceIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(DisappearanceCase,case_id)
    if not r or user.id not in {r.subject_user_id,r.opened_by_user_id}:raise HTTPException(404,'Caso no encontrado')
    ref=InstitutionalReference(case_id=case_id,**payload.model_dump());db.add(ref);r.status='INSTITUTIONAL_REFERENCE_ADDED';db.flush();audit(db,user.id,'INSTITUTIONAL_REFERENCE_ADD','case',r.id,metadata={"source":payload.source});db.commit();return {"id":ref.id,"case_status":r.status}
