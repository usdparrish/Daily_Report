# src/radiology_reports/reports/adapters/manager_location_adapter.py

from datetime import date, datetime
from collections import defaultdict
import pandas as pd
import calendar

from radiology_reports.data.workload import (
    get_data_by_date,
    get_budget_daily_volume,
    get_monthly_units,
    get_budget_mtd
)

from radiology_reports.reports.models.location_report import (
    LocationReport,
    PeriodMetrics,
    ModalityMetrics,
    Status
)


def is_business_day(d: date) -> bool:
    # Monday = 0, Sunday = 6
    return d.weekday() < 5


def count_business_days(start: date, end: date) -> int:
    """Count Mon–Fri between start and end inclusive."""
    days = 0
    current = start
    while current <= end:
        if is_business_day(current):
            days += 1
        current = current.replace(day=current.day + 1)
    return days


def build_manager_location_reports(target_date: date) -> list[LocationReport]:
    """
    Adapter that converts existing workload + budget data
    into LocationReport objects for Manager PDFs.
    """

    # =========================
    # DAILY DATA
    # =========================
    df_daily = get_data_by_date(target_date)

    # Daily budget only applies on business days
    daily_budget_df = None
    if is_business_day(target_date):
        daily_budget_df = get_budget_daily_volume(
            year=target_date.year,
            month=target_date.month
        )

    # =========================
    # MTD DATA
    # =========================
    df_mtd = get_monthly_units(target_date.month, target_date.year)

    # Business days elapsed (MTD)
    month_start = target_date.replace(day=1)
    business_days_elapsed = count_business_days(month_start, target_date)

    mtd_budget_df = get_budget_mtd(
        year=target_date.year,
        month=target_date.month,
        businessdays=business_days_elapsed
    )

    # =========================
    # GROUP BY LOCATION
    # =========================
    locations = sorted(df_daily["LocationName"].unique())
    reports: list[LocationReport] = []

    for location in locations:

        # ---------- DAILY ----------
        daily_rows = []
        daily_completed_total = 0
        daily_budget_total = 0

        daily_loc = df_daily[df_daily["LocationName"] == location]

        if daily_budget_df is not None:
            daily_budget_loc = daily_budget_df[daily_budget_df["LocationName"] == location]
        else:
            daily_budget_loc = pd.DataFrame()

        modalities = sorted(daily_loc["ProcedureCategory"].unique())

        for modality in modalities:
            completed = int(
                daily_loc[daily_loc["ProcedureCategory"] == modality]["Unit"].sum()
            )
            daily_completed_total += completed

            if not is_business_day(target_date):
                budget = None
                delta = None
                status = Status.INFO
            else:
                budget = int(
                    daily_budget_loc[
                        daily_budget_loc["ProcedureCategory"] == modality
                    ]["Unit"].sum()
                )
                daily_budget_total += budget
                delta = completed - budget
                status = (
                    Status.GREEN if delta >= 0
                    else Status.YELLOW if delta >= -5
                    else Status.RED
                )

            daily_rows.append(
                ModalityMetrics(
                    modality=modality,
                    completed_exams=completed,
                    budget_exams=budget,
                    delta=delta,
                    status=status
                )
            )

        if not is_business_day(target_date):
            daily_status = Status.INFO
            daily_budget_total = None
            daily_delta = None
        else:
            daily_delta = daily_completed_total - daily_budget_total
            daily_status = (
                Status.GREEN if daily_delta >= 0
                else Status.YELLOW if daily_delta >= -10
                else Status.RED
            )

        daily_metrics = PeriodMetrics(
            label="DAILY",
            is_business_day=is_business_day(target_date),
            business_days_elapsed=0,
            completed_exams=daily_completed_total,
            budget_exams=daily_budget_total,
            delta=daily_delta,
            status=daily_status,
            modalities=daily_rows
        )

        # ---------- MTD ----------
        mtd_rows = []
        mtd_completed_total = 0
        mtd_budget_total = 0

        mtd_loc = df_mtd[df_mtd["LocationName"] == location]
        mtd_budget_loc = mtd_budget_df[mtd_budget_df["LocationName"] == location]

        modalities = sorted(mtd_loc["ProcedureCategory"].unique())

        for modality in modalities:
            completed = int(
                mtd_loc[mtd_loc["ProcedureCategory"] == modality]["Unit"].sum()
            )
            mtd_completed_total += completed

            budget = int(
                mtd_budget_loc[
                    mtd_budget_loc["ProcedureCategory"] == modality
                ]["Unit"].sum()
            )
            mtd_budget_total += budget

            delta = completed - budget
            status = (
                Status.GREEN if delta >= 0
                else Status.YELLOW if delta >= -10
                else Status.RED
            )

            mtd_rows.append(
                ModalityMetrics(
                    modality=modality,
                    completed_exams=completed,
                    budget_exams=budget,
                    delta=delta,
                    status=status
                )
            )

        mtd_delta = mtd_completed_total - mtd_budget_total
        mtd_status = (
            Status.GREEN if mtd_delta >= 0
            else Status.YELLOW if mtd_delta >= -25
            else Status.RED
        )

        mtd_metrics = PeriodMetrics(
            label="MTD",
            is_business_day=True,
            business_days_elapsed=business_days_elapsed,
            completed_exams=mtd_completed_total,
            budget_exams=mtd_budget_total,
            delta=mtd_delta,
            status=mtd_status,
            modalities=mtd_rows
        )

        # ---------- LOCATION REPORT ----------
        reports.append(
            LocationReport(
                location_name=location,
                report_date=target_date,
                daily=daily_metrics,
                mtd=mtd_metrics
            )
        )

    return reports
