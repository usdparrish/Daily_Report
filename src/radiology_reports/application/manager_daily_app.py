from datetime import date
from pathlib import Path
from typing import Optional

from radiology_reports.data.workload import budget_exists_for_month

from radiology_reports.reports.pdf.manager_report_runner import (
    run_manager_pdf_report,
    run_manager_combined_pdf,
)
from radiology_reports.reports.pdf.manager_yoy_report_runner import (
    run_manager_pdf_yoy_report,
    run_manager_combined_yoy_pdf,
)

from radiology_reports.reports.adapters.manager_location_adapter import (
    build_manager_location_reports,
)
from radiology_reports.reports.adapters.manager_location_yoy_adapter import (
    build_manager_location_yoy_reports,
)

from radiology_reports.reports.email.manager_daily_body_builder import (
    build_manager_daily_email_body,
)
from radiology_reports.reports.email.manager_daily_yoy_body_builder import (
    build_manager_daily_yoy_email_body,
)

from radiology_reports.utils.email_sender import EmailConfig, send_email


class ManagerDailyReportApplication:
    """
    Application-layer orchestration for Manager Daily Reports.

    Routing logic:
    - If budget exists for month → Budget vs Actual
    - Else → YoY vs same day last year
    """

    def run(
        self,
        *,
        target_date: date,
        output_root: Path,
        combined: bool,
        email: bool,
    ) -> Optional[Path]:

        use_budget = budget_exists_for_month(
            target_date.year,
            target_date.month,
        )

        # -------------------------
        # PDF GENERATION
        # -------------------------
        if use_budget:
            run_manager_pdf_report(
                target_date=target_date,
                output_root=output_root,
            )
        else:
            run_manager_pdf_yoy_report(
                target_date=target_date,
                output_root=output_root,
            )

        combined_pdf: Optional[Path] = None
        if combined:
            combined_pdf = (
                run_manager_combined_pdf(
                    target_date=target_date,
                    output_root=output_root,
                )
                if use_budget
                else run_manager_combined_yoy_pdf(
                    target_date=target_date,
                    output_root=output_root,
                )
            )

        # -------------------------
        # EMAIL
        # -------------------------
        if email:
            if not combined_pdf:
                raise RuntimeError("--email requires --combined")

            config = EmailConfig()
            if not config.default_recipients:
                raise RuntimeError("DEFAULT_RECIPIENTS not set in .env")

            recipients = [
                r.strip()
                for r in config.default_recipients.split(",")
            ]

            if use_budget:
                reports = build_manager_location_reports(target_date)
                body = build_manager_daily_email_body(
                    reports,
                    target_date,
                )
                subject = (
                    f"Radiology Regional - Daily Operations Report "
                    f"({target_date.strftime('%b %d, %Y')})"
                )
            else:
                reports = build_manager_location_yoy_reports(target_date)
                body = build_manager_daily_yoy_email_body(
                    reports,
                    target_date,
                )
                subject = (
                    f"Radiology Regional - Daily Operations Report (YoY) "
                    f"({target_date.strftime('%b %d, %Y')})"
                )

            send_email(
                config=config,
                subject=subject,
                body=body,
                recipients=recipients,
                attachments=[combined_pdf],
            )

        return combined_pdf
