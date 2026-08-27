import os
import base64
import hashlib
from datetime import datetime, timedelta
from time import monotonic

from cryptography.fernet import Fernet, InvalidToken
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_login_attempts: dict[str, list[float]] = {}
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "60"))
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))


def _fernet() -> Fernet:
    raw_key = os.getenv("FIELD_ENCRYPTION_KEY") or SECRET_KEY
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes if expires_minutes is not None else ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def encrypt_sensitive_value(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_sensitive_value(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def is_login_limited(identifier: str) -> bool:
    now = monotonic()
    attempts = [
        attempt
        for attempt in _login_attempts.get(identifier, [])
        if now - attempt < LOGIN_WINDOW_SECONDS
    ]
    _login_attempts[identifier] = attempts
    return len(attempts) >= LOGIN_MAX_ATTEMPTS


def record_failed_login(identifier: str):
    now = monotonic()
    _login_attempts.setdefault(identifier, []).append(now)


def clear_failed_logins(identifier: str):
    _login_attempts.pop(identifier, None)
