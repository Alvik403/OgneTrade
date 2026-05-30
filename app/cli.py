import argparse
import sys

from app.catalog_data import YAGEL_PRODUCTS
from app.database import (
    Product,
    SessionLocal,
    SiteSetting,
    User,
    UserRole,
    engine,
    init_db,
)
from app.migrate import migrate_schema
from app.services.analytics import DEFAULT_CONTACTS
from app.seed_demo import seed_demo_data
from app.services.auth import hash_password

OGNETRADE_CONTACTS = {
    "phone": "+7 (495) 123-45-67",
    "email": "info@ognetrade.ru",
    "address": "г. Москва, ognetrade.ru",
    "whatsapp": "",
    "telegram": "",
}

LEGACY_PRODUCT_TITLES = {"ОП-4", "ОП-5", "ОУ-3", "CO2-5", "ОП-8"}


def create_admin(email: str, password: str, full_name: str):
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists")
            return
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole.SUPER_ADMIN,
        )
        db.add(user)
        db.commit()
        print(f"Super admin created: {email}")
    finally:
        db.close()


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


def seed():
    init_db()
    migrate_schema(engine)

    db = SessionLocal()
    try:
        contacts_row = db.get(SiteSetting, "contacts")
        if not contacts_row:
            db.add(SiteSetting(key="contacts", value=OGNETRADE_CONTACTS))
        elif contacts_row.value == DEFAULT_CONTACTS:
            contacts_row.value = OGNETRADE_CONTACTS

        if db.query(User).count() == 0:
            db.add(
                User(
                    email="admin@example.ru",
                    password_hash=hash_password("admin12345"),
                    full_name="Администратор",
                    role=UserRole.SUPER_ADMIN,
                )
            )
            db.add(
                User(
                    email="manager@example.ru",
                    password_hash=hash_password("manager12345"),
                    full_name="Менеджер",
                    role=UserRole.MANAGER,
                )
            )

        _upsert_yagel_products(db)

        db.commit()
        print("Seed completed.")
        print("Admin: admin@example.ru / admin12345")
        print("Manager: manager@example.ru / manager12345")
    finally:
        db.close()


def seed_demo(clear: bool = True):
    result = seed_demo_data(clear=clear)
    if result.get("cleared"):
        print("Cleared previous demo data:")
        for key, count in result["cleared"].items():
            print(f"  {key}: {count}")
    print(
        "Demo data seeded: "
        f"{result['leads']} leads across {result['products']} products, "
        f"{result['clicks']} clicks, {result['views']} page views."
    )


def main():
    parser = argparse.ArgumentParser(description="Lids CLI")
    sub = parser.add_subparsers(dest="command")

    admin_parser = sub.add_parser("create-admin")
    admin_parser.add_argument("--email", required=True)
    admin_parser.add_argument("--password", required=True)
    admin_parser.add_argument("--name", default="Admin")

    sub.add_parser("seed")

    demo_parser = sub.add_parser("seed-demo", help="Fill DB with demo leads, clicks and page views")
    demo_parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not clear existing leads and analytics before seeding",
    )

    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.password, args.name)
    elif args.command == "seed":
        seed()
    elif args.command == "seed-demo":
        seed_demo(clear=not args.keep_existing)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
