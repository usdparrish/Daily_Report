#!/usr/bin/env python3
"""
daily_capacity_executive_summary.py

Refactored to use rrc.data.workload, rrc.services.capacity, and rrc.services.executive_report.
Only necessary changes applied.
"""
import argparse
from datetime import date, timedelta

from utils.logger import get_logger
from rrc.data.workload import get_daily_completed_workload, get_scheduled_snapshot, get_capacity_by_location
from rrc.services.capacity import compute_capacity_summary
from rrc.services.executive_report import build_text_report

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily executive capacity summary (scheduled vs completed vs capacity)."
    )
    parser.add_argument(
        "--date",
        "-d",
        help="DOS in YYYY-MM-DD format. Defaults to yesterday.",
    )
    return parser.parse_args()

def resolve_date(arg):
    if arg:
        return date.fromisoformat(arg)
    return date.today() - timedelta(days=1)

def main():
    log = get_logger(__name__)
    log.info("=== Daily Capacity Executive Summary Started ===")

    args = parse_args()
    target_d = resolve_date(args.date)
    d_str = target_d.strftime("%Y-%m-%d")

    # Load datasets via the workload module
    completed_df = get_daily_completed_workload(d_str)
    scheduled_df = get_scheduled_snapshot(d_str)
    capacity_df = get_capacity_by_location()

    # Detect unknown modalities (where modality_weight is null)
    unknown_modalities = set()
    if not scheduled_df.empty:
        for _, r in scheduled_df.iterrows():
            if r.get('modality_weight') is None or (isinstance(r.get('modality_weight'), float) and r.get('modality_weight') == 0):
                unknown_modalities.add(r.get('modality') or '(NULL)')

    # Compute capacity summary using centralized logic
    summary_df = compute_capacity_summary(scheduled_df, completed_df, capacity_df)

    # Build executive text report
    report_text = build_text_report(summary_df, d_str)

    # Print report
    print(report_text)

    if unknown_modalities:
        log.warning("Unknown modalities found in SCHEDULED (weight missing): %s", ", ".join(sorted(unknown_modalities)))

    log.info("=== Daily Capacity Executive Summary Completed ===")

if __name__ == "__main__":
    main()
