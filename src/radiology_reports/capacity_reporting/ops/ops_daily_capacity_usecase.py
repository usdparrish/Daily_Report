from __future__ import annotations

from datetime import date

from radiology_reports.capacity_reporting.daily_capacity_usecase import (
    run_daily_capacity_report,
)

from radiology_reports.capacity_reporting.ops.ops_capacity_models import (
    OpsCompletedSummary,
    OpsDailyCapacityResult,
    OpsExecutionDelta,
    OpsScheduledSummary,
)


def _nz(v: float | None) -> float:
    """Null-safe numeric cast for optional floats in legacy summary."""
    return float(v) if v is not None else 0.0


def build_ops_daily_capacity(dos: date) -> OpsDailyCapacityResult:
    """
    OPS v1 Use Case (Execution-focused)

    Rules:
    - DOES NOT parse console/email text
    - DOES NOT recompute capacity/weights
    - Projects from the authoritative DailyCapacityResult.summary
    - Scheduling email behavior is not touched by this path
    """
    result = run_daily_capacity_report(dos)
    s = result.summary

    scheduled_weighted = float(s.network_scheduled_weighted)
    capacity_90th = float(s.network_capacity_90th)
    scheduled_util = float(s.network_utilization_pct)

    completed_weighted = _nz(s.network_completed_weighted)
    completed_util = _nz(s.network_completed_utilization_pct)

    delta_weighted = _nz(s.execution_delta_weighted)
    delta_pct_points = _nz(s.execution_delta_pct_points)

    scheduled = OpsScheduledSummary(
        network_weighted=scheduled_weighted,
        network_capacity_90th=capacity_90th,
        utilization_pct=scheduled_util,
        sites_over=int(s.sites_over),
        sites_at=int(s.sites_at),
        sites_under=int(s.sites_under),
    )

    completed = OpsCompletedSummary(
        network_weighted=completed_weighted,
        utilization_pct=completed_util,
    )

    execution = OpsExecutionDelta(
        delta_weighted=delta_weighted,
        delta_pct_points=delta_pct_points,
    )

    return OpsDailyCapacityResult(
        dos=dos,
        snapshot_date=result.snapshot_date,
        total_active_sites=int(s.total_active_sites),
        scheduled=scheduled,
        completed=completed,
        execution=execution,
    )
