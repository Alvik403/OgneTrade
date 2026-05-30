import logging

import aiosmtplib
import httpx
from email.message import EmailMessage
from sqlalchemy.orm import Session

from app.database import Lead, NotificationLog, User, UserRole
from app.services.analytics import get_notification_settings

logger = logging.getLogger(__name__)


async def _log_notification(db: Session, channel: str, recipient: str, status: str, error: str | None, lead_id: str | None):
    db.add(
        NotificationLog(
            channel=channel,
            recipient=recipient,
            status=status,
            error=error,
            lead_id=lead_id,
        )
    )
    db.commit()


async def send_email(db: Session, to: str, subject: str, body: str, lead_id: str | None = None) -> bool:
    settings = get_notification_settings(db)
    if not settings.smtp_host or not settings.smtp_from:
        await _log_notification(db, "email", to, "skipped", "SMTP not configured", lead_id)
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
        )
        await _log_notification(db, "email", to, "sent", None, lead_id)
        return True
    except Exception as exc:
        logger.exception("Email send failed")
        await _log_notification(db, "email", to, "failed", str(exc), lead_id)
        return False


async def send_telegram(db: Session, text: str, lead_id: str | None = None) -> bool:
    settings = get_notification_settings(db)
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        await _log_notification(db, "telegram", settings.telegram_chat_id or "n/a", "skipped", "Telegram not configured", lead_id)
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"chat_id": settings.telegram_chat_id, "text": text, "parse_mode": "HTML"})
            resp.raise_for_status()
        await _log_notification(db, "telegram", settings.telegram_chat_id, "sent", None, lead_id)
        return True
    except Exception as exc:
        logger.exception("Telegram send failed")
        await _log_notification(db, "telegram", settings.telegram_chat_id, "failed", str(exc), lead_id)
        return False


def _lead_message(lead: Lead) -> str:
    product = lead.product_name_snapshot or "Не указан"
    return (
        f"Новая заявка!\n\n"
        f"Имя: {lead.name}\n"
        f"Телефон: {lead.phone}\n"
        f"Email: {lead.email or '—'}\n"
        f"Товар: {product}\n"
        f"Комментарий: {lead.comment_initial or '—'}"
    )


def _lead_message_html(lead: Lead) -> str:
    product = lead.product_name_snapshot or "Не указан"
    return (
        f"<b>Новая заявка!</b>\n"
        f"Имя: {lead.name}\n"
        f"Телефон: {lead.phone}\n"
        f"Email: {lead.email or '—'}\n"
        f"Товар: {product}\n"
        f"Комментарий: {lead.comment_initial or '—'}"
    )


async def notify_new_lead(db: Session, lead: Lead) -> None:
    body = _lead_message(lead)
    html = _lead_message_html(lead)

    managers = db.query(User).filter(User.is_active.is_(True)).all()
    for user in managers:
        if user.email:
            await send_email(db, user.email, "Новая заявка с сайта", body, lead.id)

    await send_telegram(db, html, lead.id)


async def send_test_notification(db: Session) -> dict:
    managers = db.query(User).filter(User.is_active.is_(True)).all()
    email_ok = False
    for user in managers[:1]:
        email_ok = await send_email(db, user.email, "Тест уведомления", "Проверка SMTP с сайта огнетушителей.", None)
    tg_ok = await send_telegram(db, "<b>Тест</b>\nУведомление Telegram работает.", None)
    return {"email": email_ok, "telegram": tg_ok}
