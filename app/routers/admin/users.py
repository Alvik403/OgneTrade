from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import User, UserRole, get_db
from app.dependencies import require_admin, require_manager
from app.schemas import UserCreate, UserResponse, UserUpdate
from app.services.auth import hash_password

router = APIRouter(prefix="/users", tags=["admin-users"])


@router.get("/managers")
def list_managers(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    managers = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .order_by(User.full_name)
        .all()
    )
    return [UserResponse.model_validate(u) for u in managers]


@router.get("")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("")
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email уже занят")
    if payload.role not in (UserRole.SUPER_ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=400, detail="Invalid role")
    new_user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)


@router.patch("/{user_id}")
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in (UserRole.SUPER_ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=400, detail="Invalid role")
    if (
        "role" in data
        and data["role"] != UserRole.SUPER_ADMIN
        and target.role == UserRole.SUPER_ADMIN
        and target.is_active
    ):
        active_admins = (
            db.query(User)
            .filter(User.role == UserRole.SUPER_ADMIN, User.is_active.is_(True))
            .count()
        )
        if active_admins <= 1:
            raise HTTPException(status_code=400, detail="Нельзя снять роль у последнего администратора")
    if "password" in data:
        target.password_hash = hash_password(data.pop("password"))
    for key, value in data.items():
        setattr(target, key, value)
    db.commit()
    db.refresh(target)
    return UserResponse.model_validate(target)
