from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    payload = decode_access_token(authorization.split(" ", 1)[1].strip())
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    user = db.get(User, payload.get("sub"))
    if not user or user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Usuario no disponible")
    return user
