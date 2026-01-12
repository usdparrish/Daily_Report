# src/radiology_reports/reports/adapters/manager_location_adapter.py
from datetime import date
import pandas as pd
import calendar

from radiology_reports.data.workload import (
    get_data_by_date,
    get_budget_daily_volume,
    get_units_by_range,
    get_budget_mtd,
)

from radiology_reports.reports.models.location_report import (
    LocationReport,
    PeriodMetrics,
    ModalityMetrics,
    Status,
)

from radiology_reports.utils.businessdays import is_business_day, get_business_days


def build_manager_location_reports(target_date: date) -> list[LocationReport]:
    df_daily = get_data_by_date(target_date)

    month_start = target_date.replace(day=1)
    df_mtd = get_units_by_range(month_start, target_date)

    # 🔴 FIX: location universe must come from MTD, not daily
    locations = sorted(df_mtd["LocationName"].unique())

    if is_business_day(target_date):
        daily_budget_df = get_budget_daily_volume(target_date.year, target_date.month)
    else:
        daily_budget_df = pd.DataFrame(columns=["LocationName", "ProcedureCategory", "Unit"])

    month_end = date(
        target_date.year,
        target_date.month,
        calendar.monthrange(target_date.year, target_date.month)[1],
    )

    business_days_elapsed = get_business_days(month_start, target_date)
    business_days_total = get_business_days(month_start, month_end)

    mtd_budget_df = get_budget_mtd(
        year=target_date.year,
        month=target_date.month,
        businessdays=business_days_elapsed,
    )

    reports: list[LocationReport] = []

    for location in locations:
        # ---------- DAILY ----------
        daily_loc = df_daily[df_daily["LocationName"] == location]
        daily_budget_loc = daily_budget_df[daily_budget_df["LocationName"] == location]

        completed_by_modality = daily_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        budget_by_modality = daily_budget_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()

        daily_rows = []
        daily_completed_total = 0
        daily_budget_total = 0

        for modality in set(completed_by_modality) | set(budget_by_modality):
            completed = int(completed_by_modality.get(modality, 0))
            budget = budget_by_modality.get(modality)

            if completed == 0 and budget is None:
                continue

            daily_completed_total += completed

            if not is_business_day(target_date) or budget is None:
                delta = None
                status = Status.INFO
            else:
                budget = int(budget)
                daily_budget_total += budget
                delta = completed - budget
                status = Status.GREEN if delta >= 0 else Status.YELLOW if delta >= -5 else Status.RED

            daily_rows.append(
                ModalityMetrics(
                    modality=modality,
                    completed_exams=completed,
                    budget_exams=budget,
                    delta=delta,
                    status=status,
                )
            )

        if not is_business_day(target_date):
            daily_status = Status.INFO
            daily_budget_total = None
            daily_delta = None
        else:
            daily_delta = daily_completed_total - daily_budget_total
            daily_status = Status.GREEN if daily_delta >= 0 else Status.YELLOW if daily_delta >= -10 else Status.RED

        daily_metrics = PeriodMetrics(
            label="DAILY",
            is_business_day=is_business_day(target_date),
            business_days_elapsed=0,
            business_days_total=None,
            completed_exams=daily_completed_total,
            budget_exams=daily_budget_total,
            delta=daily_delta,
            status=daily_status,
            modalities=daily_rows,
        )

        # ---------- MTD ----------
        mtd_loc = df_mtd[df_mtd["LocationName"] == location]
        mtd_budget_loc = mtd_budget_df[mtd_budget_df["LocationName"] == location]

        completed_by_modality = mtd_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        budget_by_modality = mtd_budget_loc.groupby("ProcedureCategory")["Unit"].sum().to_dict()

        mtd_rows = []
        mtd_completed_total = 0
        mtd_budget_total = 0

        for modality in set(completed_by_modality) | set(budget_by_modality):
            completed = int(completed_by_modality.get(modality, 0))
            budget = budget_by_modality.get(modality)

            if completed == 0 and budget is None:
                continue

            mtd_completed_total += completed

            if budget is None:
                delta = None
                status = Status.INFO
            else:
                budget = int(budget)
                mtd_budget_total += budget
                delta = completed - budget
                status = Status.GREEN if delta >= 0 else Status.YELLOW if delta >= -10 else Status.RED

            mtd_rows.append(
                ModalityMetrics(
                    modality=modality,
                    completed_exams=completed,
                    budget_exams=budget,
                    delta=delta,
                    status=status,
                )
            )

        mtd_delta = mtd_completed_total - mtd_budget_total
        mtd_status = Status.GREEN if mtd_delta >= 0 else Status.YELLOW if mtd_delta >= -25 else Status.RED

        mtd_metrics = PeriodMetrics(
            label="MTD",
            is_business_day=True,
            business_days_elapsed=business_days_elapsed,
            business_days_total=business_days_total,
            completed_exams=mtd_completed_total,
            budget_exams=mtd_budget_total,
            delta=mtd_delta,
            status=mtd_status,
            modalities=mtd_rows,
        )

        reports.append(
            LocationReport(
                location_name=location,
                report_date=target_date,
                daily=daily_metrics,
                mtd=mtd_metrics,
            )
        )

    return reports
