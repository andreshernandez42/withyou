from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User, Device, TrustedContact
from app.schemas.api import ProfileUpdateIn, DeviceIn
from app.services.common import audit
from app.services.timeutils import utcnow

router = APIRouter(tags=["users"])


def user_out(u: User) -> dict:
    return {"id":u.id,"full_name":u.full_name,"email":u.email,"role":u.role,"is_minor":u.is_minor,
            "community_opt_in":u.community_opt_in,"locale":u.locale,"status":u.status}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.patch("/me")
def update_me(payload: ProfileUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    if user.is_minor and data.get('community_opt_in') is True:
        raise HTTPException(403, 'Los perfiles NNA del MVP no pueden participar como verificadores comunitarios')
    for k,v in data.items(): setattr(user,k,v)
    audit(db,user.id,"PROFILE_UPDATE","user",user.id,metadata=data); db.commit()
    return user_out(user)


@router.get("/users")
def users(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Compatibilidad con el frontend existente sin exponer un directorio global a usuarios normales.
    if user.role == "ADMIN":
        rows = db.scalars(select(User).where(User.id != user.id, User.status == "ACTIVE")).all()
    else:
        rels=db.scalars(select(TrustedContact).where(TrustedContact.contact_user_id==user.id,TrustedContact.status=="ACCEPTED",TrustedContact.revoked_at.is_(None))).all()
        ids=[r.owner_user_id for r in rels]
        rows=db.scalars(select(User).where(User.id.in_(ids),User.status=="ACTIVE")).all() if ids else []
    return [{"id":r.id,"full_name":r.full_name,"email":r.email,"is_minor":r.is_minor} for r in rows]

@router.get("/authorized-subjects")
def authorized_subjects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rels=db.scalars(select(TrustedContact).where(
        TrustedContact.contact_user_id==user.id, TrustedContact.status=="ACCEPTED", TrustedContact.revoked_at.is_(None)
    )).all()
    result=[]
    for rel in rels:
        owner=db.get(User,rel.owner_user_id)
        if owner and owner.status=="ACTIVE":
            result.append({"user_id":owner.id,"full_name":owner.full_name,"can_request_welfare":rel.can_request_welfare,"can_view_checkpoint":rel.can_view_checkpoint,"can_receive_sos":rel.can_receive_sos})
    return result


@router.post("/devices")
def upsert_device(payload: DeviceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Device).where(Device.user_id==user.id,Device.device_uid==payload.device_uid).limit(1))
    if not row:
        row=Device(user_id=user.id,device_uid=payload.device_uid,platform=payload.platform,device_name=payload.device_name,push_token=payload.push_token)
        db.add(row); db.flush()
    else:
        row.platform=payload.platform; row.device_name=payload.device_name; row.push_token=payload.push_token; row.active=True; row.last_seen_at=utcnow()
    audit(db,user.id,"DEVICE_UPSERT","device",row.id,metadata={"platform":row.platform}); db.commit()
    return {"id":row.id,"device_uid":row.device_uid,"platform":row.platform,"device_name":row.device_name,"active":row.active}


@router.get("/devices")
def devices(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(Device).where(Device.user_id==user.id,Device.active==True)).all()  # noqa:E712
    return [{"id":r.id,"device_uid":r.device_uid,"platform":r.platform,"device_name":r.device_name,"last_seen_at":r.last_seen_at} for r in rows]


@router.delete("/devices/{device_id}")
def delete_device(device_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(Device,device_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,"Dispositivo no encontrado")
    row.active=False; row.push_token=None; audit(db,user.id,"DEVICE_REVOKE","device",row.id); db.commit()
    return {"id":row.id,"active":False}
