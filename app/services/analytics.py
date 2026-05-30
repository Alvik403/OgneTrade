from datetime import date, datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import CardClick, Lead, PageView, Product, SiteSetting
from app.schemas import ContactsSettings, NotificationSettings
from app.services.auth import hash_ip

DEFAULT_CONTACTS = ContactsSettings().model_dump()
DEFAULT_NOTIFICATIONS = NotificationSettings().model_dump()

PERIOD_DELTAS = {
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}

PERIOD_META = {
    "6h": {"granularity": "hour", "step_hours": 1, "label": "по часам"},
    "12h": {"granularity": "hour", "step_hours": 1, "label": "по часам"},
    "24h": {"granularity": "hour", "step_hours": 1, "label": "по часам"},
    "7d": {"granularity": "day", "step_hours": 24, "label": "по дням"},
    "30d": {"granularity": "day", "step_hours": 24, "label": "по дням"},
    "90d": {"granularity": "day", "step_hours": 24, "label": "по дням"},
}


def get_setting(db: Session, key: str, default: dict | None = None) -> dict:
    row = db.get(SiteSetting, key)
    if row:
        return row.value
    return default or {}


def set_setting(db: Session, key: str, value: dict) -> None:
    row = db.get(SiteSetting, key)
    if row:
        row.value = value
    else:
        db.add(SiteSetting(key=key, value=value))
    db.commit()


def get_contacts(db: Session) -> ContactsSettings:
    data = get_setting(db, "contacts", DEFAULT_CONTACTS)
    return ContactsSettings(**data)


def get_notification_settings(db: Session) -> NotificationSettings:
    data = get_setting(db, "notifications", DEFAULT_NOTIFICATIONS)
    return NotificationSettings(**data)


def record_page_view(db: Session, session_id: str, ip: str, referrer: str | None, user_agent: str | None):
    db.add(
        PageView(
            session_id=session_id,
            ip_hash=hash_ip(ip),
            referrer=referrer,
            user_agent=user_agent,
        )
    )
    db.commit()


def record_card_click(db: Session, product_id: str, session_id: str):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        return False
    db.add(CardClick(product_id=product_id, session_id=session_id))
    db.commit()
    return True


def _parse_period(period: str) -> tuple[datetime, datetime, str, timedelta]:
    meta = PERIOD_META.get(period, PERIOD_META["7d"])
    delta = PERIOD_DELTAS.get(period, PERIOD_DELTAS["7d"])
    granularity = meta["granularity"]
    step = timedelta(hours=meta["step_hours"])
    now = datetime.utcnow()
    return now - delta, now, granularity, step


def _floor_datetime(dt: datetime, granularity: str) -> datetime:
    if granularity == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _normalize_bucket(value, granularity: str) -> datetime:
    if isinstance(value, datetime):
        return _floor_datetime(value, granularity)
    if isinstance(value, date):
        return _floor_datetime(datetime(value.year, value.month, value.day), granularity)
    text = str(value).strip().replace("T", " ")
    for fmt, size in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:00:00", 16), ("%Y-%m-%d", 10)):
        try:
            return _floor_datetime(datetime.strptime(text[:size], fmt), granularity)
        except ValueError:
            continue
    try:
        return _floor_datetime(datetime.fromisoformat(text), granularity)
    except ValueError:
        return _floor_datetime(datetime.utcnow(), granularity)


def _generate_buckets(since: datetime, now: datetime, granularity: str, step: timedelta) -> list[datetime]:
    start = _floor_datetime(since, granularity)
    end = _floor_datetime(now, granularity)
    buckets: list[datetime] = []
    current = start
    while current <= end:
        buckets.append(current)
        current += step
    if not buckets:
        buckets.append(end)
    return buckets


def _format_bucket(value: datetime, granularity: str, period: str) -> str:
    if granularity == "hour":
        if period in {"6h", "12h"}:
            return value.strftime("%H:%M")
        return value.strftime("%d.%m %H:%M")
    if period == "7d":
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return f"{weekdays[value.weekday()]} {value.strftime('%d.%m')}"
    if period == "90d":
        return value.strftime("%d.%m")
    return value.strftime("%d.%m.%y")


def _time_bucket(model_created_at, granularity: str, dialect: str):
    if granularity == "hour":
        if dialect == "postgresql":
            return func.date_trunc("hour", model_created_at)
        return func.strftime("%Y-%m-%d %H:00:00", model_created_at)
    if dialect == "postgresql":
        return func.date(model_created_at)
    return func.strftime("%Y-%m-%d", model_created_at)


def _series_dict(db: Session, model, since: datetime, granularity: str) -> dict[datetime, int]:
    dialect = db.bind.dialect.name if db.bind else "postgresql"
    bucket = _time_bucket(model.created_at, granularity, dialect)
    rows = (
        db.query(bucket.label("bucket"), func.count(model.id))
        .filter(model.created_at >= since)
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )
    result: dict[datetime, int] = {}
    for bucket_value, count in rows:
        key = _normalize_bucket(bucket_value, granularity)
        result[key] = result.get(key, 0) + int(count)
    return result


