from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Dict, Optional
import bcrypt
import jwt

from app.core.config import settings


def _get_signing_key() -> bytes:
    """Return a minimum 32-byte cryptographic key derived from settings.SECRET_KEY."""
    raw_key = settings.SECRET_KEY.encode("utf-8")
    if len(raw_key) >= 32:
        return raw_key
    # Derive deterministic 32-byte SHA-256 digest to prevent InsecureKeyLengthWarning
    return hashlib.sha256(raw_key).digest()


def hash_password(password: str) -> str:
    """Hash plaintext password securely using bcrypt with automatic salt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plaintext password matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token for user authentication."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    signing_key = _get_signing_key()
    return jwt.encode(to_encode, signing_key, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and cryptographically verify a JWT access token."""
    try:
        signing_key = _get_signing_key()
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None
