from radiology_reports.utils.email_sender import send_email


OPS_EMAIL_SUBJECT = "Daily Radiology Capacity – OPS (Execution)"


def send_ops_capacity_email(
    report_text: str,
    recipients: list[str],
) -> None:
    """
    Send OPS Daily Radiology Capacity Execution email.
    Plain text for v1. HTML styling intentionally deferred.
    """
    if not recipients:
        raise ValueError("OPS_RECIPIENTS is empty; cannot send OPS email")

    send_email(
        subject=OPS_EMAIL_SUBJECT,
        body=report_text,
        recipients=recipients,
    )
