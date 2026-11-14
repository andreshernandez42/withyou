from __future__ import annotations
import base64
import hashlib
import json
import secrets
from datetime import timedelta
from typing import Any
import jwt
from argon2 import PasswordHasher
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
from app.services.timeutils import utcnow

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.token_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.token_secret, algorithms=["HS256"])
        return payload if payload.get("typ") == "access" else None
    except jwt.PyJWTError:
        return None


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fernet() -> Fernet:
    key = settings.field_encryption_key.strip()
    if not key:
        # Solo para DEV/TEST. En producción validate_runtime_settings obliga a configurarla.
        digest = hashlib.sha256(settings.token_secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest).decode("ascii")
    return Fernet(key.encode("ascii"))


def encrypt_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(raw).decode("ascii")


def decrypt_json(token: str) -> dict[str, Any] | None:
    try:
        raw = _fernet().decrypt(token.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError):
        return None
