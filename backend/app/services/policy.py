from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import TrustedContact, ConsentPolicy


def contact_relation(db: Session, owner_user_id: str, requester_user_id: str) -> TrustedContact | None:
    return db.scalar(
        select(TrustedContact).where(
            TrustedContact.owner_user_id == owner_user_id,
            TrustedContact.contact_user_id == requester_user_id,
            TrustedContact.status == "ACCEPTED",
        ).limit(1)
    )


def default_policy(db: Session, user_id: str) -> ConsentPolicy | None:
    return db.scalar(
        select(ConsentPolicy).where(ConsentPolicy.user_id == user_id, ConsentPolicy.active == True)
        .order_by(ConsentPolicy.created_at.asc()).limit(1)
    )
