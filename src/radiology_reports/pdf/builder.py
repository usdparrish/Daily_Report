# src/radiology_reports/pdf/builder.py

from pathlib import Path
from functools import partial

from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

from radiology_reports.pdf.styles import RR_BLUE, RR_GRAY


# ============================================================
# ASSET PATHS (BULLETPROOF)
# ============================================================

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = PACKAGE_ROOT / "reporting" / "assets" / "logo.png"


# ============================================================
# HEADER / FOOTER
# ============================================================

def draw_header_footer(canvas, doc, report_title, report_date):
    canvas.saveState()
    width, height = doc.pagesize

    # Header bar (Radiology Regional Blue)
    canvas.setFillColor(colors.HexColor(RR_BLUE))
    canvas.rect(0, height - 0.9 * inch, width, 0.9 * inch, fill=1, stroke=0)

    # Logo (now guaranteed to resolve)
    if LOGO_PATH.exists():
        canvas.drawImage(
            ImageReader(str(LOGO_PATH)),
            0.5 * inch,
            height - 0.72 * inch,
            height=0.55 * inch,
            preserveAspectRatio=True,
            mask="auto"
        )

    # Title
    canvas.setFont("Helvetica-Bold", 15)
    canvas.setFillColor(colors.white)
    canvas.drawString(
        1.7 * inch,
        height - 0.52 * inch,
        report_title
    )

    # Date
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(
        width - 0.5 * inch,
        height - 0.52 * inch,
        report_date
    )

    # Footer rule
    canvas.setStrokeColor(colors.HexColor(RR_GRAY))
    canvas.line(
        0.5 * inch,
        0.75 * inch,
        width - 0.5 * inch,
        0.75 * inch
    )

    # Footer text
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor(RR_GRAY))
    canvas.drawString(
        0.5 * inch,
        0.5 * inch,
        "Confidential — Radiology Regional Internal Use Only"
    )
    canvas.drawRightString(
        width - 0.5 * inch,
        0.5 * inch,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# PDF BUILDER
# ============================================================

def build_pdf(
    output_path: str,
    elements: list,
    report_title: str,
    report_date: str,
    pagesize=LETTER
):
    """
    Builds a branded Radiology Regional PDF.
    Supports portrait or landscape pages.
    """

    doc = SimpleDocTemplate(
        output_path,
        pagesize=pagesize,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=1.15 * inch,
        bottomMargin=1.0 * inch,
    )

    doc.build(
        elements,
        onFirstPage=partial(
            draw_header_footer,
            report_title=report_title,
            report_date=report_date
        ),
        onLaterPages=partial(
            draw_header_footer,
            report_title=report_title,
            report_date=report_date
        )
    )
