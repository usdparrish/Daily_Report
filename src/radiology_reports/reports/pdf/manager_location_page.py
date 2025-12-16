from reportlab.platypus import (
    SimpleDocTemplate,
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

from radiology_reports.reports.models.location_report import LocationReport, Status
from radiology_reports.reports.models.status_theme import STATUS_THEME


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def fmt(value):
    return value if value is not None else "N/A"


# -------------------------------------------------
# BUILD ELEMENTS FOR ONE LOCATION (REUSABLE)
# -------------------------------------------------
def build_manager_location_elements(location: LocationReport):
    styles = getSampleStyleSheet()
    elements = []

    # ======================
    # HEADER
    # ======================
    elements.append(
        Paragraph(
            f"<b>Radiology Regional – Daily Operations Report</b><br/>"
            f"Location: {location.location_name} &nbsp;&nbsp; "
            f"Date: {location.report_date.strftime('%b %d, %Y')}",
            styles["Title"],
        )
    )

    elements.append(Spacer(1, 12))

    # ======================
    # DAILY SUMMARY
    # ======================
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

    elements.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.lightgrey,
            spaceBefore=6,
            spaceAfter=6,
        )
    )

    elements.append(
        Paragraph(
            f"Completed Exams: {daily.completed_exams}<br/>"
            f"Budgeted Exams: {fmt(daily.budget_exams)}",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 8))

    # ======================
    # DAILY TABLE
    # ======================
    daily_table = [["Modality", "Exams", "Budget", "Δ", "Status"]]

    for m in daily.modalities:
        daily_table.append(
            [
                m.modality,
                m.completed_exams,
                fmt(m.budget_exams),
                fmt(m.delta),
                "●",
            ]
        )

    daily_tbl = Table(
        daily_table,
        colWidths=[2.4 * inch, 1 * inch, 1 * inch, 1 * inch, 0.6 * inch],
    )

    daily_style_tbl = TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-2, -1), "CENTER"),
            ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    )

    STATUS_COL = 4
    for row_idx, modality in enumerate(daily.modalities, start=1):
        style = STATUS_THEME[modality.status]
        daily_style_tbl.add(
            "BACKGROUND",
            (STATUS_COL, row_idx),
            (STATUS_COL, row_idx),
            style.fill_color,
        )

    daily_tbl.setStyle(daily_style_tbl)
    elements.append(daily_tbl)

    # ======================
    # MTD SUMMARY
    # ======================
    mtd = location.mtd
    mtd_style = STATUS_THEME[mtd.status]

    elements.append(Spacer(1, 16))

    elements.append(
        Paragraph(
            f"<b>MONTH-TO-DATE</b> (Business Days: {mtd.business_days_elapsed})<br/>"
            f"<b>MTD Status:</b> {mtd_style.label} "
            f'<font color="{mtd_style.legend_color}">●</font>',
            styles["Normal"],
        )
    )

    elements.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.lightgrey,
            spaceBefore=6,
            spaceAfter=6,
        )
    )

    elements.append(
        Paragraph(
            f"MTD Completed Exams: {mtd.completed_exams}<br/>"
            f"MTD Budgeted Exams: {fmt(mtd.budget_exams)}",
            styles["Normal"],
        )
    )


    elements.append(Spacer(1, 8))

    # ======================
    # MTD TABLE
    # ======================
    mtd_table = [["Modality", "MTD Exams", "MTD Budget", "Δ", "Status"]]

    for m in mtd.modalities:
        mtd_table.append(
            [
                m.modality,
                m.completed_exams,
                fmt(m.budget_exams),
                fmt(m.delta),
                "●",
            ]
        )

    mtd_tbl = Table(
        mtd_table,
        colWidths=[2.4 * inch, 1.2 * inch, 1.2 * inch, 1 * inch, 0.6 * inch],
    )

    mtd_style_tbl = TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-2, -1), "CENTER"),
            ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    )

    for row_idx, modality in enumerate(mtd.modalities, start=1):
        style = STATUS_THEME[modality.status]
        mtd_style_tbl.add(
            "BACKGROUND",
            (STATUS_COL, row_idx),
            (STATUS_COL, row_idx),
            style.fill_color,
        )

    mtd_tbl.setStyle(mtd_style_tbl)
    elements.append(mtd_tbl)

    # ======================
    # FOOTER LEGEND (SINGLE SOURCE OF TRUTH)
    # ======================
    elements.append(Spacer(1, 14))

    footer_style = ParagraphStyle(
        "FooterLegend",
        fontSize=8,
        textColor=colors.grey,
    )

    legend = (
        "<b>Status Legend:</b> "
        f'<font color="{STATUS_THEME[Status.GREEN].legend_color}">●</font> '
        f'GREEN = {STATUS_THEME[Status.GREEN].label} &nbsp;&nbsp; '
        f'<font color="{STATUS_THEME[Status.YELLOW].legend_color}">●</font> '
        f'YELLOW = {STATUS_THEME[Status.YELLOW].label} &nbsp;&nbsp; '
        f'<font color="{STATUS_THEME[Status.RED].legend_color}">●</font> '
        f'RED = {STATUS_THEME[Status.RED].label} &nbsp;&nbsp; '
        f'<font color="{STATUS_THEME[Status.INFO].legend_color}">●</font> '
        f'INFO = {STATUS_THEME[Status.INFO].label}'
        "<br/>"
        "Daily budget applies to business days only (Mon–Fri). "
        "Saturday exam volume is included; budget is not applied."
    )


    elements.append(Paragraph(legend, footer_style))

    return elements


# -------------------------------------------------
# SINGLE-LOCATION PDF WRAPPER
# -------------------------------------------------
def build_manager_location_page(location: LocationReport, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    elements = build_manager_location_elements(location)
    doc.build(elements)
