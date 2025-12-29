import argparse

from radiology_reports.forecasting.daily_capacity_usecase import (
    run_daily_capacity_forecast,
)
from radiology_reports.presentation.console import (
    render_daily_capacity,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Daily Weighted Capacity Forecast"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to run (default: 1)",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    results = run_daily_capacity_forecast(
        start_date=args.start_date,
        days=args.days,
    )

    for daily_result in results:
        render_daily_capacity(daily_result)


if __name__ == "__main__":
    main()
