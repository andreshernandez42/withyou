from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import current_user
from app.models import User, TrustedContact
from app.schemas.api import ContactCreate, ContactAccept, ContactUpdate
from app.services.common import audit, notify
from app.services.policy import revoke_location_grants
from app.services.timeutils import utcnow

router=APIRouter(tags=["trusted-circle"])


def out(r:TrustedContact)->dict:
    return {"id":r.id,"contact_user_id":r.contact_user_id,"contact_name":r.contact_name,"contact_email":r.contact_email,
            "status":r.status,"can_receive_sos":r.can_receive_sos,"can_view_checkpoint":r.can_view_checkpoint,
            "can_request_welfare":r.can_request_welfare,"quorum_weight":r.quorum_weight}


@router.post("/trusted-contacts",status_code=201)
def create_contact(payload:ContactCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    email=payload.contact_email.lower()
    if email==user.email: raise HTTPException(400,"No puede agregarse a sí mismo")
    existing=db.scalar(select(TrustedContact).where(TrustedContact.owner_user_id==user.id,TrustedContact.contact_email==email).limit(1))
    if existing and existing.status!="REVOKED": raise HTTPException(409,"El contacto ya existe")
    target=db.scalar(select(User).where(User.email==email))
    row=existing or TrustedContact(owner_user_id=user.id,contact_email=email,contact_name=payload.contact_name)
    row.contact_user_id=target.id if target else None; row.contact_name=payload.contact_name; row.status="PENDING"; row.revoked_at=None
    row.can_receive_sos=payload.can_receive_sos; row.can_view_checkpoint=payload.can_view_checkpoint
    row.can_request_welfare=payload.can_request_welfare; row.quorum_weight=payload.quorum_weight
    if not existing: db.add(row)
    db.flush()
    if target: notify(db,target.id,"CONTACT_INVITE",f"{user.full_name} te agregó a su círculo de confianza","Acepta o rechaza la invitación.",{"contact_id":row.id})
    audit(db,user.id,"TRUSTED_CONTACT_CREATE","trusted_contact",row.id); db.commit(); return out(row)


@router.get("/trusted-contacts")
def list_contacts(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(TrustedContact).where(TrustedContact.owner_user_id==user.id,TrustedContact.status!="REVOKED")).all()
    return [out(r) for r in rows]


@router.get("/trusted-contacts/invitations")
def invitations(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(TrustedContact).where(TrustedContact.contact_user_id==user.id,TrustedContact.status=="PENDING")).all()
    return [{"id":r.id,"owner_user_id":r.owner_user_id,"contact_name":r.contact_name,"contact_email":r.contact_email} for r in rows]


@router.post("/trusted-contacts/{contact_id}/accept")
def accept(contact_id:str,payload:ContactAccept,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(TrustedContact,contact_id)
    if not row or row.contact_user_id!=user.id or row.status!="PENDING": raise HTTPException(404,"Invitación no encontrada")
    row.status="ACCEPTED" if payload.accept else "REJECTED"
    audit(db,user.id,"TRUSTED_CONTACT_DECISION","trusted_contact",row.id,metadata={"accepted":payload.accept}); db.commit(); return out(row)


@router.patch("/trusted-contacts/{contact_id}")
def update(contact_id:str,payload:ContactUpdate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(TrustedContact,contact_id)
    if not row or row.owner_user_id!=user.id or row.status=="REVOKED": raise HTTPException(404,"Contacto no encontrado")
    for k,v in payload.model_dump(exclude_none=True).items(): setattr(row,k,v)
    audit(db,user.id,"TRUSTED_CONTACT_UPDATE","trusted_contact",row.id,metadata=payload.model_dump(exclude_none=True)); db.commit(); return out(row)


@router.delete("/trusted-contacts/{contact_id}")
def revoke(contact_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(TrustedContact,contact_id)
    if not row or row.owner_user_id!=user.id: raise HTTPException(404,"Contacto no encontrado")
    row.status="REVOKED"; row.revoked_at=utcnow()
    if row.contact_user_id: revoke_location_grants(db,user.id,row.contact_user_id)
    audit(db,user.id,"TRUSTED_CONTACT_REVOKE","trusted_contact",row.id); db.commit()
    return {"id":row.id,"status":"REVOKED"}
