# src/radiology_reports/pdf/chart_builder.py
"""
Chart Builder — Creates monthly volume bar chart
"""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt

from radiology_reports.pdf.styles import REPORT_TITLE


def build_monthly_chart(chart_data: Dict[str, Any]) -> Path | None:
    output_path = Path(__file__).parent.parent / "output"
    output_path.mkdir(parents=True, exist_ok=True)
    chart_path = output_path / "monthly_chart.png"

    this_daily = chart_data["this_year"]
    last_daily = chart_data["last_year"]
    month_name = chart_data["month_name"]

    if this_daily.empty and last_daily.empty:
        return None

    plt.figure(figsize=(11, 5))
    days = range(1, 32)
    this_vals = [this_daily.get(d, 0) for d in days]
    last_vals = [last_daily.get(d, 0) for d in days]

    plt.bar([d - 0.2 for d in days], this_vals, width=0.4, label=str(chart_data["this_year"]), color='#003087')
    plt.bar([d + 0.2 for d in days], last_vals, width=0.4, label=str(chart_data["last_year"]), color='#808080')

    plt.xlabel("Day of Month", fontsize=12)
    plt.ylabel("Total Units", fontsize=12)
    plt.title(f"Monthly Volume Comparison — {month_name}", fontsize=14)
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    plt.savefig(chart_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return chart_path