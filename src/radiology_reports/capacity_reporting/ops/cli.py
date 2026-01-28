# src/radiology_reports/capacity_reporting/ops/cli.py

import argparse
from datetime import date

from radiology_reports.capacity_reporting.ops.ops_daily_capacity_usecase import (
    build_ops_daily_capacity,
)
from radiology_reports.capacity_reporting.ops.renderers import (
    render_ops_capacity_text,
)
from radiology_reports.presentation.ops_email import send_ops_capacity_email
from radiology_reports.utils.config import config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OPS Daily Radiology Capacity Execution Report"
    )
    parser.add_argument(
        "--dos",
        required=True,
        help="Date of Service (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send OPS execution email",
    )

    args = parser.parse_args()

    # Normalize input at boundary
    dos = date.fromisoformat(args.dos)

    # Domain use case
    result = build_ops_daily_capacity(dos=dos)

    # Presentation layer
    body = render_ops_capacity_text(result)

    # Always print
    print(body)

    # Optional email
    if args.email:
        send_ops_capacity_email(
            report_text=body,
            recipients=config.OPS_RECIPIENTS,
        )


if __name__ == "__main__":
    main()
