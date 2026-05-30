"""Ensure schema columns exist on older databases."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _add_columns(engine: Engine, table: str, additions: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for name, col_type in additions.items():
            if name in existing:
                continue
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {col_type}"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}"))


def migrate_product_columns(engine: Engine) -> None:
    dialect = engine.dialect.name
    _add_columns(
        engine,
        "products",
        {
            "article": "VARCHAR(64)",
            "long_description": "TEXT",
            "specs": "JSON" if dialect == "postgresql" else "TEXT",
            "volume_liters": "INTEGER",
        },
    )


def migrate_lead_columns(engine: Engine) -> None:
    dialect = engine.dialect.name
    _add_columns(
        engine,
        "leads",
        {
            "is_read": "BOOLEAN DEFAULT FALSE" if dialect == "postgresql" else "INTEGER DEFAULT 0",
        },
    )
    inspector = inspect(engine)
    if "leads" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("leads")}
    if "is_read" not in existing:
        return
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("UPDATE leads SET is_read = FALSE WHERE is_read IS NULL"))
        else:
            conn.execute(text("UPDATE leads SET is_read = 0 WHERE is_read IS NULL"))


def migrate_schema(engine: Engine) -> None:
    migrate_product_columns(engine)
    migrate_lead_columns(engine)
