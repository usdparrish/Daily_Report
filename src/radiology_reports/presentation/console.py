from __future__ import annotations

import io
from typing import Iterable, List, Sequence

from radiology_reports.forecasting.capacity_models import DailyCapacityResult


def _format_table(rows: Sequence[Sequence[object]], headers: List[str], max_rows: int | None = None) -> str:
    output = io.StringIO()
    rows = list(rows)

    if max_rows is not None and len(rows) > max_rows:
        shown = rows[:max_rows]
        omitted = len(rows) - max_rows
    else:
        shown = rows
        omitted = 0

    widths = [len(h) for h in headers]
    for row in shown:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))

    def fmt(r):
        return " ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers)))

    print(fmt(headers), file=output)
    print(" ".join("-" * w for w in widths), file=output)
    for row in shown:
        print(fmt(row), file=output)

    if omitted:
        print(f"... ({omitted} more rows omitted) ...", file=output)

    return output.getvalue()


def render_daily_capacity(result: DailyCapacityResult) -> None:
    s = result.summary

    out = io.StringIO()

    print("\n" + "=" * 80, file=out)
    print("EXECUTIVE SUMMARY - RADIOLOGY CAPACITY REPORT", file=out)
    print("=" * 80, file=out)
    print(f"Report Date: {s.report_date.isoformat()}", file=out)
    print(f"Scheduled For: {s.start_date.isoformat()} to {s.end_date.isoformat()}", file=out)
    print(f"Total Active Sites: {s.total_active_sites}", file=out)
    print(file=out)

    print(f"Network Scheduled Weighted: {s.network_scheduled_weighted:.2f}", file=out)
    print(f"Network Capacity (90th):   {s.network_capacity_90th:.2f}", file=out)
    print(f"Network Utilization:       {s.network_utilization_pct}%", file=out)
    print(file=out)

    print(f"Sites OVER capacity:  {s.sites_over}", file=out)
    print(f"Sites AT capacity:    {s.sites_at}", file=out)
    print(f"Sites UNDER capacity: {s.sites_under}", file=out)
    print(file=out)

    print("Top 5 Highest Utilization Sites:", file=out)
    top5 = sorted(result.locations, key=lambda r: (r.pct_of_capacity or 0.0), reverse=True)[:5]
    for r in top5:
        pct_str = f"{r.pct_of_capacity:.1%}" if r.pct_of_capacity is not None else "N/A"
        print(f"  • {r.location:<15} {r.weighted_units:>8.1f} weighted ({pct_str} of capacity) → {r.status}", file=out)

    print("\n" + "=" * 80 + "\n", file=out)

    print(f"SCHEDULED WEIGHTED VOLUME — {s.start_date.isoformat()} -> {s.end_date.isoformat()}", file=out)
    print("(Latest snapshot from v_Scheduled_Current; active locations only)\n", file=out)

    # Location rollup
    print("== Location Rollup ==\n", file=out)
    loc_rows = [
        (
            r.dos.isoformat(),
            r.location,
            r.exams,
            f"{r.weighted_units:.2f}",
            f"{r.capacity_90th:.2f}" if r.capacity_90th is not None else None,
            f"{r.pct_of_capacity:.3f}" if r.pct_of_capacity is not None else None,
            f"{r.gap_units:.2f}" if r.gap_units is not None else None,
            r.status,
        )
        for r in result.locations
    ]
    print(
        _format_table(
            loc_rows,
            ["dos", "location", "exams", "weighted_units", "capacity_90th", "pct_of_capacity", "gap_units", "status"],
            max_rows=200,
        ),
        file=out,
    )

    # Modality detail
    print("\n== Modality Detail ==\n", file=out)
    mod_rows = [
        (
            r.dos.isoformat(),
            r.location,
            r.modality,
            r.exams,
            f"{r.weighted_units:.2f}",
            f"{r.cap_mod:.2f}" if r.cap_mod is not None else None,
            f"{r.pct_of_capacity:.3f}" if r.pct_of_capacity is not None else None,
            r.status,
        )
        for r in result.modalities
    ]
    print(
        _format_table(
            mod_rows,
            ["dos", "location", "modality", "exams", "weighted_units", "cap_mod", "pct_of_capacity", "status"],
            max_rows=400,
        ),
        file=out,
    )

    if result.unknown_modalities:
        print("\nWARNING: Unknown modalities (missing weight):", file=out)
        for m in sorted(result.unknown_modalities):
            print(" -", repr(m), file=out)

    # Print final report
    print(out.getvalue(), end="")
