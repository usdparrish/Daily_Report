from __future__ import annotations

import argparse
import os
from datetime import date, datetime

from radiology_reports.capacity_reporting.ops.ops_daily_capacity_usecase import (
    build_ops_daily_capacity,
)
from radiology_reports.capacity_reporting.ops.ops_email_presenter import (
    render_ops_email,
    send_ops_capacity_email,
    _parse_recipients,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Daily Radiology Capacity – OPS (Execution)"
    )

    parser.add_argument(
        "--dos",
        type=str,
        required=True,
        help="Day of Service (YYYY-MM-DD). Required for OPS execution reporting.",
    )

    parser.add_argument(
        "--email",
        action="store_true",
        help="Send OPS execution email (requires recipients).",
    )

    parser.add_argument(
        "--to",
        type=str,
        default=None,
        help="Comma-separated recipients for OPS email. If omitted, uses OPS_RECIPIENTS env var.",
    )

    args = parser.parse_args()
    dos = datetime.strptime(args.dos, "%Y-%m-%d").date()

    ops_result = build_ops_daily_capacity(dos)
    body = render_ops_email(ops_result)

    # Always print (useful for runs + golden capture)
    print(body)

    if args.email:
        to_value = args.to or os.getenv("OPS_RECIPIENTS", "").strip()
        recipients = _parse_recipients(to_value)

        if not recipients:
            raise ValueError(
                "OPS recipients not provided. Supply --to or set OPS_RECIPIENTS in environment."
            )

        send_ops_capacity_email(
            body_text=body,
            recipients=recipients,
            subject="Daily Radiology Capacity – OPS (Execution)",
        )


if __name__ == "__main__":
    main()
