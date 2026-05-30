import uuid
from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import User, UserRole, get_db
from app.services.auth import decode_token, verify_csrf_token

settings = get_settings()


def get_session_id(request: Request, response=None) -> str:
    sid = request.cookies.get("sid")
    if sid:
        return sid
    return str(uuid.uuid4())


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        return None
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только для администратора")
    return user


def require_manager(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.SUPER_ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return user


def validate_csrf(request: Request) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    session_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    form_token = None
    if request.headers.get("content-type", "").startswith("application/json"):
        pass
    else:
        form_token = None
    submitted = header_token or request.headers.get("x-csrf-token")
    if not submitted and hasattr(request, "_form_csrf"):
        submitted = request._form_csrf
    if not verify_csrf_token(session_token, submitted):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
