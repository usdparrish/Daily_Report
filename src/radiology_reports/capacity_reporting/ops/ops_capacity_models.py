from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class OpsScheduledSummary:
    network_weighted: float
    network_capacity_90th: float
    utilization_pct: float
    sites_over: int
    sites_at: int
    sites_under: int


@dataclass(frozen=True)
class OpsCompletedSummary:
    network_weighted: float
    utilization_pct: float


@dataclass(frozen=True)
class OpsExecutionDelta:
    delta_weighted: float
    delta_pct_points: float


@dataclass(frozen=True)
class OpsDailyCapacityResult:
    dos: date
    snapshot_date: date | None
    total_active_sites: int

    scheduled: OpsScheduledSummary
    completed: OpsCompletedSummary
    execution: OpsExecutionDelta
