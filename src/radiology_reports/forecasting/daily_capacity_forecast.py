#!/usr/bin/env python3
"""
daily_capacity_forecast.py
Morning report: Tomorrow's scheduled volume vs capacity
Refactored to use rrc.data.workload and rrc.services.capacity modules.
Only necessary changes applied.
"""
import argparse
from collections import defaultdict
from datetime import date, timedelta, datetime
import sys
import io
import pandas as pd

from utils.logger import get_logger
from utils.config import DEFAULT_RECIPIENTS
from utils.email_handler import send_executive_capacity_report
from rrc.data.workload import get_scheduled_snapshot, get_capacity_by_location, get_capacity_by_modality

DEFAULT_WEIGHT = 999.0

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start-date", "-s", help="Start DOS (YYYY-MM-DD). Defaults to today.")
    p.add_argument("--days", "-n", type=int, default=30)
    p.add_argument("--send-email", action="store_true")
    p.add_argument("--recipients", type=str)
    return p.parse_args()

def format_table(rows, headers, max_rows=None):
    output = io.StringIO()
    rows = list(rows)
    if max_rows and len(rows) > max_rows:
        rows = rows[:max_rows]
        omitted = len(rows) - max_rows
    else:
        omitted = 0
    widths = [len(h) for h in headers]
    for row in rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))
    def fmt(r): return " ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers)))
    print(fmt(headers), file=output)
    print(" ".join("-" * w for w in widths), file=output)
    for row in rows:
        print(fmt(row), file=output)
    if omitted:
        print(f"... ({omitted} more rows omitted) ...", file=output)
    return output.getvalue()

