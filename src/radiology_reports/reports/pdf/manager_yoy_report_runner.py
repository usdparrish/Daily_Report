# src/radiology_reports/reports/pdf/manager_yoy_report_runner.py
from pathlib import Path
from datetime import date

from reportlab.platypus import SimpleDocTemplate, PageBreak
from reportlab.lib.pagesizes import LETTER

from radiology_reports.reports.adapters.manager_location_yoy_adapter import (
    build_manager_location_yoy_reports,
)
from radiology_reports.reports.pdf.manager_location_yoy_page import (
    build_manager_location_yoy_page,
    build_manager_location_yoy_elements,
)

def run_manager_pdf_yoy_report(
    target_date: date,
    output_root: Path | str,
):
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    reports = build_manager_location_yoy_reports(target_date)
    generated = []

    for report in reports:
        filename = (
            f"Manager_Daily_YoY_Report_"
            f"{report.location_name.replace(' ', '_')}_"
            f"{target_date.isoformat()}.pdf"
        )
        pdf_path = output_root / filename
        build_manager_location_yoy_page(
            location=report,
            output_path=str(pdf_path),
        )
        generated.append(pdf_path)

    return generated

def run_manager_combined_yoy_pdf(
    target_date: date,
    output_root: Path | str,
):
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    combined_path = (
        output_root
        / f"Manager_Daily_YoY_Report_ALL_LOCATIONS_{target_date.isoformat()}.pdf"
    )

    reports = build_manager_location_yoy_reports(target_date)

    doc = SimpleDocTemplate(
        str(combined_path),
        pagesize=LETTER,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    elements = []
    for idx, report in enumerate(reports):
        elements.extend(build_manager_location_yoy_elements(report))
        if idx < len(reports) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    return combined_path