"""
Console presentation for Daily Capacity Forecast.

Enterprise rules:
- Rendering only
- No business logic
- No data access
"""

from radiology_reports.forecasting.capacity_models import (
    DailyCapacityResult,
)


def render_daily_capacity(result: DailyCapacityResult) -> None:
    """
    Render Daily Capacity Forecast to console.
    """

    print("\nDaily Capacity Forecast")
    print("-" * 30)
    print(f"Date: {result.date}")
    print(f"Total Active Sites: {len(result.locations)}")

    print(
        f"Total Scheduled Weighted Units: "
        f"{result.network.total_weighted_units:,.1f}"
    )
    print(
        f"Total Network Capacity: "
        f"{result.network.total_capacity:,.1f}"
    )
    print(
        f"Network Utilization: "
        f"{result.network.utilization:.1%}"
    )

    print("\nTop 5 Locations by Utilization:")
    top_locations = sorted(
        result.locations,
        key=lambda x: x.utilization,
        reverse=True
    )[:5]

    for r in top_locations:
        print(
            f"{r.location:<25} "
            f"{r.utilization:.1%} "
            f"({r.status})"
        )

    print("\n")
