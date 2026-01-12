# src/radiology_reports/reports/adapters/manager_location_yoy_adapter.py
from datetime import date
import calendar

from radiology_reports.data.workload import get_data_by_date, get_units_by_range
from radiology_reports.utils.businessdays import is_business_day, get_business_days
from radiology_reports.reports.models.location_report_yoy import (
    LocationReportYoY,
    PeriodMetricsYoY,
    ModalityMetricsYoY,
    Status,
)

def _get_prev_date(target_date: date) -> date:
    try:
        return target_date.replace(year=target_date.year - 1)
    except ValueError:
        return date(target_date.year - 1, target_date.month, target_date.day - 1)


def build_manager_location_yoy_reports(target_date: date) -> list[LocationReportYoY]:
    prev_date = _get_prev_date(target_date)

    df_daily_curr = get_data_by_date(target_date)
    df_daily_prev = get_data_by_date(prev_date)

    month_start_curr = target_date.replace(day=1)
    month_start_prev = prev_date.replace(day=1)

    df_mtd_curr = get_units_by_range(month_start_curr, target_date)
    df_mtd_prev = get_units_by_range(month_start_prev, prev_date)

    # 🔴 FIX: use MTD for location universe
    locations = sorted(df_mtd_curr["LocationName"].unique())

    month_end = date(
        target_date.year,
        target_date.month,
        calendar.monthrange(target_date.year, target_date.month)[1],
    )

    business_days_elapsed = get_business_days(month_start_curr, target_date)
    business_days_total = get_business_days(month_start_curr, month_end)

    reports: list[LocationReportYoY] = []

    for location in locations:
        # ---------- DAILY ----------
        daily_curr = df_daily_curr[df_daily_curr["LocationName"] == location]
        daily_prev = df_daily_prev[df_daily_prev["LocationName"] == location]

        completed = int(daily_curr["Unit"].sum())
        prev = int(daily_prev["Unit"].sum())

        if not is_business_day(target_date):
            daily_status = Status.INFO
            daily_delta = None
            daily_pct = None
        else:
            daily_delta = completed - prev
            daily_pct = (daily_delta / prev) if prev > 0 else None
            if daily_pct is None:
                daily_status = Status.INFO
            elif daily_pct >= 0.05:
                daily_status = Status.GREEN
            elif daily_pct <= -0.05:
                daily_status = Status.RED
            else:
                daily_status = Status.YELLOW

        daily_metrics = PeriodMetricsYoY(
            label="DAILY",
            is_business_day=is_business_day(target_date),
            business_days_elapsed=1 if is_business_day(target_date) else 0,
            business_days_total=None,
            prev_year_exams=prev,
            completed_exams=completed,
            delta=daily_delta,
            pct=daily_pct,
            status=daily_status,
            modalities=[],
        )

        # ---------- MTD ----------
        mtd_curr = df_mtd_curr[df_mtd_curr["LocationName"] == location]
        mtd_prev = df_mtd_prev[df_mtd_prev["LocationName"] == location]

        mtd_completed = int(mtd_curr["Unit"].sum())
        mtd_prev_total = int(mtd_prev["Unit"].sum())

        mtd_delta = mtd_completed - mtd_prev_total
        mtd_pct = (mtd_delta / mtd_prev_total) if mtd_prev_total > 0 else None

        if mtd_pct is None:
            mtd_status = Status.INFO
        elif mtd_pct >= 0.05:
            mtd_status = Status.GREEN
        elif mtd_pct <= -0.05:
            mtd_status = Status.RED
        else:
            mtd_status = Status.YELLOW

        mtd_metrics = PeriodMetricsYoY(
            label="MTD",
            is_business_day=True,
            business_days_elapsed=business_days_elapsed,
            business_days_total=business_days_total,
            prev_year_exams=mtd_prev_total,
            completed_exams=mtd_completed,
            delta=mtd_delta,
            pct=mtd_pct,
            status=mtd_status,
            modalities=[],
        )

        reports.append(
            LocationReportYoY(
                location_name=location,
                report_date=target_date,
                prev_year=prev_date.year,
                curr_year=target_date.year,
                daily=daily_metrics,
                mtd=mtd_metrics,
            )
        )

    return reports
