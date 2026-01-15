import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from radiology_reports.utils.config import config
from radiology_reports.utils.logger import get_logger

log = get_logger(__name__)


def send_executive_capacity_email(
    report_text: str,
    recipients: List[str],
    audience: str = "scheduling",
) -> None:
    """
    Legacy-accurate executive HTML capacity email.

    IMPORTANT:
    - report_text MUST be the full console output
    - This function intentionally parses text (legacy behavior)
    - audience controls content depth ONLY
    """

    lines = report_text.splitlines()
    utilization = "N/A"
    over_count = "?"
    dos = "Unknown"
    snapshot_date = "Unknown"

    # Ops-only execution metrics
    scheduled_weighted = "N/A"
    completed_weighted = "N/A"
    execution_delta = "N/A"

    try:
        util_line = next((l for l in lines if "Network Utilization" in l), None)
        over_line = next((l for l in lines if "Sites OVER capacity" in l), None)
        dos_line = next((l for l in lines if "Scheduled For:" in l), None)
        snapshot_line = next(
            (l for l in lines if "Schedule Snapshot As Of:" in l), None
        )

        if util_line:
            utilization = util_line.split(":")[1].strip()
        if over_line:
            over_count = over_line.split(":")[1].strip().split()[0]
        if dos_line:
            dos = dos_line.split("Scheduled For:")[1].strip().split(" to ")[0]
        if snapshot_line:
            snapshot_date = snapshot_line.split(
                "Schedule Snapshot As Of:"
            )[1].strip()

        # Execution parsing (only text-based, no assumptions)
        for l in lines:
            if "Network Scheduled Weighted" in l:
                scheduled_weighted = l.split(":")[1].strip()
            elif "Network Completed Weighted" in l:
                completed_weighted = l.split(":")[1].strip()
            elif "Execution Delta" in l:
                execution_delta = l.split(":")[1].strip()

    except Exception as e:
        log.warning(f"Failed to parse metrics for email subject/body: {e}")

    subject = f"Capacity Alert – {over_count} Sites Over ({utilization})"

    # --------------------------------------------------
    # Apply color replacements to FULL report text
    # --------------------------------------------------
    colored_report = (
        report_text
        .replace(
            "OVER CAPACITY",
            '<span style="color:#e74c3c;font-weight:bold;">OVER CAPACITY</span>',
        )
        .replace(
            "AT CAPACITY",
            '<span style="color:#27ae60;font-weight:bold;">AT CAPACITY</span>',
        )
        .replace(
            "UNDER CAPACITY (GAP)",
            '<span style="color:#3498db;font-weight:bold;">UNDER CAPACITY (GAP)</span>',
        )
        .replace(
            "UNDER (GAP)",
            '<span style="color:#3498db;font-weight:bold;">UNDER (GAP)</span>',
        )
    )

    # --------------------------------------------------
    # Build HTML email
    # --------------------------------------------------
    html = f"""
    <html>
    <body style="font-family: Calibri, Arial, sans-serif; line-height:1.6; color:#333;">
      <h2 style="color:#2c3e50;">Daily Radiology Capacity Report</h2>
      <p><strong>DOS ({dos}) forecast:</strong></br>
      <strong>Schedule Snapshot As Of:</strong> {snapshot_date}</p>

      <div style="background:#f8f9fa;padding:15px;border-left:6px solid #3498db;margin:20px 0;">
        <p><strong>Network Utilization:</strong>
           <span style="font-size:1.2em;">{utilization}</span>
        </p>
        <p><strong>Status:</strong>
          <span style="color:#e74c3c;"><strong>{over_count} sites OVER CAPACITY</strong></span> •
          <span style="color:#27ae60;">AT CAPACITY</span> •
          <span style="color:#3498db;">UNDER</span>
        </p>
      </div>
    """

    # ==================================================
    # Scheduling audience — ORIGINAL BEHAVIOR (UNCHANGED)
    # ==================================================
    if audience == "scheduling":
        html += f"""
        <p style="color:#7f8c8d;font-size:90%;">
          <em>Full location and modality tables below for reference.</em>
        </p>

        <pre style="background:#f5f5f5;padding:15px;border:1px solid #eee;
                    font-size:10pt;font-family:Consolas;line-height:1.3;">
{colored_report}
        </pre>
        """

    # ==================================================
    # Ops audience — DOWNSIZED + EXECUTION SUMMARY
    # ==================================================
    else:
        html += f"""
        <div style="background:#fff3cd;padding:15px;border-left:6px solid #f39c12;margin:20px 0;">
          <p><strong>Execution Summary (Prior Day)</strong></p>
          <p>Scheduled Weighted: {scheduled_weighted}</p>
          <p>Completed Weighted: {completed_weighted}</p>
          <p>Execution Delta: {execution_delta}</p>
          <p style="color:#7f8c8d;font-size:90%;">
            Scheduling operated within capacity targets; variance reflects same-day operational factors.
          </p>
        </div>
        """

    html += """
      <hr style="border:0;border-top:1px solid #eee;margin:40px 0;">
      <p style="color:#95a5a6;font-size:85%;">
        Automated • Radiology Operations
      </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.sendmail(config.SENDER_EMAIL, recipients, msg.as_string())
        log.info(
            f"Executive capacity report sent to: {', '.join(recipients)} "
            f"(audience={audience})"
        )
    except Exception:
        log.error("Failed to send executive capacity email", exc_info=True)
        raise
