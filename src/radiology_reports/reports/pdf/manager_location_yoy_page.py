# src/radiology_reports/reports/pdf/manager_location_yoy_page.py
from reportlab.platypus import (
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    HRFlowable
)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from radiology_reports.reports.models.location_report_yoy import LocationReportYoY, Status
from radiology_reports.reports.models.status_theme import STATUS_THEME
from radiology_reports.reports.pdf.formatting import fmt_number, fmt_percent

def build_manager_location_yoy_elements(location: LocationReportYoY):
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(
        Paragraph(
            f"<b>Radiology Regional – Daily Operations Report (YoY)</b><br/>"
            f"Location: {location.location_name} &nbsp;&nbsp; "
            f"Date: {location.report_date.strftime('%b %d, %Y')}",
            styles["Title"],
        )
    )
    elements.append(Spacer(1, 12))

    # DAILY SUMMARY
    daily = location.daily
    daily_style = STATUS_THEME[daily.status]
    elements.append(
        Paragraph(
            f"<b>DAILY</b><br/>"
            f"<b>Status:</b> {daily_style.label} "
            f'<font color="{daily_style.legend_color}">●</font>',
            styles["Normal"],
        )
    )
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 6))

    # DAILY TABLE
    daily_tbl_data = [
        ["Modality", str(location.prev_year), str(location.curr_year), "Δ Units", "Δ %", "Status"]
    ]
    for modality in daily.modalities:
        daily_tbl_data.append([
            modality.modality,
            fmt_number(modality.prev_year_exams),
            fmt_number(modality.completed_exams),
            fmt_number(modality.delta),
            fmt_percent(modality.pct / 100) if modality.pct is not None else "N/A",
            "●"
        ])
    daily_tbl = Table(daily_tbl_data, colWidths=[1.5*inch, 0.75*inch, 0.75*inch, 0.75*inch, 0.75*inch, 0.5*inch])
    daily_tbl_style = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 12),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ])
    for row_idx, modality in enumerate(daily.modalities, start=1):
        style = STATUS_THEME[modality.status]
        daily_tbl_style.add("TEXTCOLOR", (5, row_idx), (5, row_idx), colors.HexColor(style.legend_color))
    daily_tbl.setStyle(daily_tbl_style)
    elements.append(daily_tbl)
    elements.append(Spacer(1, 12))

    # MTD SUMMARY (similar adaptation)
    mtd = location.mtd
    mtd_style = STATUS_THEME[mtd.status]
    elements.append(
        Paragraph(
            f"<b>MTD</b><br/>"
            f"<b>Status:</b> {mtd_style.label} "
            f'<font color="{mtd_style.legend_color}">●</font>',
            styles["Normal"],
        )
    )
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 6))

    # MTD TABLE (adapted similarly)
    mtd_tbl_data = [
        ["Modality", str(location.prev_year), str(location.curr_year), "Δ Units", "Δ %", "Status"]
    ]
    for modality in mtd.modalities:
        mtd_tbl_data.append([
            modality.modality,
            fmt_number(modality.prev_year_exams),
            fmt_number(modality.completed_exams),
            fmt_number(modality.delta),
            fmt_percent(modality.pct / 100) if modality.pct is not None else "N/A",
            "●"
        ])
    mtd_tbl = Table(mtd_tbl_data, colWidths=[1.5*inch, 0.75*inch, 0.75*inch, 0.75*inch, 0.75*inch, 0.5*inch])
    mtd_tbl_style = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 12),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ])
    for row_idx, modality in enumerate(mtd.modalities, start=1):
        style = STATUS_THEME[modality.status]
        mtd_tbl_style.add("TEXTCOLOR", (5, row_idx), (5, row_idx), colors.HexColor(style.legend_color))
    mtd_tbl.setStyle(mtd_tbl_style)
    elements.append(mtd_tbl)

    # Footer Legend (adapted)
    elements.append(Spacer(1, 14))
    footer_style = ParagraphStyle("FooterLegend", fontSize=8, textColor=colors.grey)
    legend = (
        "<b>Status Legend:</b> "
        f'<font color="{STATUS_THEME[Status.GREEN].legend_color}">●</font> GREEN = 5%+ Growth &nbsp;&nbsp; '
        f'<font color="{STATUS_THEME[Status.YELLOW].legend_color}">●</font> YELLOW = Within ±5% &nbsp;&nbsp; '
        f'<font color="{STATUS_THEME[Status.RED].legend_color}">●</font> RED = -5%+ Decline &nbsp;&nbsp; '
        f'<font color="{STATUS_THEME[Status.INFO].legend_color}">●</font> INFO = No Prior Data<br/>'
        "Comparisons are to the same period previous year. Saturday volumes included without adjustment."
    )
    elements.append(Paragraph(legend, footer_style))
    return elements

# Single-location PDF wrapper
from reportlab.platypus import SimpleDocTemplate
def build_manager_location_yoy_page(location: LocationReportYoY, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    elements = build_manager_location_yoy_elements(location)
    doc.build(elements)