from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import TrustedContact, ConsentPolicy, LocationAccessGrant, WelfareConfirmation
from app.services.timeutils import utcnow
from app.services.common import audit


def contact_relation(db: Session, owner_user_id: str, requester_user_id: str) -> TrustedContact | None:
    return db.scalar(
        select(TrustedContact).where(
            TrustedContact.owner_user_id == owner_user_id,
            TrustedContact.contact_user_id == requester_user_id,
            TrustedContact.status == "ACCEPTED",
            TrustedContact.revoked_at.is_(None),
        ).limit(1)
    )


def default_policy(db: Session, user_id: str, event_type: str | None = None) -> ConsentPolicy | None:
    q = select(ConsentPolicy).where(ConsentPolicy.user_id == user_id, ConsentPolicy.active == True)  # noqa: E712
    rows = db.scalars(q.order_by(ConsentPolicy.created_at.desc())).all()
    if event_type:
        for row in rows:
            if row.event_type.upper() == event_type.upper():
                return row
    for row in rows:
        if row.event_type.upper() == "GENERAL":
            return row
    return rows[0] if rows else None


def issue_location_grant(db: Session, subject_user_id: str, grantee_user_id: str, level: str,
                         reason: str, source_type: str, source_id: str | None,
                         ttl_minutes: int) -> LocationAccessGrant:
    now = utcnow()
    active = db.scalar(select(LocationAccessGrant).where(
        LocationAccessGrant.subject_user_id == subject_user_id,
        LocationAccessGrant.grantee_user_id == grantee_user_id,
        LocationAccessGrant.source_type == source_type,
        LocationAccessGrant.source_id == source_id,
        LocationAccessGrant.revoked_at.is_(None),
        LocationAccessGrant.expires_at > now,
    ).limit(1))
    if active:
        return active
    row = LocationAccessGrant(
        subject_user_id=subject_user_id,
        grantee_user_id=grantee_user_id,
        level=level,
        reason=reason,
        source_type=source_type,
        source_id=source_id,
        expires_at=now + timedelta(minutes=ttl_minutes),
    )
    db.add(row); db.flush()
    audit(db, subject_user_id, "LOCATION_GRANT_CREATE", "location_access_grant", row.id,
          metadata={"grantee": grantee_user_id, "level": level, "source_type": source_type, "source_id": source_id})
    return row


def active_location_grant(db: Session, subject_user_id: str, grantee_user_id: str) -> LocationAccessGrant | None:
    return db.scalar(select(LocationAccessGrant).where(
        LocationAccessGrant.subject_user_id == subject_user_id,
        LocationAccessGrant.grantee_user_id == grantee_user_id,
        LocationAccessGrant.revoked_at.is_(None),
        LocationAccessGrant.expires_at > utcnow(),
    ).order_by(LocationAccessGrant.created_at.desc()).limit(1))


def revoke_location_grants(db: Session, subject_user_id: str, grantee_user_id: str | None = None) -> int:
    q = select(LocationAccessGrant).where(
        LocationAccessGrant.subject_user_id == subject_user_id,
        LocationAccessGrant.revoked_at.is_(None),
    )
    if grantee_user_id:
        q = q.where(LocationAccessGrant.grantee_user_id == grantee_user_id)
    rows = db.scalars(q).all()
    now = utcnow()
    for row in rows:
        row.revoked_at = now
    return len(rows)


def grant_after_quorum(db: Session, check) -> list[str]:
    policy = default_policy(db, check.subject_user_id)
    if not policy or not policy.release_after_quorum:
        return []
    confirmations = db.scalars(select(WelfareConfirmation).where(
        WelfareConfirmation.welfare_check_id == check.id,
        WelfareConfirmation.response == "ALSO_CONCERNED",
    )).all()
    granted = []
    for confirmation in confirmations:
        rel = contact_relation(db, check.subject_user_id, confirmation.contact_user_id)
        if not rel or not rel.can_view_checkpoint:
            continue
        level = "EXACT" if policy.allow_exact_location else "COARSE"
        issue_location_grant(
            db, check.subject_user_id, confirmation.contact_user_id, level,
            "Quórum de confianza satisfecho", "WELFARE_CHECK", check.id,
            policy.access_ttl_minutes,
        )
        granted.append(confirmation.contact_user_id)
    return granted


def grant_for_emergency_contacts(db: Session, subject_user_id: str, source_type: str,
                                 source_id: str | None, reason: str, event_type: str | None = None) -> list[str]:
    policy = default_policy(db, subject_user_id, event_type)
    if not policy:
        return []
    contacts = db.scalars(select(TrustedContact).where(
        TrustedContact.owner_user_id == subject_user_id,
        TrustedContact.status == "ACCEPTED",
        TrustedContact.revoked_at.is_(None),
        TrustedContact.can_receive_sos == True,  # noqa: E712
        TrustedContact.can_view_checkpoint == True,  # noqa: E712
        TrustedContact.contact_user_id.is_not(None),
    )).all()
    level = "EXACT" if policy.allow_exact_location else "COARSE"
    granted = []
    for c in contacts:
        issue_location_grant(db, subject_user_id, c.contact_user_id, level, reason,
                             source_type, source_id, policy.access_ttl_minutes)
        granted.append(c.contact_user_id)
    return granted
