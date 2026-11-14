from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import WelfareCheck, WelfareConfirmation, TrustedContact, CommunityVerification, SafetyStatus
from app.services.timeutils import utcnow, as_utc
from app.services.common import notify, audit
from app.services.policy import contact_relation, default_policy, grant_after_quorum
from app.services.vault import latest_checkpoint, set_incident_hold


def request_welfare(db: Session, requester_id: str, subject_id: str, reason: str) -> WelfareCheck:
    if requester_id == subject_id:
        raise PermissionError("No se permite solicitar verificación propia por este flujo")
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
        expires_at=utcnow() + timedelta(hours=settings.welfare_check_ttl_hours),
        quorum_required=quorum_required,
        quorum_count=1,
        last_checkpoint_id=cp.id if cp else None,
    )
    db.add(row); db.flush()
    db.add(SafetyStatus(user_id=subject_id,welfare_check_id=row.id,status='CHECK_REQUESTED',expires_at=utcnow()+timedelta(hours=settings.welfare_check_ttl_hours)))
    db.add(WelfareConfirmation(welfare_check_id=row.id, contact_user_id=requester_id, response="ALSO_CONCERNED"))
    notify(db, subject_id, "WELFARE_CHECK", "Un contacto quiere confirmar que estás bien", reason,
           {"welfare_check_id": row.id})
    others = db.scalars(select(TrustedContact).where(
        TrustedContact.owner_user_id == subject_id,
        TrustedContact.status == "ACCEPTED",
        TrustedContact.revoked_at.is_(None),
        TrustedContact.can_request_welfare == True,  # noqa: E712
        TrustedContact.contact_user_id.is_not(None),
        TrustedContact.contact_user_id != requester_id,
    )).all()
    for contact in others:
        notify(db, contact.contact_user_id, "QUORUM_REQUEST", "¿También intentas contactar a esta persona?",
               reason, {"welfare_check_id": row.id})
    audit(db, requester_id, "WELFARE_REQUEST", "welfare_check", row.id,
          metadata={"subject_user_id": subject_id, "quorum": quorum_required})
    return row


def confirm_quorum(db: Session, check: WelfareCheck, contact_user_id: str, response: str) -> WelfareCheck:
    if check.expires_at and as_utc(check.expires_at) < utcnow():
        check.status = "EXPIRED"
        raise ValueError("La solicitud de verificación expiró")
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
        granted = grant_after_quorum(db, check)
        audit(db, contact_user_id, "WELFARE_QUORUM_MET", "welfare_check", check.id,
              metadata={"granted_users": granted})
    else:
        check.status = "TRUSTED_QUORUM_PENDING"
    audit(db, contact_user_id, "WELFARE_QUORUM_RESPONSE", "welfare_check", check.id,
          metadata={"response": response, "count": count})
    return check


def activate_community_check(db: Session, check: WelfareCheck, actor_user_id: str) -> WelfareCheck:
    rel = contact_relation(db, check.subject_user_id, actor_user_id)
    if actor_user_id != check.subject_user_id and not rel:
        raise PermissionError("No autorizado")
    policy = default_policy(db, check.subject_user_id)
    if not policy or not policy.allow_community_check:
        raise PermissionError("La política del usuario no permite verificación comunitaria")
    if check.status not in {"TRUSTED_QUORUM_MET", "NO_RESPONSE", "COMMUNITY_HELP_REPORTED"}:
        raise ValueError("El caso aún no cumple condiciones para apoyo comunitario")
    check.community_active = True
    check.status = "COMMUNITY_CHECK_ACTIVE"
    audit(db, actor_user_id, "COMMUNITY_CHECK_ACTIVATE", "welfare_check", check.id)
    return check


def register_community_verification(db: Session, check: WelfareCheck, verifier_user_id: str,
                                    result: str, approximate_distance_m: int | None) -> CommunityVerification:
    if not check.community_active:
        raise ValueError("La verificación comunitaria no está activa")
    if verifier_user_id in {check.subject_user_id, check.requester_user_id}:
        raise PermissionError("El solicitante o sujeto no puede actuar como verificador comunitario")
    existing = db.scalar(select(CommunityVerification).where(
        CommunityVerification.welfare_check_id == check.id,
        CommunityVerification.verifier_user_id == verifier_user_id,
    ).limit(1))
    if existing:
        raise ValueError("Ya existe una verificación de este usuario")
    row = CommunityVerification(
        welfare_check_id=check.id,
        verifier_user_id=verifier_user_id,
        result=result,
        approximate_distance_m=approximate_distance_m,
    )
    db.add(row); db.flush()
    if result == "LOCATED_HELP_REQUIRED":
        check.status = "COMMUNITY_HELP_REPORTED"
    elif result == "LOCATED_SAFE":
        count = db.scalar(select(func.count(CommunityVerification.id)).where(
            CommunityVerification.welfare_check_id == check.id,
            CommunityVerification.result == "LOCATED_SAFE",
        )) or 0
        if int(count) >= settings.community_confirmation_threshold:
            check.status = "COMMUNITY_SAFE_CONFIRMED"
    audit(db, verifier_user_id, "COMMUNITY_VERIFICATION", "welfare_check", check.id,
          metadata={"result": result, "distance_m": approximate_distance_m})
    return row


def expire_welfare_checks(db: Session) -> int:
    rows = db.scalars(select(WelfareCheck).where(
        WelfareCheck.expires_at.is_not(None),
        WelfareCheck.expires_at <= utcnow(),
        WelfareCheck.status.in_(["CHECK_REQUESTED", "TRUSTED_QUORUM_PENDING"]),
    )).all()
    for row in rows:
        row.status = "EXPIRED"
        audit(db, None, "WELFARE_EXPIRED", "welfare_check", row.id)
    return len(rows)
