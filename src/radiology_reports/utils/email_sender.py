# src/radiology_reports/utils/email_sender.py

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional, Union

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class EmailConfig(BaseSettings):
    """
    Configuration model for email settings, loaded from environment variables.
    Validates required fields and provides defaults where appropriate.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    smtp_server: str
    smtp_port: int = 25
    sender_email: str
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    default_recipients: str


def _extract_email_settings(config) -> dict:
    """
    Normalize email settings from either EmailConfig (pydantic)
    or utils.config.Config (global singleton).
    """
    # EmailConfig path (existing behavior)
    if isinstance(config, EmailConfig):
        return {
            "smtp_server": config.smtp_server,
            "smtp_port": config.smtp_port,
            "sender_email": config.sender_email,
            "smtp_user": config.smtp_user,
            "smtp_password": config.smtp_password,
        }

    # utils.config.Config path (OPS / scheduling)
    return {
        "smtp_server": config.SMTP_SERVER,
        "smtp_port": config.SMTP_PORT,
        "sender_email": config.SENDER_EMAIL,
        "smtp_user": None,
        "smtp_password": None,
    }


def send_email(
    *,
    config,
    subject: str,
    body: str,
    recipients: List[str],
    attachments: Optional[List[Path]] = None,
    html_body: Optional[str] = None,
) -> None:
    """
    Sends an email with the specified subject, body, recipients, optional attachments,
    and optional HTML body.

    Compatible with both EmailConfig and utils.config.Config.
    """
    settings = _extract_email_settings(config)

    if not settings["smtp_server"] or not settings["sender_email"]:
        raise RuntimeError("SMTP_SERVER or SENDER_EMAIL not configured.")

    if not recipients:
        raise RuntimeError("Recipient list is empty.")

    msg = EmailMessage()
    msg["From"] = settings["sender_email"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    attachments = attachments or []
    for path in attachments:
        if not path.exists():
            logger.warning("Attachment not found: %s", path)
            continue
        with open(path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=path.name,
            )

    try:
        with smtplib.SMTP(settings["smtp_server"], settings["smtp_port"]) as server:
            if settings["smtp_user"] and settings["smtp_password"]:
                server.login(settings["smtp_user"], settings["smtp_password"])
            server.send_message(msg)

        logger.info(
            "Email sent successfully to: %s",
            ", ".join(recipients),
        )

    except smtplib.SMTPException as e:
        logger.error("SMTP error occurred: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error sending email: %s", e)
        raise