def _build_chart(
    since: datetime,
    now: datetime,
    period: str,
    granularity: str,
    step: timedelta,
    views: dict[datetime, int],
    clicks: dict[datetime, int],
    leads: dict[datetime, int],
) -> dict:
    buckets = _generate_buckets(since, now, granularity, step)
    labels = [_format_bucket(bucket, granularity, period) for bucket in buckets]
    return {
        "labels": labels,
        "timestamps": [bucket.isoformat() for bucket in buckets],
        "views": [views.get(bucket, 0) for bucket in buckets],
        "clicks": [clicks.get(bucket, 0) for bucket in buckets],
        "leads": [leads.get(bucket, 0) for bucket in buckets],
        "intervals": len(buckets),
    }


def analytics_dashboard(db: Session, period: str = "7d") -> dict:
    since, now, granularity, step = _parse_period(period)
    meta = PERIOD_META.get(period, PERIOD_META["7d"])

    views = db.query(func.count(PageView.id)).filter(PageView.created_at >= since).scalar() or 0
    clicks = db.query(func.count(CardClick.id)).filter(CardClick.created_at >= since).scalar() or 0
    leads = db.query(func.count(Lead.id)).filter(Lead.created_at >= since).scalar() or 0
    unread_leads = (
        db.query(func.count(Lead.id))
        .filter(or_(Lead.is_read.is_(False), Lead.is_read.is_(None)))
        .scalar()
        or 0
    )

    views_series = _series_dict(db, PageView, since, granularity)
    clicks_series = _series_dict(db, CardClick, since, granularity)
    leads_series = _series_dict(db, Lead, since, granularity)
    chart = _build_chart(since, now, period, granularity, step, views_series, clicks_series, leads_series)

    top = (
        db.query(Product.title, func.count(CardClick.id).label("clicks"))
        .join(CardClick, CardClick.product_id == Product.id)
        .filter(CardClick.created_at >= since)
        .group_by(Product.id)
        .order_by(func.count(CardClick.id).desc())
        .limit(5)
        .all()
    )

    return {
        "period": period,
        "granularity": granularity,
        "granularity_label": meta["label"],
        "range": {"from": since.isoformat(), "to": now.isoformat()},
        "summary": {
            "views": views,
            "clicks": clicks,
            "leads": leads,
            "conversion_rate": round((leads / views * 100) if views else 0, 2),
            "click_rate": round((clicks / views * 100) if views else 0, 2),
            "lead_rate": round((leads / clicks * 100) if clicks else 0, 2),
            "unread_leads": unread_leads,
        },
        "chart": chart,
        "top_products": [{"title": title, "clicks": count} for title, count in top],
    }


def analytics_overview(db: Session, days: int = 7) -> dict:
    period = f"{days}d" if str(days) in {"7", "30", "90"} else "7d"
    if days == 1:
        period = "24h"
    dashboard = analytics_dashboard(db, period)
    summary = dashboard["summary"]
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    views_today = db.query(func.count(PageView.id)).filter(PageView.created_at >= today_start).scalar() or 0
    clicks_today = db.query(func.count(CardClick.id)).filter(CardClick.created_at >= today_start).scalar() or 0
    leads_today = db.query(func.count(Lead.id)).filter(Lead.created_at >= today_start).scalar() or 0

    return {
        "views_today": views_today,
        "clicks_today": clicks_today,
        "leads_today": leads_today,
        "conversion_rate": summary["conversion_rate"],
        "new_leads_count": summary["unread_leads"],
        "top_products": dashboard["top_products"],
    }


def visits_by_day(db: Session, days: int = 30) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(func.date(PageView.created_at).label("day"), func.count(PageView.id))
        .filter(PageView.created_at >= since)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
        .all()
    )
    return [{"date": str(day), "count": count} for day, count in rows]


def clicks_by_product(db: Session, days: int = 30) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(Product.title, func.count(CardClick.id))
        .join(CardClick, CardClick.product_id == Product.id)
        .filter(CardClick.created_at >= since)
        .group_by(Product.id)
        .order_by(func.count(CardClick.id).desc())
        .all()
    )
    return [{"title": title, "clicks": count} for title, count in rows]


def funnel_stats(db: Session, days: int = 30) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    views = db.query(func.count(PageView.id)).filter(PageView.created_at >= since).scalar() or 0
    clicks = db.query(func.count(CardClick.id)).filter(CardClick.created_at >= since).scalar() or 0
    leads = db.query(func.count(Lead.id)).filter(Lead.created_at >= since).scalar() or 0
    return {
        "views": views,
        "clicks": clicks,
        "leads": leads,
        "click_rate": round((clicks / views * 100) if views else 0, 2),
        "lead_rate": round((leads / clicks * 100) if clicks else 0, 2),
    }
