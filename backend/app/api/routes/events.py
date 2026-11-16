from datetime import timedelta
import json
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import current_user,require_roles
from app.models import User,EmergencyEvent,OfficialSourceSync
from app.schemas.api import TestEventIn
from app.services.common import audit
from app.services.events import trigger_checkins,event_is_current
from app.services.timeutils import utcnow, as_utc
from app.services.sgc_sync import sync_sgc_events

router=APIRouter(tags=["events"])

def event_out(r:EmergencyEvent)->dict:
    return {"id":r.id,"external_id":r.external_id,"source":r.source,"type":r.type,"status":r.status,
            "severity":r.severity,"certainty":r.certainty,"urgency":r.urgency,"latitude":r.latitude,
            "longitude":r.longitude,"radius_km":r.radius_km,"magnitude":r.magnitude,"depth_km":r.depth_km,
            "is_test":r.is_test,"starts_at":r.starts_at,"ends_at":r.ends_at,"received_at":r.received_at}

@router.post('/test/emergency-events',status_code=201)
def create_test_event(payload:TestEventIn,user:User=Depends(require_roles('TESTER','ADMIN')),db:Session=Depends(get_db)):
    if not settings.allow_test_endpoints: raise HTTPException(404,'Endpoints de prueba deshabilitados')
    source=payload.source if payload.source.upper().startswith('TEST') else f'TEST-{payload.source}'
    row=EmergencyEvent(**payload.model_dump(exclude={'source','starts_at','external_id'}),source=source,is_test=True,
                       starts_at=payload.starts_at or utcnow(),external_id=payload.external_id or f'test-{utcnow().timestamp()}',
                       raw_payload=json.dumps(payload.model_dump(),default=str,ensure_ascii=False))
    db.add(row);db.flush();affected=trigger_checkins(db,row);audit(db,user.id,'TEST_EVENT_CREATE','event',row.id,metadata={"affected":affected});db.commit()
    return {"event_id":row.id,"is_test":True,"event":event_out(row),"affected_users":affected,"note":"Evento de prueba; nunca equivale a evento oficial."}

@router.get('/events')
def list_events(limit:int=Query(20,ge=1,le=100),include_test:bool=False,user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=select(EmergencyEvent)
    # Los eventos sintéticos son visibles solo a roles de laboratorio/administración.
    if user.role not in {'TESTER','ADMIN'}:
        include_test=False
    if not include_test:q=q.where(EmergencyEvent.is_test==False)  # noqa:E712
    rows=db.scalars(q.order_by(EmergencyEvent.created_at.desc()).limit(limit)).all();return [event_out(r) for r in rows]

@router.get('/events/{event_id}')
def get_event(event_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(EmergencyEvent,event_id)
    if not row or (row.is_test and user.role not in {'TESTER','ADMIN'}):
        raise HTTPException(404,'Evento no encontrado')
    return event_out(row)

@router.post('/events/{event_id}/reprocess')
def reprocess(event_id:str,user:User=Depends(require_roles('TESTER','ADMIN')),db:Session=Depends(get_db)):
    row=db.get(EmergencyEvent,event_id)
    if not row: raise HTTPException(404,'Evento no encontrado')
    affected=trigger_checkins(db,row);audit(db,user.id,'EVENT_REPROCESS','event',row.id,metadata={"affected":affected});db.commit();return {"event_id":row.id,"affected_users":affected}

@router.post('/events/sync/sgc')
async def sync_sgc(user:User=Depends(require_roles('TESTER','ADMIN')),db:Session=Depends(get_db)):
    try:
        return await sync_sgc_events(db, user.id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, 'No fue posible consultar la fuente del SGC. Revise los registros del backend.') from exc


@router.get('/official/sgc/status')
def sgc_status(user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Estado de la integración, no una garantía de alerta temprana."""
    sync=db.scalar(select(OfficialSourceSync).where(OfficialSourceSync.source=='SGC')
                   .order_by(OfficialSourceSync.last_success_at.desc()).limit(1))
    latest=db.scalar(select(EmergencyEvent).where(EmergencyEvent.source=='SGC',EmergencyEvent.is_test==False)
                     .order_by(EmergencyEvent.starts_at.desc()).limit(1))
    return {
        'source':'SGC', 'poll_enabled':settings.sgc_poll_enabled,
        'last_sync_at':sync.last_success_at if sync else None,
        'last_sync_status':sync.status if sync else 'NOT_RUN',
        'last_fetched':sync.records_count if sync else None,
        'latest_event_at':latest.starts_at if latest else None,
        'recent_feed_verified':bool(latest and event_is_current(latest)),
        'note':'Sismos publicados por el SGC; no es una alerta temprana previa al movimiento.',
    }
