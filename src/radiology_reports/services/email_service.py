import smtplib
from email.message import EmailMessage
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()


def send_email(
    subject: str,
    body: str,
    recipients: list[str],
    attachments: list[Path] | None = None,
):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "25"))
    sender = os.getenv("SENDER_EMAIL")

    if not smtp_server or not sender:
        raise RuntimeError("SMTP_SERVER or SENDER_EMAIL not configured.")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    attachments = attachments or []
    for path in attachments:
        with open(path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=path.name,
            )

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.send_message(msg)
