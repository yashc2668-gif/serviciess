"""Email integration helpers."""

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_password_reset_otp_email(*, recipient_email: str, otp_code: str) -> None:
    logger.info(
        "auth.password_reset_otp_sent",
        extra={
            "event": "auth.password_reset_otp_sent",
            "recipient_email": recipient_email,
            "sender": settings.EMAIL_SENDER,
            "subject": settings.PASSWORD_RESET_EMAIL_SUBJECT,
            "otp_code": otp_code,
        },
    )
