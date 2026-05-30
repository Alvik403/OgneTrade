from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import User, get_db
from app.dependencies import require_admin, require_manager
from app.schemas import SiteSettingsUpdate
from app.services.analytics import (
    analytics_dashboard,
    analytics_overview,
    clicks_by_product,
    funnel_stats,
    get_contacts,
    get_notification_settings,
    get_setting,
    set_setting,
    visits_by_day,
)
from app.services.notifications import send_test_notification

router = APIRouter(prefix="/analytics", tags=["admin-analytics"])


@router.get("/overview")
def overview(days: int = 7, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    return analytics_overview(db, days)


@router.get("/dashboard")
def dashboard(period: str = "7d", db: Session = Depends(get_db), user: User = Depends(require_manager)):
    return analytics_dashboard(db, period)


@router.get("/visits")
def visits(days: int = 30, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    return visits_by_day(db, days)


@router.get("/clicks")
def clicks(days: int = 30, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    return clicks_by_product(db, days)


@router.get("/funnel")
def funnel(days: int = 30, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    return funnel_stats(db, days)


settings_router = APIRouter(prefix="/settings", tags=["admin-settings"])


@settings_router.get("")
def get_settings(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return {
        "contacts": get_contacts(db).model_dump(),
        "notifications": get_notification_settings(db).model_dump(),
    }


@settings_router.put("")
def update_settings(payload: SiteSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if payload.contacts:
        set_setting(db, "contacts", payload.contacts.model_dump())
    if payload.notifications:
        set_setting(db, "notifications", payload.notifications.model_dump())
    return get_settings(db, user)


@settings_router.post("/test-notify")
async def test_notify(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return await send_test_notification(db)
