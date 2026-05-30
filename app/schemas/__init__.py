import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


PHONE_PATTERN = re.compile(r"^(\+7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$")


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    return f"+{digits}" if digits else value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str = "manager"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    title: str
    article: str | None = None
    image_url: str = "/static/images/products/placeholder.svg"
    price_from: float = 0
    description: str = ""
    long_description: str = ""
    specs: list[dict[str, str]] = Field(default_factory=list)
    volume_liters: int | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    title: str | None = None
    article: str | None = None
    image_url: str | None = None
    price_from: float | None = None
    description: str | None = None
    long_description: str | None = None
    specs: list[dict[str, str]] | None = None
    volume_liters: int | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: str
    title: str
    article: str | None = None
    image_url: str
    price_from: float
    description: str
    long_description: str = ""
    specs: list[dict[str, str]] = Field(default_factory=list)
    volume_liters: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class LeadCreatePublic(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone: str
    email: EmailStr | None = None
    product_id: str | None = None
    product_name: str | None = None
    comment: str | None = None
    website: str | None = None  # honeypot

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE_PATTERN.match(value.strip()):
            raise ValueError("Некорректный номер телефона")
        return normalize_phone(value)


class LeadUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    status: str | None = None
    sub_status: str | None = None
    amount: float | None = None
    assigned_to: str | None = None
    product_name_snapshot: str | None = None
    is_read: bool | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not PHONE_PATTERN.match(value.strip()):
            raise ValueError("Некорректный номер телефона")
        return normalize_phone(value)


class LeadStatusUpdate(BaseModel):
    status: str
    sub_status: str | None = None


class CommentCreate(BaseModel):
    text: str = Field(min_length=1)


class CommentResponse(BaseModel):
    id: str
    text: str
    author_name: str
    created_at: datetime


class LeadResponse(BaseModel):
    id: str
    name: str
    phone: str
    email: str | None
    product_id: str | None
    product_name_snapshot: str | None
    status: str
    sub_status: str | None
    amount: float | None
    assigned_to: str | None
    assignee_name: str | None = None
    comment_initial: str | None
    is_read: bool
    created_at: datetime
    updated_at: datetime
    comments: list[CommentResponse] = []


class TrackClickRequest(BaseModel):
    product_id: str


class ContactsSettings(BaseModel):
    phone: str = "+7 (495) 123-45-67"
    email: str = "info@ognetrade.ru"
    address: str = "г. Москва, ognetrade.ru"
    whatsapp: str = ""
    telegram: str = ""


class NotificationSettings(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


class SiteSettingsUpdate(BaseModel):
    contacts: ContactsSettings | None = None
    notifications: NotificationSettings | None = None


class AnalyticsOverview(BaseModel):
    views_today: int
    leads_today: int
    clicks_today: int
    conversion_rate: float
    new_leads_count: int
    top_products: list[dict[str, Any]]
