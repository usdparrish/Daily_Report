# src/radiology_reports/cli/manager_pdf.py

from datetime import date, timedelta
from pathlib import Path
import argparse
import sys

from radiology_reports.application.manager_daily_app import (
    ManagerDailyReportApplication,
)
from radiology_reports.utils.file_utils import cleanup_old_files  # New import for cleanup

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Manager Daily PDF Reports (historical, budget vs actual)."
    )

    parser.add_argument("--date", type=str)
    parser.add_argument(
        "--output",
        type=str,
        default="output/manager_reports",
    )
    parser.add_argument("--combined", action="store_true")
    parser.add_argument("--email", action="store_true")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old PDF files after generation.")

    return parser.parse_args()

def resolve_target_date(date_arg: str | None) -> date:
    if not date_arg:
        return date.today() - timedelta(days=1)
    return date.fromisoformat(date_arg)

def main() -> int:
    args = parse_args()

    try:
        app = ManagerDailyReportApplication()

        app.run(
            target_date=resolve_target_date(args.date),
            output_root=Path(args.output),
            combined=args.combined,
            email=args.email,
        )

        if args.cleanup:
            cleanup_old_files(args.output)  # Run cleanup if flag is set

        print("Manager PDF reports generated successfully.")
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())