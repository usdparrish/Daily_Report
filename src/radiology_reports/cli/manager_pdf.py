from datetime import date, timedelta
from pathlib import Path
import argparse
import sys
import os

from radiology_reports.reports.pdf.manager_report_runner import (
    run_manager_pdf_report,
    run_manager_combined_pdf,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Manager Daily PDF Reports (historical, budget vs actual)."
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Report date in YYYY-MM-DD format (defaults to yesterday).",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="output/manager_reports",
        help="Output directory for generated PDFs.",
    )

    parser.add_argument(
        "--combined",
        action="store_true",
        help="Generate combined (all locations) PDF.",
    )

    # NOTE: email flag will be wired after this is stable
    # parser.add_argument("--email", action="store_true")

    return parser.parse_args()


def resolve_target_date(date_arg: str | None) -> date:
    if not date_arg:
        return date.today() - timedelta(days=1)

    try:
        return date.fromisoformat(date_arg)
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format.")


def main() -> int:
    args = parse_args()

    try:
        target_date = resolve_target_date(args.date)
        output_root = Path(args.output)

        # Always generate per-location PDFs
        run_manager_pdf_report(
            target_date=target_date,
            output_root=output_root,
        )

        # Optionally generate combined PDF
        if args.combined:
            run_manager_combined_pdf(
                target_date=target_date,
                output_root=output_root,
            )

        print(
            f"Manager PDF reports generated successfully "
            f"for {target_date.isoformat()}."
        )
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
