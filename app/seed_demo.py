import hashlib
import random
import uuid
from datetime import datetime, timedelta

from app.catalog_data import YAGEL_PRODUCTS
from app.database import (
    CardClick,
    Lead,
    LeadComment,
    LeadStatusHistory,
    NotificationLog,
    PageView,
    Product,
    SessionLocal,
    User,
    engine,
    init_db,
)
from app.migrate import migrate_schema

FIRST_NAMES = [
    "Алексей",
    "Мария",
    "Дмитрий",
    "Елена",
    "Иван",
    "Ольга",
    "Сергей",
    "Анна",
    "Павел",
    "Наталья",
    "Андрей",
    "Татьяна",
    "Михаил",
    "Екатерина",
    "Николай",
]

LAST_NAMES = [
    "Иванов",
    "Петрова",
    "Сидоров",
    "Козлова",
    "Смирнов",
    "Волкова",
    "Новиков",
    "Морозова",
    "Фёдоров",
    "Лебедева",
    "Кузнецов",
    "Соколова",
    "Попов",
    "Васильева",
    "Михайлов",
]

MESSAGES = [
    "Нужен расчёт для офиса на 120 м².",
    "Интересует доставка в регион, уточните сроки.",
    "Хочу заказать партию для склада.",
    "Подскажите, подойдёт ли для серверной?",
    "Нужна консультация по выбору объёма.",
    "Прошу перезвонить после 18:00.",
    "Готов обсудить оптовую поставку.",
    "Нужен монтаж и обучение персонала.",
    "Интересует комплект для автопарка.",
    "Уточните наличие и стоимость доставки.",
    "Хотим протестировать на одном объекте.",
    "Нужен КП для тендера.",
]

REFERRERS = [
    None,
    "https://yandex.ru/",
    "https://google.com/",
    "https://ognetrade.ru/",
    "https://vk.com/",
    None,
    None,
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14) Chrome/121.0 Mobile",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1",
]

LEGACY_PRODUCT_TITLES = {"ОП-4", "ОП-5", "ОУ-3", "CO2-5", "ОП-8"}


def _upsert_yagel_products(db):
    products = []
    for spec in YAGEL_PRODUCTS:
        product = db.query(Product).filter(Product.article == spec["article"]).first()
        if not product:
            product = db.query(Product).filter(Product.title == spec["title"]).first()
        if product:
            for key, value in spec.items():
                setattr(product, key, value)
            product.is_active = True
        else:
            product = Product(**spec)
            db.add(product)
        products.append(product)

    for legacy in db.query(Product).filter(Product.title.in_(LEGACY_PRODUCT_TITLES)).all():
        legacy.is_active = False

    db.flush()
    return sorted(products, key=lambda p: p.volume_liters or 0)


def _random_dt(rng: random.Random, start: datetime, end: datetime) -> datetime:
    seconds = int((end - start).total_seconds())
    if seconds <= 0:
        return end
    return start + timedelta(seconds=rng.randint(0, seconds))


def _fake_ip_hash(rng: random.Random) -> str:
    raw = f"demo-{rng.randint(1, 999999)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _fake_session(rng: random.Random) -> str:
    return uuid.uuid4().hex[:16]


def _fake_phone(rng: random.Random, index: int) -> str:
    code = rng.choice(["903", "905", "916", "925", "926", "929", "931", "965", "977", "999"])
    tail = f"{index:07d}"[-7:]
    return f"+7{code}{tail}"


def clear_demo_data(db) -> dict[str, int]:
    counts = {
        "lead_status_history": db.query(LeadStatusHistory).delete(),
        "lead_comments": db.query(LeadComment).delete(),
        "notification_logs": db.query(NotificationLog).delete(),
        "leads": db.query(Lead).delete(),
        "page_views": db.query(PageView).delete(),
        "card_clicks": db.query(CardClick).delete(),
    }
    db.commit()
    return counts


def seed_demo_data(*, clear: bool = True, min_per_product: int = 10, max_per_product: int = 20) -> dict:
    init_db()
    migrate_schema(engine)

    rng = random.Random(20260522)
    now = datetime.utcnow()
    since = now - timedelta(days=90)

    db = SessionLocal()
    try:
        if clear:
            cleared = clear_demo_data(db)
        else:
            cleared = {}

        products = [p for p in _upsert_yagel_products(db) if p.is_active]
        if not products:
            products = db.query(Product).filter(Product.is_active.is_(True)).all()

        leads_created = 0
        clicks_created = 0
        views_created = 0
        lead_index = 1

        for product in products:
            leads_count = rng.randint(min_per_product, max_per_product)
            clicks_count = rng.randint(min_per_product, max_per_product)

            for _ in range(clicks_count):
                db.add(
                    CardClick(
                        product_id=product.id,
                        session_id=_fake_session(rng),
                        created_at=_random_dt(rng, since, now),
                    )
                )
                clicks_created += 1

            for i in range(leads_count):
                first = rng.choice(FIRST_NAMES)
                last = rng.choice(LAST_NAMES)
                created_at = _random_dt(rng, since, now)
                is_read = rng.random() > 0.42

                db.add(
                    Lead(
                        name=f"{first} {last}",
                        phone=_fake_phone(rng, lead_index),
                        email=f"client{lead_index}@example.ru" if rng.random() > 0.15 else None,
                        product_id=product.id,
                        product_name_snapshot=product.title,
                        comment_initial=rng.choice(MESSAGES),
                        is_read=is_read,
                        created_at=created_at,
                        updated_at=created_at,
                    )
                )
                leads_created += 1
                lead_index += 1

        extra_leads = rng.randint(3, 8)
        for _ in range(extra_leads):
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            created_at = _random_dt(rng, since, now)
            db.add(
                Lead(
                    name=f"{first} {last}",
                    phone=_fake_phone(rng, lead_index),
                    email=f"client{lead_index}@example.ru" if rng.random() > 0.3 else None,
                    product_id=None,
                    product_name_snapshot=None,
                    comment_initial="Заявка без выбора товара — нужен подбор комплекта.",
                    is_read=rng.random() > 0.5,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            leads_created += 1
            lead_index += 1

        views_count = rng.randint(350, 520)
        for _ in range(views_count):
            db.add(
                PageView(
                    session_id=_fake_session(rng),
                    ip_hash=_fake_ip_hash(rng),
                    referrer=rng.choice(REFERRERS),
                    user_agent=rng.choice(USER_AGENTS),
                    created_at=_random_dt(rng, since, now),
                )
            )
            views_created += 1

        db.commit()

        return {
            "cleared": cleared,
            "products": len(products),
            "leads": leads_created,
            "clicks": clicks_created,
            "views": views_created,
        }
    finally:
        db.close()
