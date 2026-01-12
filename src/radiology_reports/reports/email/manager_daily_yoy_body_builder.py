# src/radiology_reports/reports/email/manager_daily_yoy_body_builder.py
from datetime import date
from typing import List

from radiology_reports.reports.models.location_report_yoy import LocationReportYoY
from radiology_reports.reports.pdf.formatting import fmt_number, fmt_percent

def build_manager_daily_yoy_email_body(
    reports: List[LocationReportYoY],
    report_date: date,
) -> str:
    if not reports:
        return (
            "Attached is the Daily Operations Report (YoY) for Radiology Regional.\n\n"
            f"Reporting Date: {report_date.strftime('%B %d, %Y')}"
        )

    # Aggregate DAILY metrics
    daily_completed = sum(r.daily.completed_exams for r in reports)
    daily_prev = sum(r.daily.prev_year_exams for r in reports)
    daily_variance_abs = daily_completed - daily_prev
    daily_variance_pct = (daily_variance_abs / daily_prev) if daily_prev > 0 else None

    # Aggregate MTD metrics
    mtd_completed = sum(r.mtd.completed_exams for r in reports)
    mtd_prev = sum(r.mtd.prev_year_exams for r in reports)
    business_days_elapsed = reports[0].mtd.business_days_elapsed if reports else None
    business_days_total = reports[0].mtd.business_days_total if reports else None

    mtd_daily_avg = round(mtd_completed / business_days_elapsed) if business_days_elapsed else None
    mtd_variance_abs = mtd_completed - mtd_prev
    mtd_variance_pct = (mtd_variance_abs / mtd_prev) if mtd_prev > 0 else None

    # Build body
    lines = [
        "Attached is the Daily Operations Report (YoY) for Radiology Regional.",
        "",
        f"Reporting Date: {report_date.strftime('%B %d, %Y')}",
        "",
        "Daily Summary:",
        f"• Daily Exams Completed: {fmt_number(daily_completed)}",
        f"• Previous Year Daily Exams: {fmt_number(daily_prev)}",
    ]
    if daily_variance_abs is not None and daily_variance_pct is not None:
        lines.append(
            f"• Daily Variance to Previous Year: {fmt_percent(daily_variance_pct)} ({fmt_number(daily_variance_abs)})"
        )

    lines.extend(["", "Month-to-Date Summary:"])
    if business_days_elapsed and business_days_total:
        lines.append(f"• Business Days: {business_days_elapsed} of {business_days_total}")
    lines.append(f"• MTD Exams Completed: {fmt_number(mtd_completed)}")
    if mtd_daily_avg is not None:
        lines.append(f"• MTD Daily Average: {fmt_number(mtd_daily_avg)}")
    if mtd_variance_abs is not None and mtd_variance_pct is not None:
        lines.append(
            f"• MTD Variance to Previous Year: {fmt_percent(mtd_variance_pct)} ({fmt_number(mtd_variance_abs)})"
        )

    lines.extend(["", "Please refer to the attached PDF for location and modality detail."])
    return "\n".join(lines)