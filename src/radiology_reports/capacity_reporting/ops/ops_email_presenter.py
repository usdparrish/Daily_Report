from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from typing import Iterable, List

from radiology_reports.capacity_reporting.ops.ops_capacity_models import (
    OpsDailyCapacityResult,
)
from radiology_reports.utils.config import config
from radiology_reports.utils.logger import get_logger

log = get_logger(__name__)


def render_ops_email(ops: OpsDailyCapacityResult) -> str:
    """
    Render OPS (Execution) email body.

    v1 intent:
    - short, human-readable
    - explicit scheduled vs completed semantics
    - includes capacity baseline
    - no tables
    """
    report_date = date.today().isoformat()
    dos = ops.dos.isoformat()
    snapshot = ops.snapshot_date.isoformat() if ops.snapshot_date else "Unknown"

    sch = ops.scheduled
    comp = ops.completed
    ex = ops.execution

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("DAILY RADIOLOGY CAPACITY – OPS (EXECUTION)")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Report Date: {report_date}")
    lines.append(f"DOS: {dos}")
    lines.append(f"Schedule Snapshot As Of: {snapshot}")
    lines.append(f"Total Active Sites: {ops.total_active_sites}")
    lines.append("")
    lines.append("--- SCHEDULED (PLAN) ---")
    lines.append(f"Network Scheduled Weighted: {sch.network_weighted:.2f}")
    lines.append(f"Network Capacity (90th):   {sch.network_capacity_90th:.2f}")
    lines.append(f"Scheduled Utilization:     {sch.utilization_pct:.1f}%")
    lines.append(
        f"Sites OVER / AT / UNDER:   {sch.sites_over} / {sch.sites_at} / {sch.sites_under}"
    )
    lines.append("")
    lines.append("--- COMPLETED (ACTUAL) ---")
    lines.append(f"Network Completed Weighted: {comp.network_weighted:.2f}")
    lines.append(f"Completed Utilization:      {comp.utilization_pct:.1f}%")
    lines.append("")
    lines.append("--- EXECUTION DELTA ---")
    lines.append(f"Completed - Scheduled: {ex.delta_weighted:.2f} weighted ({ex.delta_pct_points:.1f} pts)")
    
    lines.append("")
    lines.append("Automated • Radiology Operations")

    # Plain text output for deterministic golden testing
    return "\n".join(lines)


def send_ops_capacity_email(
    body_text: str,
    recipients: List[str],
    subject: str = "Daily Radiology Capacity – OPS (Execution)",
) -> None:
    """
    Send OPS email (plain text).

    This is intentionally separate from the legacy scheduling email sender,
    to preserve the original scheduling output contract.
    """
    if not recipients:
        raise ValueError("OPS recipients list is empty.")

    msg = MIMEMultipart("alternative")
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # plain text only for v1 (stable + readable)
    msg.attach(MIMEText(body_text, "plain"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.sendmail(config.SENDER_EMAIL, recipients, msg.as_string())
        log.info(f"OPS capacity report sent to: {', '.join(recipients)}")
    except Exception:
        log.error("Failed to send OPS capacity email", exc_info=True)
        raise


def _parse_recipients(value: str) -> List[str]:
    return [e.strip() for e in value.split(",") if e.strip()]
