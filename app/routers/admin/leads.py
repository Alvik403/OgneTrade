from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import Lead, LeadComment, LeadStatusHistory, Product, User, get_db
from app.dependencies import get_current_user, require_manager
from app.schemas import CommentCreate, CommentResponse, LeadResponse, LeadStatusUpdate, LeadUpdate

router = APIRouter(prefix="/leads", tags=["admin-leads"])

SUB_STATUSES = {
    "in_progress": ["Позвонили", "КП отправлено", "Ждём решения"],
    "done": ["Оплачено", "Отказ", "Не дозвонились"],
}


def _lead_is_read(lead: Lead) -> bool:
    return lead.is_read is True


def _apply_read_filter(query, read: bool | None):
    if read is None:
        return query
    if read:
        return query.filter(Lead.is_read.is_(True))
    return query.filter(or_(Lead.is_read.is_(False), Lead.is_read.is_(None)))


def _apply_lead_filters(query, client: str | None = None, product: str | None = None):
    if client:
        term = f"%{client.strip()}%"
        query = query.filter(
            or_(
                Lead.name.ilike(term),
                Lead.phone.ilike(term),
                Lead.email.ilike(term),
            )
        )
    if product is not None:
        if product == "__none__":
            query = query.filter(or_(Lead.product_name_snapshot.is_(None), Lead.product_name_snapshot == ""))
        else:
            query = query.filter(Lead.product_name_snapshot == product)
    return query


def _serialize_lead(lead: Lead) -> dict:
    comments = [
        CommentResponse(
            id=c.id,
            text=c.text,
            author_name=c.author.full_name if c.author else "—",
            created_at=c.created_at,
        )
        for c in sorted(lead.comments, key=lambda x: x.created_at)
    ]
    return LeadResponse(
        id=lead.id,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        product_id=lead.product_id,
        product_name_snapshot=lead.product_name_snapshot,
        status=lead.status,
        sub_status=lead.sub_status,
        amount=float(lead.amount) if lead.amount is not None else None,
        assigned_to=lead.assigned_to,
        assignee_name=lead.assignee.full_name if lead.assignee else None,
        comment_initial=lead.comment_initial,
        is_read=_lead_is_read(lead),
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        comments=comments,
    ).model_dump()


