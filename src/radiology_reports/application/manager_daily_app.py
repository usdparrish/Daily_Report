from datetime import date
from pathlib import Path
from typing import Optional
import os

from radiology_reports.reports.pdf.manager_report_runner import (
    run_manager_pdf_report,
    run_manager_combined_pdf,
)
from radiology_reports.reports.adapters.manager_location_adapter import build_manager_location_reports
from radiology_reports.reports.manager_daily_email_body import build_manager_daily_email_body
from radiology_reports.utils.email_sender import EmailConfig, send_email

class ManagerDailyReportApplication:
    """
    Application-layer orchestration for Manager Daily Reports.
    Mirrors CLI logic EXACTLY.
    """

    def run(
        self,
        *,
        target_date: date,
        output_root: Path,
        combined: bool,
        email: bool,
    ) -> Optional[Path]:

        # 1. Always generate per-location PDFs
        run_manager_pdf_report(
            target_date=target_date,
            output_root=output_root,
        )

        # 2. Combined PDF (optional)
        combined_pdf: Optional[Path] = None
        if combined:
            combined_pdf = run_manager_combined_pdf(
                target_date=target_date,
                output_root=output_root,
            )

        # 3. Email (optional, same rules as CLI)
        if email:
            if not combined_pdf:
                raise RuntimeError("--email requires --combined")

            config = EmailConfig()
            if not config.default_recipients:
                raise RuntimeError("DEFAULT_RECIPIENTS not set in .env")

            recipients = [r.strip() for r in config.default_recipient.split(",")]

            # Fetch reports data for body calculations
            reports = build_manager_location_reports(target_date)

            subject = f"Radiology Regional - Daily Operations Report ({target_date.strftime('%b %d, %Y')})"
            body = build_manager_daily_email_body(reports, target_date)
            attachments = [combined_pdf]

            send_email(
                config=config,
                subject=subject,
                body=body,
                recipients=recipients,
                attachments=attachments,
            )

        return combined_pdf