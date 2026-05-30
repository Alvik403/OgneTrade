import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import User, get_db
from app.dependencies import get_current_user
from app.limiter import limiter
from app.schemas import LoginRequest, UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
)

router = APIRouter(prefix="/auth", tags=["admin-auth"])
settings = get_settings()


def _set_auth_cookies(response: Response, access: str, refresh: str, csrf: str):
    common = {"httponly": True, "samesite": "lax", "secure": settings.cookie_secure}
    response.set_cookie("access_token", access, max_age=settings.access_token_expire_minutes * 60, **common)
    response.set_cookie("refresh_token", refresh, max_age=settings.refresh_token_expire_days * 86400, **common)
    response.set_cookie("csrf_token", csrf, httponly=False, samesite="lax", secure=settings.cookie_secure)


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        await asyncio.sleep(1)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    csrf = generate_csrf_token()
    _set_auth_cookies(response, access, refresh, csrf)
    return {"ok": True, "user": UserResponse.model_validate(user)}


@router.post("/logout")
async def logout(response: Response):
    for name in ("access_token", "refresh_token", "csrf_token"):
        response.delete_cookie(name)
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    access = create_access_token(user.id, user.role)
    csrf = generate_csrf_token()
    _set_auth_cookies(response, access, token, csrf)
    return {"ok": True}
