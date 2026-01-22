from io import StringIO
from typing import List

from radiology_reports.capacity_reporting.capacity_models import (
    DailyCapacityResult,
    LocationCapacityResult,
    ModalityCapacityResult,
)
from radiology_reports.utils.logger import get_logger

log = get_logger(__name__)


def render_daily_capacity(
    result: DailyCapacityResult,
    audience: str = "scheduling",
) -> str:
    """
    Render the Daily Capacity Utilization Report to console.

    CRITICAL:
    - Output format MUST remain stable for scheduling
    - Email renderer parses this text verbatim
    - audience controls depth ONLY
    """

    out = StringIO()

    # ==========================================================
    # Header
    # ==========================================================
    out.write("=" * 70 + "\n")
    out.write("EXECUTIVE SUMMARY - RADIOLOGY CAPACITY REPORT\n")
    out.write("=" * 70 + "\n\n")

    s = result.summary

    out.write(f"Report Date: {s.report_date}\n")
    out.write(f"Scheduled For: {s.start_date}\n")

    if result.snapshot_date:
        out.write(f"Schedule Snapshot As Of: {result.snapshot_date}\n")
    else:
        out.write("Schedule Snapshot As Of: Unknown\n")

    out.write(f"Total Active Sites: {s.total_active_sites}\n\n")

    # ==========================================================
    # Network Summary
    # ==========================================================
    out.write(f"Network Scheduled Weighted: {s.network_scheduled_weighted:.2f}\n")
    out.write(f"Network Capacity (90th):   {s.network_capacity_90th:.2f}\n")
    out.write(f"Network Utilization:       {s.network_utilization_pct}%\n")

    # ---------------------------
    # Completed metrics
    # ---------------------------
    if s.network_completed_weighted is not None:
        out.write(
            f"Network Completed Weighted: {s.network_completed_weighted:.2f}\n"
        )
        out.write(
            f"Network Completed Utilization: "
            f"{s.network_completed_utilization_pct}%\n"
        )
        out.write(
            f"Execution Delta (Completed - Scheduled): "
            f"{s.execution_delta_weighted:+.2f} weighted "
            f"({s.execution_delta_pct_points:+.1f} pts)\n"
        )
    else:
        out.write("Network Completed Utilization: N/A (future DOS)\n")

    out.write("\n")

    # ==========================================================
    # Capacity Status Counts
    # ==========================================================
    out.write(f"Sites OVER capacity:  {s.sites_over}\n")
    out.write(f"Sites AT capacity:    {s.sites_at}\n")
    out.write(f"Sites UNDER capacity: {s.sites_under}\n\n")

    # ==========================================================
    # Top 5 Highest Utilization Sites
    # ==========================================================
    out.write("Top 5 Highest Utilization Sites:\n")

    top5 = sorted(
        result.locations,
        key=lambda r: (r.pct_of_capacity or 0.0),
        reverse=True,
    )[:5]

    if not top5:
        out.write(" • No utilization data available\n")
    else:
        for r in top5:
            pct = (
                f"{r.pct_of_capacity * 100:.1f}%"
                if r.pct_of_capacity is not None
                else "N/A"
            )

            out.write(
                f" • {r.location:<12} "
                f"{r.weighted_units:.1f} weighted "
                f"({pct} of capacity) -> {r.status}\n"
            )

    out.write("\n")

    # ==========================================================
    # Scheduling audience ONLY — detailed sections
    # ==========================================================
    if audience == "scheduling":

        # --------------------------
        # Full Location Rollup
        # --------------------------
        out.write("-" * 70 + "\n")
        out.write("FULL LOCATION CAPACITY DETAIL\n")
        out.write("-" * 70 + "\n")

        out.write(
            f"{'DOS':<12}"
            f"{'Location':<16}"
            f"{'Exams':>8}"
            f"{'Weighted':>12}"
            f"{'Capacity':>12}"
            f"{'%Util':>10}"
            f"{'Gap':>10}"
            f"{'Status':>20}\n"
        )

        for r in result.locations:
            pct = (
                f"{r.pct_of_capacity * 100:.1f}%"
                if r.pct_of_capacity is not None
                else "N/A"
            )
            gap = f"{r.gap_units:.1f}" if r.gap_units is not None else "N/A"
            cap = f"{r.capacity_90th:.1f}" if r.capacity_90th is not None else "N/A"

            out.write(
                f"{r.dos:%Y-%m-%d}  "
                f"{r.location:<16}"
                f"{r.exams:>8}"
                f"{r.weighted_units:>12.1f}"
                f"{cap:>12}"
                f"{pct:>10}"
                f"{gap:>10}"
                f"{r.status:>20}\n"
            )

        out.write("\n")

        # --------------------------
        # Full Modality Detail
        # --------------------------
        out.write("-" * 70 + "\n")
        out.write("FULL MODALITY CAPACITY DETAIL\n")
        out.write("-" * 70 + "\n")

        out.write(
            f"{'DOS':<12}"
            f"{'Location':<16}"
            f"{'Modality':<12}"
            f"{'Exams':>8}"
            f"{'Weighted':>12}"
            f"{'Capacity':>12}"
            f"{'%Util':>10}"
            f"{'Status':>18}\n"
        )

        for r in result.modalities:
            pct = (
                f"{r.pct_of_capacity * 100:.1f}%"
                if r.pct_of_capacity is not None
                else "N/A"
            )
            cap = f"{r.cap_mod:.1f}" if r.cap_mod is not None else "N/A"

            out.write(
                f"{r.dos:%Y-%m-%d}  "
                f"{r.location:<16}"
                f"{r.modality:<12}"
                f"{r.exams:>8}"
                f"{r.weighted_units:>12.1f}"
                f"{cap:>12}"
                f"{pct:>10}"
                f"{r.status:>18}\n"
            )

        # --------------------------
        # Unknown Modality Warning
        # --------------------------
        if result.unknown_modalities:
            out.write("\n")
            out.write("WARNING: Unknown modalities detected (missing weights):\n")
            for m in sorted(result.unknown_modalities):
                out.write(f" - {m}\n")

        out.write("\n")

    out.write("=" * 70 + "\n")

    report_text = out.getvalue()
    print(report_text, end="")

    return report_text
