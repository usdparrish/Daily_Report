"""
Capacity Domain Logic

Enterprise rules:
- Pure functions only
- No database access
- No printing
- No config
- No side effects
"""

from typing import Dict, List, Tuple
from radiology_reports.forecasting.capacity_models import (
    LocationCapacityResult,
    NetworkCapacitySummary,
)


# ----------------------------
# Aggregation
# ----------------------------

def aggregate_by_location_and_modality(rows) -> Tuple[Dict, Dict]:
    """
    Aggregate scheduled data by location and (location, modality).

    Logic preserved from daily_capacity_forecast.
    """
    loc_output = {}
    mod_output = {}

    for _, row in rows.iterrows():
        loc = row["location"]
        mod = row["modality"]
        weighted = row.get("weighted_units", 0) or 0
        volume = row.get("volume", 0) or 0

        if loc not in loc_output:
            loc_output[loc] = {"weighted": 0, "volume": 0}

        loc_output[loc]["weighted"] += weighted
        loc_output[loc]["volume"] += volume

        key = (loc, mod)
        if key not in mod_output:
            mod_output[key] = {"weighted": 0, "volume": 0}

        mod_output[key]["weighted"] += weighted
        mod_output[key]["volume"] += volume

    return loc_output, mod_output


# ----------------------------
# Capacity / Utilization
# ----------------------------

def calculate_utilization(weighted: float, capacity: float) -> float:
    """
    Calculate utilization ratio.
    """
    return weighted / capacity if capacity else 0.0


def classify_status(utilization: float) -> str:
    """
    Classify utilization status.

    Logic preserved:
    - OVER >= 100%
    - WARNING >= 90%
    - OK otherwise
    """
    if utilization >= 1.0:
        return "OVER"
    if utilization >= 0.9:
        return "WARNING"
    return "OK"


def calculate_gap(weighted: float, capacity: float):
    """
    Calculate remaining gap (only if under capacity).
    """
    return capacity - weighted if weighted < capacity else None


# ----------------------------
# Location Result Builder
# ----------------------------

def build_location_results(
    dos,
    loc_output: Dict,
    capacity_by_location: Dict,
):
    results = []

    for loc, vals in loc_output.items():
        weighted = vals["weighted"]
        volume = vals["volume"]
        capacity = capacity_by_location.get(loc, 0)

        utilization = calculate_utilization(weighted, capacity)
        status = classify_status(utilization)
        gap = calculate_gap(weighted, capacity)

        results.append(
            LocationCapacityResult(
                date=dos,
                location=loc,
                weighted_units=weighted,
                volume=volume,
                capacity=capacity,
                utilization=utilization,
                status=status,
                gap=gap,
            )
        )

    return results

# ----------------------------
# Network Summary
# ----------------------------

def calculate_network_summary(results):
    total_weighted = sum(r.weighted_units for r in results)
    total_capacity = sum(r.capacity for r in results)

    utilization = total_weighted / total_capacity if total_capacity else 0

    return NetworkCapacitySummary(
        total_weighted_units=total_weighted,
        total_capacity=total_capacity,
        utilization=utilization,
    )



def top_locations_by_utilization(results, limit: int = 5):
    return sorted(
        results, key=lambda x: x.utilization, reverse=True
    )[:limit]

