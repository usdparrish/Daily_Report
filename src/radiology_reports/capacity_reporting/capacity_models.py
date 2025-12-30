from dataclasses import dataclass
from datetime import date
from typing import Optional, List, Tuple, Set


@dataclass(frozen=True)
class LocationCapacityResult:
    dos: date
    location: str
    exams: int
    weighted_units: float
    capacity_90th: Optional[float]
    pct_of_capacity: Optional[float]
    gap_units: Optional[float]
    status: str


@dataclass(frozen=True)
class ModalityCapacityResult:
    dos: date
    location: str
    modality: str
    exams: int
    weighted_units: float
    cap_mod: Optional[float]
    pct_of_capacity: Optional[float]
    status: str


@dataclass(frozen=True)
class NetworkCapacitySummary:
    report_date: date
    start_date: date
    end_date: date
    total_active_sites: int
    network_scheduled_weighted: float
    network_capacity_90th: float
    network_utilization_pct: float
    sites_over: int
    sites_at: int
    sites_under: int


@dataclass(frozen=True)
class DailyCapacityResult:
    """
    Despite name, this represents the same multi-day report as the original script:
    start_date -> end_date inclusive, containing location + modality tables.
    """
    summary: NetworkCapacitySummary
    locations: List[LocationCapacityResult]          # already sorted as original output expects
    modalities: List[ModalityCapacityResult]         # detail list
    unknown_modalities: Set[str]
