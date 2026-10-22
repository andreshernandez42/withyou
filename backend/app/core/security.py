from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any
from argon2 import PasswordHasher
from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .config import settings

_password_hasher = PasswordHasher()
_serializer = URLSafeTimedSerializer(settings.token_secret, salt="withyou-auth-v1")


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    return _serializer.dumps({"sub": user_id, "email": email, "iat": int(time.time())})


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return _serializer.loads(token, max_age=settings.token_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


def _fernet() -> Fernet:
    key = settings.field_encryption_key.strip()
    if not key:
        # Deterministic fallback for local development only. Production must set FIELD_ENCRYPTION_KEY.
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
