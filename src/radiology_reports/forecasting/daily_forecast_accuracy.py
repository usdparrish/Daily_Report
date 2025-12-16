#!/usr/bin/env python3
"""
scripts/daily_forecast_accuracy.py
Compare yesterday's scheduled snapshot (inserted=dos) vs completed weighted units.
Refactored to use rrc.data.workload
"""
from datetime import date, timedelta
from collections import defaultdict
import io
import pandas as pd

from utils.logger import get_logger
from rrc.data.workload import get_daily_completed_workload, get_scheduled_snapshot

def format_table(rows, headers):
    output = io.StringIO()
    rows = list(rows)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))
    def fmt(r): return " ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers)))
    print(fmt(headers), file=output)
    print(" ".join("-" * w for w in widths), file=output)
    for row in rows:
        print(fmt(row), file=output)
    return output.getvalue()

def main():
    log = get_logger(__name__)
    log.info("=== Daily Forecast Accuracy Check Started ===")

    yesterday = date.today() - timedelta(days=1)
    y_str = yesterday.strftime("%Y-%m-%d")

    # Use workload module to get actuals and scheduled snapshot
    actual_df = get_daily_completed_workload(y_str)
    sched_df = get_scheduled_snapshot(y_str)

    # Aggregate by location
    actual = actual_df.groupby('location')['weighted_units'].sum().to_dict() if not actual_df.empty else {}
    sched = {}
    unknown_modalities = set()
    if not sched_df.empty:
        for _, r in sched_df.iterrows():
            loc = r['location']
            weight = r.get('modality_weight')
            w_units = r.get('weighted_units')
            if weight is None or pd.isna(weight):
                unknown_modalities.add(r.get('modality') or '(NULL)')
                w_units = 0.0
            else:
                w_units = float(w_units or 0.0)
            sched[loc] = sched.get(loc, 0.0) + w_units

    rows = []
    for loc in sorted(set(actual) | set(sched)):
        s = round(sched.get(loc, 0.0), 2)
        a = round(actual.get(loc, 0.0), 2)
        diff = round(a - s, 2)
        acc = round(a / s * 100, 1) if s > 0 else 0
        rows.append((loc, s, a, diff, f"{acc}%" if s > 0 else "N/A"))

    total_scheduled = sum(sched.values())
    total_actual = sum(actual.values())
    overall_accuracy = round(total_actual / total_scheduled * 100, 1) if total_scheduled > 0 else 0.0

    out = io.StringIO()
    print(f"YESTERDAY'S FORECAST ACCURACY — {y_str}", file=out)
    print("="*80, file=out)
    print(format_table(rows, ["Location", "Scheduled", "Actual", "Diff", "Accuracy"]), file=out)
    print(file=out)
    print(f"NETWORK: Scheduled {total_scheduled:.2f} | Actual {total_actual:.2f} | "
          f"Accuracy {overall_accuracy}%", file=out)

    if unknown_modalities:
        print("\nWARNING: Unknown modalities (no weight):", file=out)
        for m in sorted(unknown_modalities):
            print(" -", m, file=out)

    print(out.getvalue())
    log.info("=== Forecast Accuracy Report Completed ===")
    return out.getvalue()

if __name__ == "__main__":
    main()
