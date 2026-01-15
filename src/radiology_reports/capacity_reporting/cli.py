import argparse
from datetime import date, timedelta, datetime

from radiology_reports.capacity_reporting.daily_capacity_usecase import (
    run_daily_capacity_report,
)
from radiology_reports.presentation.console import (
    render_daily_capacity,
)
from radiology_reports.presentation.email import (
    send_executive_capacity_email,
)
from radiology_reports.utils.config import config


def _default_dos() -> date:
    return date.today() + timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Daily Capacity Utilization Report (Exec)"
    )

    parser.add_argument(
        "--dos",
        type=str,
        default=None,
        help="Day of Service (YYYY-MM-DD). Defaults to tomorrow.",
    )

    parser.add_argument(
        "--email",
        action="store_true",
        help="Send report via email to default recipients",
    )

    # 🔹 NEW (minimal, backward-safe)
    parser.add_argument(
        "--audience",
        choices=["scheduling", "ops"],
        default="scheduling",
        help="Email audience (controls content depth)",
    )

    args = parser.parse_args()

    dos = (
        datetime.strptime(args.dos, "%Y-%m-%d").date()
        if args.dos
        else _default_dos()
    )

    result = run_daily_capacity_report(dos)

    report_text = render_daily_capacity(result)

    if args.email:
        send_executive_capacity_email(
            report_text=report_text,
            recipients=config.DEFAULT_RECIPIENTS,
            audience=args.audience,   # 🔹 NEW (passed through)
        )


if __name__ == "__main__":
    main()
