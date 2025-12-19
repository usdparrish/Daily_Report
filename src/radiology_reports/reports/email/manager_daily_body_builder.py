from datetime import date
from radiology_reports.reports.models.location_report import LocationReport
from radiology_reports.reports.pdf.formatting import fmt_number, fmt_percent

def build_manager_daily_email_body(
    reports: list[LocationReport],
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
    # Aggregate daily total volume
    daily_completed = sum(r.daily.completed_exams for r in reports)
    # Aggregate MTD metrics
    mtd_completed = 0
    mtd_budget = 0
    business_days_elapsed = None
    business_days_total = None
    for r in reports:
        mtd = r.mtd
        mtd_completed += mtd.completed_exams
        if mtd.budget_exams is not None:
            mtd_budget += mtd.budget_exams
        if business_days_elapsed is None:
            business_days_elapsed = mtd.business_days_elapsed
            business_days_total = mtd.business_days_total
    # Derived metrics
    mtd_daily_avg = (
        mtd_completed / business_days_elapsed
        if business_days_elapsed
        else None
    )
    variance_abs = (
        mtd_completed - mtd_budget
        if mtd_budget
        else None
    )
    variance_pct = (
        variance_abs / mtd_budget
        if variance_abs is not None and mtd_budget
        else None
    )
    # Build email body
    lines = [
        "Attached is the Daily Operations Report.",
        "",
        f"Reporting Date: {report_date.strftime('%B %d, %Y')}",
        "",
        f"• Daily Exams Completed: {fmt_number(daily_completed)}",
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
            f"• MTD Daily Average: {fmt_number(round(mtd_daily_avg))}"
        )
    if variance_abs is not None and variance_pct is not None:
        lines.append(
            f"• MTD Variance to Budget: "
            f"{fmt_percent(variance_pct)} "
            f"({fmt_number(variance_abs)})"
        )
    lines.extend(
        [
            "",
            "Please refer to the attached PDF for location and modality detail.",
        ]
    )
    return "\n".join(lines)