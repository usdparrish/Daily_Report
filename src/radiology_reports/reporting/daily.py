from pathlib import Path
from reportlab.platypus import Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER, landscape

from radiology_reports.reporting.csv_writer import write_csv
from radiology_reports.services.reporting_service import DailyReportingService
from radiology_reports.pdf.builder import build_pdf
from radiology_reports.pdf.table_builder import (
    build_operational_matrix_table,
    build_location_modality_table
)

PAGE_SIZE = landscape(LETTER)


def run_daily_report(target_date: str | None = None):

    service = DailyReportingService(target_date)
    styles = getSampleStyleSheet()
    elements = []

    # ============================================================
    # OPERATIONAL MATRIX PAGE (PDF)
    # ============================================================

    matrices = service.get_operational_matrix()

    elements.append(
        Paragraph(
            "<b>Daily Volume by Modality and Location</b>",
            styles["Title"]
        )
    )
    elements.append(Spacer(1, 12))

    elements.append(
        build_operational_matrix_table(
            matrices["actual"],
            "ACTUAL (Today)",
            PAGE_SIZE
        )
    )

    elements.append(PageBreak())

    # ============================================================
    # LOCATION PAGES (PDF)
    # ============================================================

    pages = service.get_location_modality_pages()

    for page in pages:
        elements.append(
            Paragraph(
                f"<b>{page['location']}</b> — Modality Performance",
                styles["Heading2"]
            )
        )
        elements.append(Spacer(1, 12))
        elements.append(build_location_modality_table(page["rows"]))
        elements.append(PageBreak())

    # ============================================================
    # OUTPUT PATHS
    # ============================================================

    output_dir = Path("output/daily")
    output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------
    # PDF OUTPUT
    # -----------------------------
    pdf_path = output_dir / f"Daily_Radiology_Report_{service.target_date}.pdf"

    build_pdf(
        output_path=str(pdf_path),
        elements=elements,
        report_title="Daily Radiology Volume Report",
        report_date=service.target_date.strftime("%B %d, %Y"),
        pagesize=PAGE_SIZE
    )

    print(f"PDF written to: {pdf_path}")

    # -----------------------------
    # CSV OUTPUT (LEGACY-COMPATIBLE)
    # -----------------------------
    #
    # IMPORTANT:
    # - This dataframe must match legacy dailystep1.csv
    # - No column changes
    # - No zero-filling
    #
    daily_csv_df = service.get_daily_csv_dataframe()

    csv_dir = Path("output/csv")
    csv_dir.mkdir(parents=True, exist_ok=True)

    csv_path = csv_dir / "dailystep1.csv"

    write_csv(
        df=daily_csv_df,
        output_path=csv_path
    )

    print(f"Daily CSV written to: {csv_path}")


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run_daily_report(date)
