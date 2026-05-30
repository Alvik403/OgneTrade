import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.types import JSON

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class UserRole:
    SUPER_ADMIN = "super_admin"
    MANAGER = "manager"


class LeadStatus:
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=UserRole.MANAGER)
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    assigned_leads: Mapped[list["Lead"]] = relationship(back_populates="assignee")
    comments: Mapped[list["LeadComment"]] = relationship(back_populates="author")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    article: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_url: Mapped[str] = mapped_column(String(512), default="/static/images/products/placeholder.svg")
    price_from: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    long_description: Mapped[str] = mapped_column(Text, default="")
    specs: Mapped[dict | list] = mapped_column(JSON, default=list)
    volume_liters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    clicks: Mapped[list["CardClick"]] = relationship(back_populates="product")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products.id"), nullable=True)
    product_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=LeadStatus.NEW, index=True)
    sub_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    comment_initial: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee: Mapped["User | None"] = relationship(back_populates="assigned_leads")
    product: Mapped["Product | None"] = relationship()
    comments: Mapped[list["LeadComment"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    status_history: Mapped[list["LeadStatusHistory"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class LeadComment(Base):
    __tablename__ = "lead_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lead: Mapped["Lead"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")


class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    old_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32))
    old_sub_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_sub_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lead: Mapped["Lead"] = relationship(back_populates="status_history")


class PageView(Base):
    __tablename__ = "page_views"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    ip_hash: Mapped[str] = mapped_column(String(64))
    referrer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CardClick(Base):
    __tablename__ = "card_clicks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    product: Mapped["Product"] = relationship(back_populates="clicks")


class SiteSetting(Base):
    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    channel: Mapped[str] = mapped_column(String(32))
    recipient: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    from app.migrate import migrate_schema

    migrate_schema(engine)
