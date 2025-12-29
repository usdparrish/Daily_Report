"""
Capacity Domain Models

Enterprise rules:
- No logic
- No DB
- No formatting
- Pure data containers
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, List


# -------------------------------------------------
# Location-Level Result
# -------------------------------------------------

@dataclass(frozen=True)
class LocationCapacityResult:
    date: date
    location: str
    weighted_units: float
    volume: float
    capacity: float
    utilization: float
    status: str
    gap: Optional[float]


# -------------------------------------------------
# Network Summary
# -------------------------------------------------

@dataclass(frozen=True)
class NetworkCapacitySummary:
    total_weighted_units: float
    total_capacity: float
    utilization: float


# -------------------------------------------------
# Full Daily Result
# -------------------------------------------------

@dataclass(frozen=True)
class DailyCapacityResult:
    date: date
    locations: List[LocationCapacityResult]
    network: NetworkCapacitySummary
