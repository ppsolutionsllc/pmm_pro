from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.config import settings

# use pbkdf2_sha256 to avoid invoking any bcrypt backend.
# the docker environment was triggering a passlib startup bug while
# detecting the bcrypt backend, resulting in a ValueError and crashing the
# application.  switching to pbkdf2_sha256 sidesteps that entirely.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _looks_like_bcrypt_hash(value: str) -> bool:
    token = str(value or "")
    return token.startswith("$2a$") or token.startswith("$2b$") or token.startswith("$2y$")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if _looks_like_bcrypt_hash(hashed_password):
        try:
            return bcrypt.checkpw(
                str(plain_password or "").encode("utf-8"),
                str(hashed_password or "").encode("utf-8"),
            )
        except Exception:
            return False
    return pwd_context.verify(plain_password, hashed_password)


def needs_password_rehash(hashed_password: str) -> bool:
    token = str(hashed_password or "")
    if not token:
        return False
    if _looks_like_bcrypt_hash(token):
        return True
    try:
        return bool(pwd_context.needs_update(token))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    # bcrypt has a maximum password length of 72 bytes. If a longer string
    # slips through (for example due to an unexpected env var), passlib will
    # raise ValueError during hashing which would crash the application at
    # startup when seeding the admin user.  Handle that gracefully by
    # truncating or falling back to another algorithm.
    try:
        return pwd_context.hash(password)
    except ValueError:
        # trim to 72 bytes (utf-8) and retry
        trimmed = password.encode("utf-8")[:72].decode("utf-8", "ignore")
        return pwd_context.hash(trimmed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
