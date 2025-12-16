from datetime import date, timedelta
from pathlib import Path
import argparse
import sys
from radiology_reports.services.email_service import send_email
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
        help="Output directory for generated PDFs (relative to project root by default).",
    )

    parser.add_argument(
        "--email",
        action="store_true",
        help="Email the combined manager PDF (office network only).",
    )


    parser.add_argument(
        "--combined",
        action="store_true",
        help="Generate combined (all locations) PDF.",
    )

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
        
        combined_pdf = None

if args.combined:
    combined_pdf = run_manager_combined_pdf(
        target_date=target_date,
        output_root=output_root,
    )

    if args.email:
        if not combined_pdf:
            raise RuntimeError("--email requires --combined")

        recipients = os.getenv("DEFAULT_RECIPIENTS", "")
        if not recipients:
            raise RuntimeError("DEFAULT_RECIPIENTS not configured.")

        send_email(
            subject=f"Manager Daily Report – {target_date.isoformat()}",
            body=(
                "Attached is the Manager Daily Operations Report.\n\n"
                "This report reflects historical exam volumes vs budget."
            ),
            recipients=[r.strip() for r in recipients.split(",")],
            attachments=[combined_pdf],
        )
        
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
