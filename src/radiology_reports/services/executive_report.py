# rrc/services/executive_report.py

"""
Executive summary report generator.
Produces formatted text content for capacity summary,
and can be used as input to a PDF generator.
"""

from datetime import date
from textwrap import indent


def build_text_report(df, dos: str) -> str:

    total_sched = df["scheduled_wu"].sum()
    total_comp = df["completed_wu"].sum()
    total_cap = df["capacity_wu"].sum()

    net_sched_pct = round(total_sched / total_cap * 100, 1) if total_cap > 0 else 0
    net_comp_pct = round(total_comp / total_cap * 100, 1) if total_cap > 0 else 0

    network_delta_sched = round(total_sched - total_comp, 2)
    network_delta_comp = round(total_comp - total_cap, 2)

    out = []

    out.append("=" * 80)
    out.append(f"EXECUTIVE CAPACITY SUMMARY — DOS {dos}")
    out.append("=" * 80)
    out.append("")

    out.append(f"Network Scheduled WU : {total_sched:,.2f}")
    out.append(f"Network Completed WU : {total_comp:,.2f}")
    out.append(f"Network Capacity WU  : {total_cap:,.2f}")
    out.append("")
    out.append(f"Scheduled % of Cap   : {net_sched_pct}%")
    out.append(f"Completed % of Cap   : {net_comp_pct}%")
    out.append(f"Δ Scheduled/Completed: {network_delta_sched}")
    out.append(f"Δ Completed/Cap      : {network_delta_comp}")
    out.append("")
    out.append("Per-Location Summary:")
    out.append(df.to_string(index=False))
    out.append("")
    out.append("=" * 80)

    return "\n".join(out)
