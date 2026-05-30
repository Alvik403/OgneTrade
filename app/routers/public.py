import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import Lead, LeadStatus, LeadStatusHistory, Product, get_db
from app.limiter import limiter
from app.schemas import LeadCreatePublic, TrackClickRequest
from app.services.analytics import get_contacts, record_card_click, record_page_view
from app.services.auth import verify_csrf_token
from app.services.notifications import notify_new_lead

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/settings/contacts")
def public_contacts(db: Session = Depends(get_db)):
    return get_contacts(db).model_dump()


@router.get("/products")
def public_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active.is_(True)).order_by(Product.title).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "image_url": p.image_url,
            "price_from": float(p.price_from),
            "description": p.description,
        }
        for p in products
    ]


@router.post("/track/view")
def track_view(request: Request, response: Response, db: Session = Depends(get_db)):
    sid = request.cookies.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        response.set_cookie("sid", sid, httponly=True, max_age=30 * 24 * 3600, samesite="lax")
    ip = request.client.host if request.client else "0.0.0.0"
    record_page_view(db, sid, ip, request.headers.get("referer"), request.headers.get("user-agent"))
    return {"ok": True}


@router.post("/track/click")
def track_click(payload: TrackClickRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    sid = request.cookies.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        response.set_cookie("sid", sid, httponly=True, max_age=30 * 24 * 3600, samesite="lax")
    ok = record_card_click(db, payload.product_id, sid)
    if not ok:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return {"ok": True}


@router.post("/leads")
@limiter.limit("5/10minutes")
async def create_lead(
    request: Request,
    payload: LeadCreatePublic,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if payload.website:
        return {"ok": True, "message": "Спасибо!"}

    csrf = request.headers.get("X-CSRF-Token")
    if not verify_csrf_token(request.cookies.get("csrf_token"), csrf):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    product_name = payload.product_name
    if payload.product_id and not product_name:
        product = db.get(Product, payload.product_id)
        if product:
            product_name = product.title

    lead = Lead(
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        product_id=payload.product_id,
        product_name_snapshot=product_name,
        comment_initial=payload.comment,
        status=LeadStatus.NEW,
        is_read=False,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    db.add(
        LeadStatusHistory(
            lead_id=lead.id,
            old_status=None,
            new_status=LeadStatus.NEW,
        )
    )
    db.commit()

    background_tasks.add_task(_notify_lead, lead.id)
    return {"ok": True, "message": "Спасибо! Мы перезвоним вам в ближайшее время."}


async def _notify_lead(lead_id: str):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if lead:
            await notify_new_lead(db, lead)
    finally:
        db.close()
