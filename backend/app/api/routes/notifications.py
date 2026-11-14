import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User,Notification
from app.services.timeutils import utcnow

router=APIRouter(tags=['notifications'])

@router.get('/notifications')
def notifications(user:User=Depends(current_user),db:Session=Depends(get_db),pending_only:bool=False):
    q=select(Notification).where(Notification.user_id==user.id)
    if pending_only:q=q.where(Notification.status.in_(['PENDING','SENT']))
    rows=db.scalars(q.order_by(Notification.created_at.desc()).limit(100)).all()
    return [{"id":r.id,"type":r.type,"title":r.title,"body":r.body,"channel":r.channel,"status":r.status,"metadata":json.loads(r.metadata_json) if r.metadata_json else {},"created_at":r.created_at,"sent_at":r.sent_at,"read_at":r.read_at} for r in rows]

@router.post('/notifications/{notification_id}/read')
def mark_read(notification_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(Notification,notification_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,'Notificación no encontrada')
    row.status='READ';row.read_at=utcnow();db.commit();return {"id":row.id,"status":row.status}
