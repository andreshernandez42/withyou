import json
from fastapi import APIRouter,Depends,Query
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User,AuditLog,EmergencyEvent,WelfareCheck,Notification,ExperimentRun,Checkpoint
from app.schemas.api import ExperimentRunIn
from app.services.maintenance import maintenance_tick
from app.services.common import audit

router=APIRouter(tags=['admin-experiments'])

@router.get('/audit-logs')
def audit_logs(limit:int=Query(100,ge=1,le=500),user:User=Depends(require_roles('ADMIN')),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [{"id":r.id,"actor_user_id":r.actor_user_id,"action":r.action,"resource_type":r.resource_type,"resource_id":r.resource_id,"result":r.result,"reason":r.reason,"metadata":json.loads(r.metadata_json) if r.metadata_json else {},"created_at":r.created_at} for r in rows]

@router.post('/admin/maintenance/run')
def run_maintenance(user:User=Depends(require_roles('ADMIN')),db:Session=Depends(get_db)):
    result=maintenance_tick(db);audit(db,user.id,'MAINTENANCE_RUN','system',None,metadata=result);db.commit();return result

@router.post('/experiments/runs',status_code=201)
def experiment(payload:ExperimentRunIn,user:User=Depends(require_roles('ADMIN')),db:Session=Depends(get_db)):
    row=ExperimentRun(user_id=user.id,experiment_type=payload.experiment_type,scenario=payload.scenario,parameters_json=json.dumps(payload.parameters,ensure_ascii=False),metrics_json=json.dumps(payload.metrics,ensure_ascii=False),notes=payload.notes)
    db.add(row);db.flush();audit(db,user.id,'EXPERIMENT_RUN_CREATE','experiment',row.id);db.commit();return {"id":row.id,"experiment_type":row.experiment_type,"scenario":row.scenario,"created_at":row.created_at}

@router.get('/experiments/runs')
def experiments(limit:int=Query(100,ge=1,le=500),user:User=Depends(require_roles('ADMIN')),db:Session=Depends(get_db)):
    rows=db.scalars(select(ExperimentRun).order_by(ExperimentRun.created_at.desc()).limit(limit)).all()
    return [{"id":r.id,"experiment_type":r.experiment_type,"scenario":r.scenario,"parameters":json.loads(r.parameters_json or '{}'),"metrics":json.loads(r.metrics_json or '{}'),"notes":r.notes,"created_at":r.created_at} for r in rows]

@router.get('/metrics/summary')
def metrics(user:User=Depends(require_roles('ADMIN')),db:Session=Depends(get_db)):
    return {
        "users":db.scalar(select(func.count(User.id))) or 0,
        "events":db.scalar(select(func.count(EmergencyEvent.id))) or 0,
        "active_welfare_checks":db.scalar(select(func.count(WelfareCheck.id)).where(WelfareCheck.closed_at.is_(None))) or 0,
        "checkpoints":db.scalar(select(func.count(Checkpoint.id))) or 0,
        "pending_notifications":db.scalar(select(func.count(Notification.id)).where(Notification.status=='PENDING')) or 0,
    }
