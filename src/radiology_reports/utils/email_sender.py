import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class EmailConfig(BaseSettings):
    """
    Configuration model for email settings, loaded from environment variables.
    Validates required fields and provides defaults where appropriate.
    """
    model_config = SettingsConfigDict(env_file='.env', env_ignore_empty=True, extra='ignore')

    smtp_server: str
    smtp_port: int = 25
    sender_email: str
    smtp_user: Optional[str] = None  # Optional if no authentication is needed
    smtp_password: Optional[str] = None  # Optional if no authentication is needed
    default_recipients: str  # Loaded from DEFAULT_RECIPIENTS in .env

def send_email(
    config: EmailConfig,
    subject: str,
    body: str,
    recipients: List[str],
    attachments: Optional[List[Path]] = None,
    html_body: Optional[str] = None,
) -> None:
    """
    Sends an email with the specified subject, body, recipients, optional attachments, and optional HTML body.

    :param config: Email configuration instance.
    :param subject: The subject of the email.
    :param body: The plain text body of the email (fallback if HTML not provided).
    :param recipients: List of recipient email addresses.
    :param attachments: Optional list of file paths to attach (PDFs by default).
    :param html_body: Optional HTML version of the body for richer formatting.
    :raises RuntimeError: If required configuration is missing.
    :raises smtplib.SMTPException: If an SMTP error occurs during sending.
    """
    if not config.smtp_server or not config.sender_email:
        raise RuntimeError("SMTP_SERVER or SENDER_EMAIL not configured.")

    msg = EmailMessage()
    msg["From"] = config.sender_email
    msg["To"] = ", ".join(recipient for recipient in recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    if html_body:
        msg.add_alternative(html_body, subtype='html')

    attachments = attachments or []
    for path in attachments:
        if not path.exists():
            logger.warning(f"Attachment not found: {path}")
            continue
        with open(path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=path.name,
            )

    try:
        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            if config.smtp_user and config.smtp_password:
                server.login(config.smtp_user, config.smtp_password)
            server.send_message(msg)
        logger.info("Email sent successfully to: %s", ", ".join(recipient for recipient in recipients))
    except smtplib.SMTPException as e:
        logger.error("SMTP error occurred: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error sending email: %s", e)
        raise