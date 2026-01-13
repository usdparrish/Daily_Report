# src/radiology_reports/reports/adapters/manager_location_yoy_adapter.py

from datetime import date
import calendar

from radiology_reports.data.workload import (
    get_data_by_date,
    get_units_by_range,
    get_active_locations,
)

from radiology_reports.utils.businessdays import get_business_days
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
        # Feb 29 → Feb 28
        return date(target_date.year - 1, target_date.month, target_date.day - 1)


def build_manager_location_yoy_reports(target_date: date) -> list[LocationReportYoY]:
    prev_date = _get_prev_date(target_date)

    # Weekend flag — deterministic
    is_weekend = target_date.weekday() >= 5

    # Data pulls
    df_daily_curr = get_data_by_date(target_date)
    df_daily_prev = get_data_by_date(prev_date)

    month_start_curr = target_date.replace(day=1)
    month_start_prev = prev_date.replace(day=1)

    df_mtd_curr = get_units_by_range(month_start_curr, target_date)
    df_mtd_prev = get_units_by_range(month_start_prev, prev_date)

    # Authoritative enterprise locations
    locations = sorted(get_active_locations()["LocationName"].tolist())

    month_end = date(
        target_date.year,
        target_date.month,
        calendar.monthrange(target_date.year, target_date.month)[1],
    )

    business_days_elapsed = get_business_days(month_start_curr, target_date)
    business_days_total = get_business_days(month_start_curr, month_end)

    reports: list[LocationReportYoY] = []

    for location in locations:
        # =====================================================
        # DAILY (YoY)
        # =====================================================
        daily_curr = df_daily_curr[df_daily_curr["LocationName"] == location]
        daily_prev = df_daily_prev[df_daily_prev["LocationName"] == location]

        curr_by_mod = daily_curr.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        prev_by_mod = daily_prev.groupby("ProcedureCategory")["Unit"].sum().to_dict()

        daily_modalities: list[ModalityMetricsYoY] = []
        daily_completed_total = 0
        daily_prev_total = 0

        for modality in set(curr_by_mod) | set(prev_by_mod):
            completed = int(curr_by_mod.get(modality, 0))
            prev = int(prev_by_mod.get(modality, 0))

            daily_completed_total += completed
            daily_prev_total += prev

            # Saturday/Sunday → suppress variance
            if is_weekend:
                delta = None
                pct = None
                status = Status.INFO
            else:
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

            daily_modalities.append(
                ModalityMetricsYoY(
                    modality=modality,
                    prev_year_exams=prev,
                    completed_exams=completed,
                    delta=delta,
                    pct=pct,
                    status=status,
                )
            )

        if is_weekend:
            daily_delta = None
            daily_pct = None
            daily_status = Status.INFO
            daily_is_business_day = False
            daily_bdays_elapsed = 0
        else:
            daily_delta = daily_completed_total - daily_prev_total
            daily_pct = (
                daily_delta / daily_prev_total
                if daily_prev_total > 0
                else None
            )

            if daily_pct is None:
                daily_status = Status.INFO
            elif daily_pct >= 0.05:
                daily_status = Status.GREEN
            elif daily_pct <= -0.05:
                daily_status = Status.RED
            else:
                daily_status = Status.YELLOW

            daily_is_business_day = True
            daily_bdays_elapsed = 1

        daily_metrics = PeriodMetricsYoY(
            label="DAILY",
            is_business_day=daily_is_business_day,
            business_days_elapsed=daily_bdays_elapsed,
            business_days_total=None,
            prev_year_exams=daily_prev_total,
            completed_exams=daily_completed_total,
            delta=daily_delta,
            pct=daily_pct,
            status=daily_status,
            modalities=daily_modalities,
        )

        # =====================================================
        # MTD (YoY)
        # =====================================================
        mtd_curr = df_mtd_curr[df_mtd_curr["LocationName"] == location]
        mtd_prev = df_mtd_prev[df_mtd_prev["LocationName"] == location]

        curr_by_mod = mtd_curr.groupby("ProcedureCategory")["Unit"].sum().to_dict()
        prev_by_mod = mtd_prev.groupby("ProcedureCategory")["Unit"].sum().to_dict()

        mtd_modalities: list[ModalityMetricsYoY] = []
        mtd_completed_total = 0
        mtd_prev_total = 0

        for modality in set(curr_by_mod) | set(prev_by_mod):
            completed = int(curr_by_mod.get(modality, 0))
            prev = int(prev_by_mod.get(modality, 0))

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

            mtd_modalities.append(
                ModalityMetricsYoY(
                    modality=modality,
                    prev_year_exams=prev,
                    completed_exams=completed,
                    delta=delta,
                    pct=pct,
                    status=status,
                )
            )

        mtd_delta = mtd_completed_total - mtd_prev_total
        mtd_pct = (
            mtd_delta / mtd_prev_total
            if mtd_prev_total > 0
            else None
        )

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
            completed_exams=mtd_completed_total,
            delta=mtd_delta,
            pct=mtd_pct,
            status=mtd_status,
            modalities=mtd_modalities,
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
