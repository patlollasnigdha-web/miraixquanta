"""
MIRAI — Authentication Service (M16)
Provides cryptographic password hashing (bcrypt), token issuance (HS256 JWT),
token verification, session revocation, and current-user dependency resolution.
"""

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.api.auth_database import get_db, SessionLocal, User, RevokedToken

_SECRET = os.getenv("MIRAI_SECRET_KEY") or os.getenv("SECRET_KEY") or "mirai_production_quant_secret_key_2026_secured"
_TTL = int(os.getenv("MIRAI_TOKEN_TTL_SECONDS", "86400"))
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hashes plain text password using bcrypt with 12 rounds."""
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("Password must be 72 UTF-8 bytes or fewer")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies plain text password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    """URL-safe base64 encoding without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_token(user_id: int, ttl_seconds: Optional[int] = None) -> str:
    """Generates standard HS256 JWT access token."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + (ttl_seconds or _TTL),
    }
    body = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def decode_token(token: str) -> int:
    """Decodes and cryptographically validates JWT token, checking expiration and revocation."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed token")
        head, body, sig = parts
        signed = f"{head}.{body}"
        expected = _b64(hmac.new(_SECRET.encode(), signed.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid signature")

        padded = body + "=" * ((4 - len(body) % 4) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
        if int(claims["exp"]) < int(time.time()):
            raise ValueError("Token expired")

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db = SessionLocal()
        try:
            if db.get(RevokedToken, token_hash):
                raise ValueError("Token revoked")
        finally:
            db.close()

        return int(claims["sub"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency to retrieve authenticated user from Bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def revoke_token(token: str) -> None:
    """Revokes session token by recording its hash until expiration."""
    try:
        payload = token.split(".")[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        exp = claims.get("exp", int(time.time()) + 86400)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        db = SessionLocal()
        try:
            db.merge(
                RevokedToken(
                    token_hash=token_hash,
                    expires_at=datetime.fromtimestamp(int(exp), timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def public_user(user: User) -> dict:
    """Converts User SQLAlchemy model into public JSON schema."""
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "username": user.username,
        "phone": user.phone,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
