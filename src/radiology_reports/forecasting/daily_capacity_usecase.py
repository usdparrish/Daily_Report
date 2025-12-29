"""
Daily Capacity Forecast Use Case

Enterprise responsibility:
- Orchestrate the workflow
- Coordinate data access
- Return domain results
- NO presentation logic
"""

from datetime import date, datetime, timedelta
from typing import Optional, List

from radiology_reports.data.workload import get_scheduled_snapshot
from radiology_reports.data.capacity import (
    get_capacity_weighted_90th_by_location,
    get_capacity_weighted_90th_by_modality,
)
from radiology_reports.utils.logger import get_logger

from radiology_reports.forecasting.capacity_domain import (
    aggregate_by_location_and_modality,
    build_location_results,
    calculate_network_summary,
)
from radiology_reports.forecasting.capacity_models import (
    DailyCapacityResult,
)

logger = get_logger(__name__)


def _parse_start_date(start_date: Optional[str]) -> date:
    if start_date:
        return datetime.strptime(start_date, "%Y-%m-%d").date()
    return date.today()


def run_daily_capacity_forecast(
    start_date: Optional[str],
    days: int = 1,
) -> List[DailyCapacityResult]:
    """
    Run the Daily Capacity Forecast workflow.

    Returns:
        List[DailyCapacityResult]
    """

    start = _parse_start_date(start_date)

    logger.info(
        "Running Daily Capacity Forecast | start_date=%s | days=%s",
        start,
        days,
    )

    capacity_by_location = get_capacity_weighted_90th_by_location()
    capacity_by_modality = get_capacity_weighted_90th_by_modality()

    results: List[DailyCapacityResult] = []

    for i in range(days):
        dos = start + timedelta(days=i)

        logger.info("Processing DOS: %s", dos)

        df = get_scheduled_snapshot(dos)

        if df.empty:
            logger.warning("No scheduled data found for %s", dos)
            continue

        loc_output, mod_output = aggregate_by_location_and_modality(df)

        location_results = build_location_results(
            dos=dos,
            loc_output=loc_output,
            capacity_by_location=capacity_by_location,
        )

        network_summary = calculate_network_summary(location_results)

        results.append(
            DailyCapacityResult(
                date=dos,
                locations=location_results,
                network=network_summary,
            )
        )

    return results
