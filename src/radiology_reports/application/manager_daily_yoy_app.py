# src/radiology_reports/application/manager_daily_yoy_app.py
from datetime import date
from pathlib import Path
from typing import Optional
import os

from radiology_reports.reports.pdf.manager_yoy_report_runner import (
    run_manager_pdf_yoy_report,
    run_manager_combined_yoy_pdf,
)
from radiology_reports.reports.adapters.manager_location_yoy_adapter import build_manager_location_yoy_reports
from radiology_reports.reports.email.manager_daily_yoy_body_builder import build_manager_daily_yoy_email_body
from radiology_reports.utils.email_sender import EmailConfig, send_email

class ManagerDailyYoYReportApplication:
    def run(
        self,
        *,
        target_date: date,
        output_root: Path,
        combined: bool,
        email: bool,
    ) -> Optional[Path]:

        # Generate per-location PDFs
        run_manager_pdf_yoy_report(
            target_date=target_date,
            output_root=output_root,
        )

        # Combined PDF (optional)
        combined_pdf: Optional[Path] = None
        if combined:
            combined_pdf = run_manager_combined_yoy_pdf(
                target_date=target_date,
                output_root=output_root,
            )

        # Email (optional)
        if email:
            if not combined_pdf:
                raise RuntimeError("--email requires --combined")

            config = EmailConfig()
            if not config.default_recipient:
                raise RuntimeError("DEFAULT_RECIPIENTS not set in .env")

            recipients = [r.strip() for r in config.default_recipient.split(",")]

            # Fetch reports for body
            reports = build_manager_location_yoy_reports(target_date)

            subject = f"Radiology Regional - Daily Operations Report YoY ({target_date.strftime('%b %d, %Y')})"
            body = build_manager_daily_yoy_email_body(reports, target_date)
            attachments = [combined_pdf]

            send_email(
                config=config,
                subject=subject,
                body=body,
                recipients=recipients,
                attachments=attachments,
            )

        return combined_pdf