# src/radiology_reports/reports/email/manager_daily_body_builder.py

from datetime import date
from typing import List

from radiology_reports.reports.models.location_report import LocationReport
from radiology_reports.reports.pdf.formatting import fmt_number, fmt_percent


def build_manager_daily_email_body(
    reports: List[LocationReport],
    report_date: date,
) -> str:
    """
    Builds the email body for the Manager Daily Operations Report.
    Aggregated across ALL locations.
    Pure function: no IO, no env, no SMTP.
    """

    if not reports:
        return (
            "Attached is the Daily Operations Report for Radiology Regional.\n\n"
            f"Reporting Date: {report_date.strftime('%B %d, %Y')}"
        )

    # -----------------------------
    # Aggregate DAILY metrics
    # -----------------------------
    daily_completed = sum(r.daily.completed_exams for r in reports)
    daily_budget = sum(r.daily.budget_exams or 0 for r in reports)
    daily_variance = daily_completed - daily_budget if daily_budget > 0 else None

    # -----------------------------
    # Aggregate MTD metrics
    # -----------------------------
    mtd_completed = sum(r.mtd.completed_exams for r in reports)
    mtd_budget = sum(r.mtd.budget_exams or 0 for r in reports)
    business_days_elapsed = reports[0].mtd.business_days_elapsed if reports else None
    business_days_total = reports[0].mtd.business_days_total if reports else None

    # -----------------------------
    # Derived metrics
    # -----------------------------
    mtd_daily_avg = (
        round(mtd_completed / business_days_elapsed)
        if business_days_elapsed
        else None
    )

    mtd_variance_abs = (
        mtd_completed - mtd_budget
        if mtd_budget > 0
        else None
    )

    mtd_variance_pct = (
        mtd_variance_abs / mtd_budget
        if mtd_variance_abs is not None and mtd_budget > 0
        else None
    )

    # -----------------------------
    # Build email body
    # -----------------------------
    lines = [
        "Attached is the Daily Operations Report for Radiology Regional.",
        "",
        f"Reporting Date: {report_date.strftime('%B %d, %Y')}",
        "",
        "Daily Summary:",
        f"• Daily Exams Completed: {fmt_number(daily_completed)}",
        f"• Daily Budgeted Exams: {fmt_number(daily_budget)}",
        f"• Daily Variance to Budget: {fmt_number(daily_variance)}" if daily_variance is not None else "",
        "",
        "Month-to-Date Summary:",
    ]

    if business_days_elapsed and business_days_total:
        lines.append(
            f"• Business Days: {business_days_elapsed} of {business_days_total}"
        )

    lines.append(f"• MTD Exams Completed: {fmt_number(mtd_completed)}")

    if mtd_daily_avg is not None:
        lines.append(
            f"• MTD Daily Average: {fmt_number(mtd_daily_avg)}"
        )

    if mtd_variance_abs is not None and mtd_variance_pct is not None:
        lines.append(
            f"• MTD Variance to Budget: "
            f"{fmt_percent(mtd_variance_pct)} "
            f"({fmt_number(mtd_variance_abs)})"
        )

    lines.extend(
        [
            "",
            "Please refer to the attached PDF for location and modality detail.",
        ]
    )

    return "\n".join(lines)