from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Product, User, get_db
from app.dependencies import get_current_user_optional
from app.services.analytics import get_contacts
from app.services.auth import generate_csrf_token

router = APIRouter(tags=["pages"])
settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
_static_root = Path(__file__).resolve().parent.parent / "static"
templates.env.globals["static_v"] = int((_static_root / "css" / "theme.css").stat().st_mtime)


def _admin_context(request: Request, user: User | None, page: str, **extra):
    return {
        "request": request,
        "user": user,
        "page": page,
        "app_name": settings.app_name,
        "admin_prefix": settings.admin_path_prefix,
        **extra,
    }


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    db: Session = Depends(get_db),
):
    contacts = get_contacts(db)
    csrf = request.cookies.get("csrf_token") or generate_csrf_token()

    catalog_products = (
        db.query(Product)
        .filter(Product.is_active.is_(True))
        .order_by(Product.volume_liters.asc().nulls_last(), Product.title)
        .all()
    )

    response = templates.TemplateResponse(
        "public/index.html",
        {
            "request": request,
            "contacts": contacts.model_dump(),
            "catalog_products": catalog_products,
            "csrf_token": csrf,
            "site_url": settings.site_url,
        },
    )
    if not request.cookies.get("csrf_token"):
        response.set_cookie("csrf_token", csrf, httponly=False, samesite="lax", secure=settings.cookie_secure)
    return response


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request, db: Session = Depends(get_db)):
    contacts = get_contacts(db)
    return templates.TemplateResponse(
        "public/privacy.html",
        {
            "request": request,
            "contacts": contacts.model_dump(),
            "site_url": settings.site_url,
        },
    )


@router.get(f"{settings.admin_path_prefix}/login", response_class=HTMLResponse)
def admin_login(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url=f"{settings.admin_path_prefix}/clients", status_code=302)
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "app_name": settings.app_name, "admin_prefix": settings.admin_path_prefix},
    )


def _require_user_page(request: Request, user: User | None):
    if not user:
        return RedirectResponse(url=f"{settings.admin_path_prefix}/login", status_code=302)
    return None


@router.get(f"{settings.admin_path_prefix}/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, user: User | None = Depends(get_current_user_optional)):
    redirect = _require_user_page(request, user)
    if redirect:
        return redirect
    return RedirectResponse(url=f"{settings.admin_path_prefix}/clients", status_code=302)


@router.get(f"{settings.admin_path_prefix}/kanban", response_class=HTMLResponse)
def admin_kanban(request: Request, user: User | None = Depends(get_current_user_optional)):
    redirect = _require_user_page(request, user)
    if redirect:
        return redirect
    return RedirectResponse(url=f"{settings.admin_path_prefix}/clients", status_code=302)


@router.get(f"{settings.admin_path_prefix}/clients", response_class=HTMLResponse)
def admin_clients(request: Request, user: User | None = Depends(get_current_user_optional)):
    redirect = _require_user_page(request, user)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "admin/clients.html",
        _admin_context(request, user, "clients"),
    )


@router.get(f"{settings.admin_path_prefix}/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request, user: User | None = Depends(get_current_user_optional)):
    redirect = _require_user_page(request, user)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "admin/analytics.html",
        _admin_context(request, user, "analytics"),
    )


@router.get(f"{settings.admin_path_prefix}/users", response_class=HTMLResponse)
def admin_users(request: Request, user: User | None = Depends(get_current_user_optional)):
    redirect = _require_user_page(request, user)
    if redirect:
        return redirect
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return RedirectResponse(url=f"{settings.admin_path_prefix}/settings#settings-users", status_code=302)


@router.get(f"{settings.admin_path_prefix}/settings", response_class=HTMLResponse)
def admin_settings_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    redirect = _require_user_page(request, user)
    if redirect:
        return redirect
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return templates.TemplateResponse(
        "admin/settings.html",
        _admin_context(request, user, "settings"),
    )