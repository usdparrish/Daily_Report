"""
Email presentation for Daily Capacity Forecast.

Enterprise rules:
- Rendering + delivery only
- No business logic
- No data access
"""

from typing import List

from radiology_reports.forecasting.capacity_models import DailyCapacityResult
from radiology_reports.utils.config import config
from radiology_reports.utils.email_sender import (
    EmailConfig,
    send_email,
)


def _build_email_body(result: DailyCapacityResult) -> str:
    lines = []

    lines.append(f"Daily Capacity Forecast — {result.date}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(
        f"Network Utilization: {result.network.utilization:.1%}"
    )
    lines.append(
        f"Scheduled Weighted Units: {result.network.total_weighted_units:,.1f}"
    )
    lines.append(
        f"Network Capacity: {result.network.total_capacity:,.1f}"
    )
    lines.append("")
    lines.append("Top 5 Locations by Utilization:")
    lines.append("-" * 40)

    top = sorted(
        result.locations,
        key=lambda x: x.utilization,
        reverse=True
    )[:5]

    for r in top:
        lines.append(
            f"{r.location:<25} "
            f"{r.utilization:.1%} "
            f"({r.status})"
        )

    lines.append("")
    lines.append("This is an automated report.")

    return "\n".join(lines)


def email_daily_capacity(
    results: List[DailyCapacityResult],
    recipients: List[str] | None = None,
) -> None:
    """
    Send Daily Capacity Forecast email(s).
    """

    email_cfg = EmailConfig(
        smtp_server=config.SMTP_SERVER,
        smtp_port=config.SMTP_PORT,
        sender_email=config.SENDER_EMAIL,
        default_recipients=",".join(
            recipients or config.DEFAULT_RECIPIENTS
        ),
    )

    for result in results:
        subject = f"Daily Capacity Forecast — {result.date}"
        body = _build_email_body(result)

        send_email(
            config=email_cfg,
            subject=subject,
            body=body,
            recipients=recipients or config.DEFAULT_RECIPIENTS,
        )
