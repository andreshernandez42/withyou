from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, new_refresh_token, hash_token
from app.core.dependencies import current_user
from app.models import User, ConsentPolicy, RefreshSession
from app.schemas.api import RegisterIn, LoginIn, RefreshIn
from app.services.common import audit
from app.services.timeutils import utcnow, as_utc

router = APIRouter(tags=["auth"])


def _user_out(user: User) -> dict:
    return {"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role,
            "is_minor": user.is_minor, "community_opt_in": user.community_opt_in, "locale": user.locale, "status": user.status}


def _tokens(db: Session, user: User) -> dict:
    access = create_access_token(user.id, user.email, user.role)
    refresh_raw, refresh_hash = new_refresh_token()
    db.add(RefreshSession(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
    ))
    return {"access_token": access, "refresh_token": refresh_raw, "token_type": "bearer", "expires_in": settings.access_token_minutes * 60, "user": _user_out(user)}


@router.post("/auth/register", status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "El correo ya está registrado")
    user = User(full_name=payload.full_name.strip(), email=email, password_hash=hash_password(payload.password),
                is_minor=payload.is_minor, locale=payload.locale)
    db.add(user); db.flush()
    db.add(ConsentPolicy(user_id=user.id, quorum_required=2, allow_exact_location=True,
                         allow_coarse_location=True, release_after_quorum=True,
                         release_on_official_event_no_response=True))
    audit(db, user.id, "USER_REGISTER", "user", user.id)
    db.commit(); db.refresh(user)
    return _user_out(user)


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash) or user.status != "ACTIVE":
        raise HTTPException(401, "Credenciales inválidas")
    result = _tokens(db, user)
    audit(db, user.id, "LOGIN", "user", user.id)
    db.commit()
    return result


@router.post("/auth/refresh")
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash).limit(1))
    if not session or session.revoked_at is not None or as_utc(session.expires_at) <= utcnow():
        raise HTTPException(401, "Refresh token inválido o expirado")
    user = db.get(User, session.user_id)
    if not user or user.status != "ACTIVE":
        raise HTTPException(401, "Usuario no disponible")
    session.revoked_at = utcnow()  # rotación
    result = _tokens(db, user)
    audit(db, user.id, "TOKEN_REFRESH", "refresh_session", session.id)
    db.commit()
    return result


@router.post("/auth/logout")
def logout(payload: RefreshIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(RefreshSession).where(
        RefreshSession.user_id == user.id,
        RefreshSession.token_hash == hash_token(payload.refresh_token),
        RefreshSession.revoked_at.is_(None),
    ).limit(1))
    if session:
        session.revoked_at = utcnow()
    audit(db, user.id, "LOGOUT", "user", user.id)
    db.commit()
    return {"status": "ok"}
