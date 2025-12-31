from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Set, Optional


# ------------------------------------------------------------
# Location-level capacity result
# ------------------------------------------------------------
@dataclass
class LocationCapacityResult:
    dos: date
    location: str
    exams: int
    weighted_units: float
    capacity_90th: Optional[float]
    pct_of_capacity: Optional[float]
    gap_units: Optional[float]
    status: str


# ------------------------------------------------------------
# Modality-level capacity result
# ------------------------------------------------------------
@dataclass
class ModalityCapacityResult:
    dos: date
    location: str
    modality: str
    exams: int
    weighted_units: float
    cap_mod: Optional[float]
    pct_of_capacity: Optional[float]
    status: str


# ------------------------------------------------------------
# Network summary (exec-facing KPIs)
# ------------------------------------------------------------
@dataclass
class NetworkCapacitySummary:
    report_date: date
    start_date: date
    end_date: date
    total_active_sites: int

    # Scheduled vs capacity
    network_scheduled_weighted: float
    network_capacity_90th: float
    network_utilization_pct: float

    # Site counts
    sites_over: int
    sites_at: int
    sites_under: int

    # --------------------------------------------------
    # Phase 2A additions (network-level only)
    # --------------------------------------------------
    network_completed_weighted: Optional[float] = None
    network_completed_utilization_pct: Optional[float] = None
    execution_delta_weighted: Optional[float] = None
    execution_delta_pct_points: Optional[float] = None


# ------------------------------------------------------------
# Final report object (single DOS)
# ------------------------------------------------------------
@dataclass
class DailyCapacityResult:
    summary: NetworkCapacitySummary
    locations: List[LocationCapacityResult]
    modalities: List[ModalityCapacityResult]
    unknown_modalities: Set[str]

    # Metadata (not KPIs)
    snapshot_date: Optional[date] = None
