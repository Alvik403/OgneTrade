from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.limiter import limiter
from app.middleware.head_method import HeadMethodMiddleware
from app.config import get_settings
from app.database import init_db
from app.routers import pages
from app.routers.admin import analytics, auth, leads, users
from app.routers.admin.analytics import settings_router
from app.routers.public import router as public_router

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if settings.environment == "production":
    allowed = [host.strip() for host in settings.allowed_hosts.split(",") if host.strip()]
    for internal_host in ("localhost", "127.0.0.1"):
        if internal_host not in allowed:
            allowed.append(internal_host)
    if allowed:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self' cdn.jsdelivr.net;"
        )
        response.headers["Content-Security-Policy"] = csp
        return response


app.add_middleware(SecurityHeadersMiddleware)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

admin_router = APIRouter(prefix="/api/admin")
admin_router.include_router(auth.router)
admin_router.include_router(leads.router)
admin_router.include_router(users.router)
admin_router.include_router(analytics.router)
admin_router.include_router(settings_router)

app.include_router(public_router)
app.include_router(admin_router)
app.include_router(pages.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(static_dir / "favicon.svg", media_type="image/svg+xml")


app = HeadMethodMiddleware(app)