@router.get("")
def list_leads(
    status: str | None = None,
    read: bool | None = Query(default=None),
    client: str | None = Query(default=None),
    product: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    query = db.query(Lead).options(joinedload(Lead.comments).joinedload(LeadComment.author), joinedload(Lead.assignee))
    if status:
        query = query.filter(Lead.status == status)
    query = _apply_read_filter(query, read)
    query = _apply_lead_filters(query, client, product)
    leads = query.order_by(Lead.created_at.desc()).all()
    return [_serialize_lead(l) for l in leads]


@router.get("/suggest")
def suggest_leads(
    q: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    needle = q.strip()
    term = f"%{needle}%"
    rows = (
        db.query(Lead)
        .filter(
            or_(
                Lead.name.ilike(term),
                Lead.phone.ilike(term),
                Lead.email.ilike(term),
            )
        )
        .order_by(Lead.created_at.desc())
        .limit(8)
        .all()
    )
    needle_lower = needle.lower()
    suggestions = []
    for lead in rows:
        if lead.name and needle_lower in lead.name.lower():
            query_value = lead.name
        elif lead.phone and needle_lower in lead.phone.lower():
            query_value = lead.phone
        elif lead.email and needle_lower in lead.email.lower():
            query_value = lead.email
        else:
            query_value = lead.name or lead.phone or lead.email or needle
        detail_parts = [part for part in [lead.phone, lead.email] if part]
        suggestions.append(
            {
                "id": lead.id,
                "query": query_value,
                "label": lead.name or lead.phone or lead.email or "—",
                "detail": " · ".join(detail_parts),
            }
        )
    return suggestions


@router.get("/meta/products")
def lead_product_filters(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    lead_counts = dict(
        db.query(Lead.product_name_snapshot, func.count(Lead.id))
        .group_by(Lead.product_name_snapshot)
        .all()
    )
    catalog = (
        db.query(Product.title)
        .filter(Product.is_active.is_(True))
        .order_by(Product.volume_liters.asc().nulls_last(), Product.title)
        .all()
    )

    products = []
    seen = set()
    for (title,) in catalog:
        count = lead_counts.get(title, 0)
        products.append({"name": title, "key": title, "count": count})
        seen.add(title)

    none_count = lead_counts.get(None, 0) + lead_counts.get("", 0)
    for name, count in lead_counts.items():
        if not name or not str(name).strip():
            continue
        if name not in seen:
            products.append({"name": name, "key": name, "count": count})

    if none_count:
        products.append({"name": "Без товара", "key": "__none__", "count": none_count})

    return products


@router.get("/counts")
def lead_counts(
    client: str | None = Query(default=None),
    product: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    def filtered_query():
        return _apply_lead_filters(db.query(Lead), client, product)

    total = filtered_query().count()
    unread = _apply_read_filter(filtered_query(), False).count()
    read = _apply_read_filter(filtered_query(), True).count()
    return {"total": total, "unread": unread, "read": read}


@router.get("/meta/sub-statuses")
def sub_statuses():
    return SUB_STATUSES


@router.get("/{lead_id}")
def get_lead(lead_id: str, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    lead = (
        db.query(Lead)
        .options(joinedload(Lead.comments).joinedload(LeadComment.author), joinedload(Lead.assignee))
        .filter(Lead.id == lead_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.is_read:
        lead.is_read = True
        db.commit()
        db.refresh(lead)
    return _serialize_lead(lead)


@router.post("/{lead_id}/read")
def mark_lead_read(lead_id: str, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.is_read = True
    db.commit()
    db.refresh(lead)
    return _serialize_lead(lead)


@router.post("/{lead_id}/unread")
def mark_lead_unread(lead_id: str, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.is_read = False
    db.commit()
    db.refresh(lead)
    return _serialize_lead(lead)


@router.patch("/{lead_id}")
def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_status = lead.status
    old_sub = lead.sub_status
    data = payload.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(lead, key, value)

    if ("status" in data and data["status"] != old_status) or (
        "sub_status" in data and data.get("sub_status") != old_sub
    ):
        db.add(
            LeadStatusHistory(
                lead_id=lead.id,
                user_id=user.id,
                old_status=old_status if "status" in data else lead.status,
                new_status=lead.status,
                old_sub_status=old_sub,
                new_sub_status=lead.sub_status,
            )
        )

    db.commit()
    db.refresh(lead)
    return _serialize_lead(lead)


@router.patch("/{lead_id}/status")
def update_status(
    lead_id: str,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    old_status = lead.status
    old_sub = lead.sub_status
    lead.status = payload.status
    lead.sub_status = payload.sub_status
    if payload.status != old_status or payload.sub_status != old_sub:
        db.add(
            LeadStatusHistory(
                lead_id=lead.id,
                user_id=user.id,
                old_status=old_status,
                new_status=lead.status,
                old_sub_status=old_sub,
                new_sub_status=lead.sub_status,
            )
        )
    db.commit()
    db.refresh(lead)
    return _serialize_lead(lead)


@router.post("/{lead_id}/comments")
def add_comment(
    lead_id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    comment = LeadComment(lead_id=lead_id, author_id=user.id, text=payload.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        text=comment.text,
        author_name=user.full_name,
        created_at=comment.created_at,
    )


@router.get("/{lead_id}/history")
def status_history(lead_id: str, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    rows = (
        db.query(LeadStatusHistory)
        .filter(LeadStatusHistory.lead_id == lead_id)
        .order_by(LeadStatusHistory.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "old_status": r.old_status,
            "new_status": r.new_status,
            "old_sub_status": r.old_sub_status,
            "new_sub_status": r.new_sub_status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
