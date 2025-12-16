#!/usr/bin/env python3
"""
capacity_check.py
Rewritten to use rrc.data.workload and rrc.services.capacity
Only necessary changes applied.
"""
import argparse
from datetime import date
import pandas as pd

from rrc.data.workload import get_daily_completed_workload, get_capacity_by_location, get_capacity_by_modality
from utils.logger import get_logger

def parse_args():
    p = argparse.ArgumentParser(description="Daily Capacity Model — Location + Modality Capacity Check")
    p.add_argument("--date", "-d", help="DOS YYYY-MM-DD", required=False)
    return p.parse_args()

def resolve_date(arg):
    return arg if arg else date.today().strftime("%Y-%m-%d")

def print_table(rows, headers):
    rows = list(rows)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
    def fmt(row):
        return "  ".join(str(v).ljust(widths[i]) for i, v in enumerate(row))
    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))

def main():
    log = get_logger(__name__)
    args = parse_args()
    target_date = resolve_date(args.date)

    # Load completed weighted workload
    completed_df = get_daily_completed_workload(target_date)
    if completed_df.empty:
        print("No completed workload data for", target_date)
        return

    # Location-level aggregation
    summary = completed_df.groupby("location").agg(
        total_exams=("volume", "sum"),
        total_weighted_units=("weighted_units", "sum")
    ).reset_index()

    cap_loc_df = get_capacity_by_location()
    capacity_loc = dict(zip(cap_loc_df['location'], cap_loc_df['capacity_weighted_90th']))

    loc_output = []
    for _, row in summary.iterrows():
        loc = row['location']
        exams = float(row['total_exams'])
        weighted = float(row['total_weighted_units'])
        cap = capacity_loc.get(loc)

        if cap:
            pct = weighted / cap
            gap_units = cap - weighted
            gap_est = round(gap_units / 1.5)
        else:
            pct = None
            gap_units = None
            gap_est = None

        loc_output.append((
            loc,
            round(exams, 1),
            round(weighted, 1),
            round(cap, 1) if cap else None,
            round(pct, 2) if pct else None,
            round(gap_units, 1) if gap_units else None,
            gap_est
        ))

    # Modality-level daily summary
    mod_summary = completed_df.groupby(["dos","location","modality"]).agg(
        total_exams=("volume","sum"),
        weighted_units=("weighted_units","sum")
    ).reset_index()

    mod_cap_df = get_capacity_by_modality()
    capacity_mod = { (r['location'], r['modality']): float(r['capacity_weighted_90th_modality']) for _, r in mod_cap_df.iterrows() }

    mod_output = []
    for _, row in mod_summary.iterrows():
        loc = row['location']
        mod = row['modality']
        exams = float(row['total_exams'])
        weighted = float(row['weighted_units'])
        cap = capacity_mod.get((loc, mod))

        if cap:
            pct = weighted / cap
            status = ("OVER" if pct > 1.05 else "AT" if 0.95 <= pct <= 1.05 else "UNDER (GAP)")
        else:
            pct = None
            status = "NO CAP"

        mod_output.append((
            row['dos'],
            loc,
            mod,
            round(exams,1),
            round(weighted,1),
            round(cap,1) if cap else None,
            round(pct,2) if pct else None,
            status
        ))

    # Print results
    print("\n==========================================")
    print(f" DAILY CAPACITY OVERVIEW — DOS {target_date}")
    print("==========================================\n")

    print_table(sorted(loc_output, key=lambda x: x[4] if x[4] else 0, reverse=True),
                headers=[
                    "location","exams","weighted_units","capacity_90th","%_of_capacity","gap_units","gap_estimated_exams"
                ])

    print("\n\n==========================================")
    print(f" MODALITY CAPACITY OVERVIEW — DOS {target_date}")
    print("==========================================\n")

    print_table(mod_output, headers=[
        "dos","location","modality","total_exams","weighted_units","capacity_90th","pct_of_capacity","status"
    ])

if __name__ == "__main__":
    main()