def main():
    log = get_logger(__name__)
    log.info("=== Daily Capacity Forecast Started ===")

    args = parse_args()
    start = args.start_date or date.today().strftime("%Y-%m-%d")
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
    except Exception:
        log.error("Invalid --start-date format; expected YYYY-MM-DD")
        sys.exit(1)
    end_date = start_date + timedelta(days=args.days - 1)

    recipients = (
        [e.strip() for e in args.recipients.split(",") if e.strip()]
        if args.recipients
        else DEFAULT_RECIPIENTS
    )

    # Aggregate scheduled snapshot across date range using workload module
    scheduled_rows = []
    unknown_modalities = set()
    total_scheduled_weighted = 0.0
    loc_map = defaultdict(lambda: {"volume": 0.0, "weighted_units": 0.0})

    cur_date = start_date
    while cur_date <= end_date:
        dos = cur_date.strftime('%Y-%m-%d')
        df_sched = get_scheduled_snapshot(dos)
        # df_sched expected columns: location, modality, volume, modality_weight, weighted_units
        for _, r in df_sched.iterrows():
            loc = r['location']
            mod = r['modality']
            vol = float(r['volume'] or 0)
            weight = r.get('modality_weight')
            w_units = r.get('weighted_units')
            if weight is None or pd.isna(weight):
                unknown_modalities.add(mod or '(NULL)')
                # if missing weight, treat weighted as 0
                w_units = 0.0
            else:
                # ensure numeric
                try:
                    w_units = float(w_units or 0)
                except Exception:
                    w_units = 0.0
            loc_map[(dos, loc)]['volume'] += vol
            loc_map[(dos, loc)]['weighted_units'] += w_units
            total_scheduled_weighted += w_units
        cur_date = cur_date + timedelta(days=1)

    # Build loc_list
    loc_list = []
    for (dos, loc), vals in sorted(loc_map.items()):
        loc_list.append((dos, loc, int(vals['volume']), round(vals['weighted_units'], 2)))

    # Capacity lookup
    cap_loc_df = get_capacity_by_location()
    cap_loc = dict(zip(cap_loc_df['location'], cap_loc_df['capacity_weighted_90th']))
    total_capacity = sum(v for v in cap_loc.values() if v is not None)

    # Build loc_output similar to previous behavior
    loc_output = []
    for dos_iso, loc, vol, weighted in loc_list:
        cap = cap_loc.get(loc)
        pct = round(weighted / cap, 3) if cap and cap > 0 else None
        gap = round(cap - weighted, 2) if cap and weighted < cap else None
        status = "NO CAP" if cap is None else "UNKNOWN"
        if cap and cap > 0:
            if weighted > cap * 1.05:
                status = "OVER CAPACITY"
            elif weighted >= cap * 0.95:
                status = "AT CAPACITY"
            else:
                status = "UNDER CAPACITY (GAP)"
        loc_output.append((dos_iso, loc, vol, weighted, cap, pct, gap, status))

    loc_sorted = sorted(loc_output, key=lambda r: (r[0], r[5] or 0), reverse=True)

    # Modality capacities
    cap_mod_df = get_capacity_by_modality()
    cap_mod = { (row['location'], row['modality']): row['capacity_weighted_90th_modality'] for _, row in cap_mod_df.iterrows() }

    mod_output = []
    # We need detail_list — reconstruct from df_sched across date range
    # Re-run to collect detail_list
    detail_list = []
    cur_date = start_date
    while cur_date <= end_date:
        dos = cur_date.strftime('%Y-%m-%d')
        df_sched = get_scheduled_snapshot(dos)
        for _, r in df_sched.iterrows():
            mod = r['modality']
            loc = r['location']
            vol = int(r['volume'] or 0)
            weighted = float(r['weighted_units'] or 0)
            detail_list.append((dos, loc, mod, vol, weighted))
        cur_date = cur_date + timedelta(days=1)

    for dos_iso, loc, mod, vol, weighted in detail_list:
        capm = cap_mod.get((loc, mod))
        pct = round(weighted / capm, 3) if capm and capm > 0 else None
        status = "NO CAP" if capm is None else "UNKNOWN"
        if capm and capm > 0:
            if weighted > capm * 1.05:
                status = "OVER CAPACITY"
            elif weighted >= capm * 0.95:
                status = "AT CAPACITY"
            else:
                status = "UNDER (GAP)"
        mod_output.append((dos_iso, loc, mod, vol, weighted, capm, pct, status))

    out = io.StringIO()
    network_util = round(total_scheduled_weighted / total_capacity * 100, 1) if total_capacity > 0 else 0.0

    print("\n" + "="*80, file=out)
    print("EXECUTIVE SUMMARY - RADIOLOGY CAPACITY REPORT", file=out)
    print("="*80, file=out)
    print(f"Report Date: {date.today().isoformat()}", file=out)
    print(f"Scheduled For: {start_date.isoformat()} to {end_date.isoformat()}", file=out)
    print(f"Total Active Sites: {len(loc_output)}", file=out)
    print(file=out)
    print(f"Network Scheduled Weighted: {total_scheduled_weighted:.2f}", file=out)
    print(f"Network Capacity (90th):   {total_capacity:.2f}", file=out)
    print(f"Network Utilization:       {network_util}%", file=out)
    print(file=out)

    over_count = sum(1 for r in loc_output if r[7] == "OVER CAPACITY")
    at_count = sum(1 for r in loc_output if "AT CAPACITY" in r[7])
    under_count = len(loc_output) - over_count - at_count
    print(f"Sites OVER capacity:  {over_count}", file=out)
    print(f"Sites AT capacity:    {at_count}", file=out)
    print(f"Sites UNDER capacity: {under_count}", file=out)
    print(file=out)

    print("Top 5 Highest Utilization Sites:", file=out)
    top5 = sorted(loc_sorted, key=lambda r: r[5] or 0, reverse=True)[:5]
    for row in top5:
        pct_str = f"{row[5]:.1%}" if row[5] is not None else "N/A"
        print(f"  • {row[1]:<15} {row[3]:>8.1f} weighted ({pct_str} of capacity) → {row[7]}", file=out)
    print("\n" + "="*80 + "\n", file=out)

    print(f"SCHEDULED WEIGHTED VOLUME — {start_date.isoformat()} -> {end_date.isoformat()}", file=out)
    print("(Latest snapshot from v_Scheduled_Current; active locations only)\n", file=out)
    print("== Location Rollup ==\n", file=out)
    print(format_table(loc_sorted, ["dos","location","exams","weighted_units","capacity_90th","pct_of_capacity","gap_units","status"], max_rows=200), file=out)

    print("\n== Modality Detail ==\n", file=out)
    print(format_table(mod_output, ["dos","location","modality","exams","weighted_units","cap_mod","pct_of_capacity","status"], max_rows=400), file=out)

    if unknown_modalities:
        print("\nWARNING: Unknown modalities (weight=999.0):", file=out)
        for m in sorted(unknown_modalities): print(" -", repr(m), file=out)

    report = out.getvalue()
    print(report)
    if args.send_email:
        send_executive_capacity_report(report, recipients)

    log.info("=== Daily Capacity Forecast Completed Successfully ===")

if __name__ == "__main__":
    main()
