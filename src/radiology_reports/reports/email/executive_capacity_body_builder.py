from typing import List

from radiology_reports.capacity_reporting.capacity_models import DailyCapacityResult
from radiology_reports.utils.logger import get_logger

log = get_logger(__name__)


# ==========================================================
# OPS-ONLY: Guardrail Context (Approved Schedule)
# ==========================================================
def render_ops_guardrail_context(summary) -> str:
    """
    OPS-only guardrail context.
    Mirrors original scheduling language.
    Presentation only. No new logic.
    """

    return f"""
Guardrail Context (Approved Schedule)

Network Scheduled Weighted: {summary.network_scheduled_weighted:.2f}
Network Capacity (90th):   {summary.network_capacity_90th:.2f}
Network Utilization:       {summary.network_utilization_pct:.1f}%

Sites OVER capacity:  {summary.sites_over}
Sites AT capacity:    {summary.sites_at}
Sites UNDER capacity: {summary.sites_under}
""".strip()


# ==========================================================
# EXISTING: Execution Summary (Prior Day)
# ==========================================================
def render_execution_summary(summary) -> str:
    return f"""
Execution Summary (Prior Day)

Scheduled Weighted: {summary.network_scheduled_weighted:.2f}
Completed Weighted: {summary.network_completed_weighted:.2f}
Execution Delta: {summary.execution_delta_weighted:+.2f} weighted ({summary.execution_delta_pct_points:+.1f} pts)
""".strip()


# ==========================================================
# EXISTING: Build OPS Email Body
# ==========================================================
def build_executive_capacity_body(
    result: DailyCapacityResult,
    audience: str,
) -> str:
    """
    Build email body for capacity reporting.

    CRITICAL:
    - Scheduling output MUST remain unchanged
    - OPS output is additive only
    """

    summary = result.summary
    body_sections: List[str] = []

    # ------------------------------------------------------
    # EXISTING HEADER (UNCHANGED)
    # ------------------------------------------------------
    body_sections.append("Daily Radiology Capacity Report\n")
    body_sections.append(f"DOS ({summary.start_date}) forecast:\n")
    body_sections.append(f"Schedule Snapshot As Of: {result.snapshot_date}\n")

    # ------------------------------------------------------
    # EXISTING STATUS BLOCK (UNCHANGED)
    # ------------------------------------------------------
    body_sections.append(f"\nNetwork Utilization: {summary.network_utilization_pct:.1f}%\n")
    body_sections.append(
        f"Status: {summary.sites_over} sites OVER CAPACITY • AT CAPACITY • UNDER\n"
    )

    # ------------------------------------------------------
    # OPS-ONLY ADDITION (APPROVED)
    # ------------------------------------------------------
    if audience == "ops":
        body_sections.append("\n" + render_ops_guardrail_context(summary) + "\n")
        body_sections.append("\n" + render_execution_summary(summary) + "\n")

    # ------------------------------------------------------
    # EXISTING SCHEDULING DETAIL (UNCHANGED)
    # ------------------------------------------------------
    if audience != "ops":
        body_sections.append("\nFull location and modality tables below for reference.\n")
        body_sections.append(result.console_text)

    return "\n".join(body_sections)
