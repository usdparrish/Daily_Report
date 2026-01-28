# src/radiology_reports/capacity_reporting/ops/renderers.py

from radiology_reports.capacity_reporting.ops.ops_capacity_models import (
    OpsDailyCapacityResult,
)


def render_ops_capacity_text(result: OpsDailyCapacityResult) -> str:
    """
    Render OPS Daily Capacity Execution report as plain text.

    Presentation-layer only:
    - No SQL
    - No email
    - No business logic
    """

    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("OPS DAILY RADIOLOGY CAPACITY – EXECUTION SUMMARY")
    lines.append("=" * 70)
    lines.append("")

    lines.append(f"Report DOS: {result.dos}")
    lines.append(f"Snapshot Date: {result.snapshot_date or 'N/A'}")
    lines.append(f"Total Active Sites: {result.total_active_sites}")
    lines.append("")

    # Scheduled (baseline)
    sched = result.scheduled
    lines.append("SCHEDULED BASELINE")
    lines.append("-" * 30)
    lines.append(f"Network Scheduled Weighted: {sched.network_weighted:,.2f}")
    lines.append(f"Network Capacity (90th):   {sched.network_capacity_90th:,.2f}")
    lines.append(f"Scheduled Utilization:     {sched.utilization_pct:.1f}%")
    lines.append(
        f"Sites OVER / AT / UNDER:   "
        f"{sched.sites_over} / {sched.sites_at} / {sched.sites_under}"
    )
    lines.append("")

    # Completed (actuals)
    comp = result.completed
    lines.append("COMPLETED ACTUALS")
    lines.append("-" * 30)
    lines.append(f"Network Completed Weighted: {comp.network_weighted:,.2f}")
    lines.append(f"Completed Utilization:      {comp.utilization_pct:.1f}%")
    lines.append("")

    # Execution delta
    delta = result.execution
    lines.append("EXECUTION DELTA (COMPLETED – SCHEDULED)")
    lines.append("-" * 45)
    lines.append(
        f"Delta Weighted: {delta.delta_weighted:,.2f} "
        f"({delta.delta_pct_points:+.1f} pts)"
    )
    lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)
