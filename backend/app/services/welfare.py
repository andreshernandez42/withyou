from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import WelfareCheck, WelfareConfirmation, SafetyStatus, TrustedContact
from app.services.common import utcnow, notify, audit
from app.services.policy import contact_relation, default_policy
from app.services.vault import latest_checkpoint, set_incident_hold


def request_welfare(db: Session, requester_id: str, subject_id: str, reason: str) -> WelfareCheck:
    rel = contact_relation(db, subject_id, requester_id)
    if not rel or not rel.can_request_welfare:
        raise PermissionError("El solicitante no está autorizado para pedir verificación")
    policy = default_policy(db, subject_id)
    quorum_required = policy.quorum_required if policy else 2
    cp = latest_checkpoint(db, subject_id)
    row = WelfareCheck(
        subject_user_id=subject_id,
        requester_user_id=requester_id,
        status="CHECK_REQUESTED",
        reason=reason,
        requested_at=utcnow(),
        expires_at=utcnow() + timedelta(hours=2),
        quorum_required=quorum_required,
        quorum_count=1,
        last_checkpoint_id=cp.id if cp else None,
    )
    db.add(row)
    db.flush()
    db.add(WelfareConfirmation(welfare_check_id=row.id, contact_user_id=requester_id, response="ALSO_CONCERNED"))
    notify(db, subject_id, "WELFARE_CHECK", "Un contacto quiere confirmar que estás bien", reason, {"welfare_check_id": row.id})
    # Ask the rest of the trusted circle for quorum confirmation.
    others = db.scalars(select(TrustedContact).where(
        TrustedContact.owner_user_id == subject_id,
        TrustedContact.status == "ACCEPTED",
        TrustedContact.can_request_welfare == True,
        TrustedContact.contact_user_id.is_not(None),
        TrustedContact.contact_user_id != requester_id,
    )).all()
    for contact in others:
        notify(db, contact.contact_user_id, "QUORUM_REQUEST", "¿También intentas contactar a esta persona?", reason, {"welfare_check_id": row.id})
    audit(db, requester_id, "WELFARE_REQUEST", "welfare_check", row.id, metadata={"subject_user_id": subject_id, "quorum": quorum_required})
    return row


def confirm_quorum(db: Session, check: WelfareCheck, contact_user_id: str, response: str) -> WelfareCheck:
    rel = contact_relation(db, check.subject_user_id, contact_user_id)
    if not rel:
        raise PermissionError("El contacto no pertenece al círculo de confianza")
    existing = db.scalar(select(WelfareConfirmation).where(
        WelfareConfirmation.welfare_check_id == check.id,
        WelfareConfirmation.contact_user_id == contact_user_id,
    ).limit(1))
    if existing:
        existing.response = response
    else:
        db.add(WelfareConfirmation(welfare_check_id=check.id, contact_user_id=contact_user_id, response=response))
    db.flush()
    count = db.scalar(select(func.count(WelfareConfirmation.id)).where(
        WelfareConfirmation.welfare_check_id == check.id,
        WelfareConfirmation.response == "ALSO_CONCERNED",
    )) or 0
    check.quorum_count = int(count)
    if check.quorum_count >= check.quorum_required:
        check.status = "TRUSTED_QUORUM_MET"
        cp = latest_checkpoint(db, check.subject_user_id)
        if cp:
            set_incident_hold(db, cp, contact_user_id, f"Quórum de confianza en {check.id}")
    else:
        check.status = "TRUSTED_QUORUM_PENDING"
    audit(db, contact_user_id, "WELFARE_QUORUM_RESPONSE", "welfare_check", check.id, metadata={"response": response, "count": count})
    return check
