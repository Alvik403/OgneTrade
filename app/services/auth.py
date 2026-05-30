import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import User, UserRole

settings = get_settings()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": user_id, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def require_role(user: User, *roles: str) -> None:
    if user.role not in roles:
        raise PermissionError("Недостаточно прав")


def hash_ip(ip: str) -> str:
    raw = f"{settings.ip_hash_salt}:{ip}".encode()
    return hashlib.sha256(raw).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf_token(session_token: str | None, submitted: str | None) -> bool:
    if not session_token or not submitted:
        return False
    return secrets.compare_digest(session_token, submitted)
