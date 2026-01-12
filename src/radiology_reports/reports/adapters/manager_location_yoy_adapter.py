# src/radiology_reports/reports/adapters/manager_location_yoy_adapter.py
from datetime import date
import pandas as pd
import calendar

from radiology_reports.data.workload import (
    get_data_by_date,
    get_units_by_range,
)
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
    except ValueError:  # Leap day
        return date(target_date.year - 1, target_date.month, target_date.day - 1)

def build_manager_location_yoy_reports(target_date: date) -> list[LocationReportYoY]:
    prev_date = _get_prev_date(target_date)
    prev_year = prev_date.year
    curr_year = target_date.year

    # Load current data
    df_daily_curr = get_data_by_date(target_date)
    month_start_curr = target_date.replace(day=1)
    df_mtd_curr = get_units_by_range(month_start_curr, target_date)

    # Load previous year data
    df_daily_prev = get_data_by_date(prev_date)
    month_start_prev = prev_date.replace(day=1)
    df_mtd_prev = get_units_by_range(month_start_prev, prev_date)

    locations = sorted(df_daily_curr["LocationName"].unique())
    reports: list[LocationReportYoY] = []

    month_end_curr = date(target_date.year, target_date.month, calendar.monthrange(target_date.year, target_date.month)[1])
    business_days_elapsed = get_business_days(month_start_curr, target_date)
    business_days_total = get_business_days(month_start_curr, month_end_curr)

    for location in locations:
        # ---------- DAILY ----------
        daily_curr_loc = df_daily_curr[df_daily_curr["LocationName"] == location]
        daily_prev_loc = df_daily_prev[df_daily_prev["LocationName"] == location]
        completed_by_modality = daily_curr_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        prev_by_modality = daily_prev_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        all_modalities = set(completed_by_modality) | set(prev_by_modality)
        daily_rows = []
        daily_completed_total = 0
        daily_prev_total = 0
        for modality in sorted(all_modalities):
            completed = int(completed_by_modality.get(modality, 0))
            prev = int(prev_by_modality.get(modality, 0))
            if completed == 0 and prev == 0:
                continue
            daily_completed_total += completed
            daily_prev_total += prev
            delta = completed - prev
            pct = (delta / prev) if prev > 0 else None
            if pct is None:
                status = Status.INFO
            elif pct >= 0.05:
                status = Status.GREEN
            elif pct <= -0.05:
                status = Status.RED
            else:
                status = Status.YELLOW
            daily_rows.append(
                ModalityMetricsYoY(
                    modality=modality,
                    prev_year_exams=prev,
                    completed_exams=completed,
                    delta=delta,
                    pct=pct * 100 if pct is not None else None,
                    status=status,
                )
            )
        daily_delta = daily_completed_total - daily_prev_total
        daily_pct = (daily_delta / daily_prev_total) if daily_prev_total > 0 else None
        daily_status = (
            Status.GREEN if daily_delta >= 0
            else Status.YELLOW if daily_delta >= -10
            else Status.RED
        ) if daily_pct is not None else Status.INFO
        daily_metrics = PeriodMetricsYoY(
            label="DAILY",
            is_business_day=is_business_day(target_date),
            business_days_elapsed=1 if is_business_day(target_date) else 0,
            business_days_total=None,
            prev_year_exams=daily_prev_total,
            completed_exams=daily_completed_total,
            delta=daily_delta,
            pct=daily_pct,
            status=daily_status,
            modalities=daily_rows,
        )

        # ---------- MTD ----------
        mtd_curr_loc = df_mtd_curr[df_mtd_curr["LocationName"] == location]
        mtd_prev_loc = df_mtd_prev[df_mtd_prev["LocationName"] == location]
        completed_by_modality = mtd_curr_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        prev_by_modality = mtd_prev_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        all_modalities = set(completed_by_modality) | set(prev_by_modality)
        mtd_rows = []
        mtd_completed_total = 0
        mtd_prev_total = 0
        for modality in sorted(all_modalities):
            completed = int(completed_by_modality.get(modality, 0))
            prev = int(prev_by_modality.get(modality, 0))
            if completed == 0 and prev == 0:
                continue
            mtd_completed_total += completed
            mtd_prev_total += prev
            delta = completed - prev
            pct = (delta / prev) if prev > 0 else None
            if pct is None:
                status = Status.INFO
            elif pct >= 0.05:
                status = Status.GREEN
            elif pct <= -0.05:
                status = Status.RED
            else:
                status = Status.YELLOW
            mtd_rows.append(
                ModalityMetricsYoY(
                    modality=modality,
                    prev_year_exams=prev,
                    completed_exams=completed,
                    delta=delta,
                    pct=pct * 100 if pct is not None else None,
                    status=status,
                )
            )
        mtd_delta = mtd_completed_total - mtd_prev_total
        mtd_pct = (mtd_delta / mtd_prev_total) if mtd_prev_total > 0 else None
        mtd_status = (
            Status.GREEN if mtd_delta >= 0
            else Status.YELLOW if mtd_delta >= -25
            else Status.RED
        ) if mtd_pct is not None else Status.INFO
        mtd_metrics = PeriodMetricsYoY(
            label="MTD",
            is_business_day=True,
            business_days_elapsed=business_days_elapsed,
            business_days_total=business_days_total,
            prev_year_exams=mtd_prev_total,
            completed_exams=mtd_completed_total,
            delta=mtd_delta,
            pct=mtd_pct,
            status=mtd_status,
            modalities=mtd_rows,
        )

        # ---------- LOCATION ----------
        reports.append(
            LocationReportYoY(
                location_name=location,
                report_date=target_date,
                prev_year=prev_year,
                curr_year=curr_year,
                daily=daily_metrics,
                mtd=mtd_metrics,
            )
        )
    return reports