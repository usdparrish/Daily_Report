# src/radiology_reports/capacity_reporting/ops/cli.py

import argparse
from datetime import date

from radiology_reports.capacity_reporting.ops.ops_daily_capacity_usecase import (
    build_ops_daily_capacity,
)
from radiology_reports.utils.config import config
from radiology_reports.presentation.ops_email import send_ops_capacity_email


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

    # Normalize CLI input at the boundary (NOT a hack)
    dos = date.fromisoformat(args.dos)

    # Build OPS execution report (domain use case)
    body = build_ops_daily_capacity(dos=dos)

    # Always print (OPS requirement)
    print(body)

    # Optional email
    if args.email:
        send_ops_capacity_email(
            report_text=body,
            recipients=config.OPS_RECIPIENTS,
        )


if __name__ == "__main__":
    main()
