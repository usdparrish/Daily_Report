# src/radiology_reports/reports/pdf/manager_location_yoy_page.py

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    HRFlowable,
)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from radiology_reports.reports.models.location_report_yoy import LocationReportYoY
from radiology_reports.reports.models.location_report import Status
from radiology_reports.reports.models.status_theme import STATUS_THEME
from radiology_reports.reports.pdf.formatting import fmt_number, fmt_percent


def _yoy_status_label(status_value: str, *, report_date) -> str:
    """
    YoY labels (NOT budget labels).
    Keep INFO flexible because adapter may use INFO for weekends or missing prior data.
    """
    if status_value == Status.GREEN.value:
        return "5%+ Growth"
    if status_value == Status.YELLOW.value:
        return "Within ±5%"
    if status_value == Status.RED.value:
        return "-5%+ Decline"
    # INFO
    if report_date.weekday() >= 5:
        return "Non-Business Day"
    return "No Prior Data"


def fmt_na(value):
    return value if value is not None else "N/A"


def build_manager_location_yoy_elements(location: LocationReportYoY):
    styles = getSampleStyleSheet()
    elements = []

    # ======================
    # HEADER (match budget structure)
    # ======================
    elements.append(
        Paragraph(
            f"<b>Radiology Regional – Daily Operations Report (YoY)</b><br/>"
            f"Location: {location.location_name} &nbsp;&nbsp; "
            f"Date: {location.report_date.strftime('%b %d, %Y')}",
            styles["Title"],
        )
    )
    elements.append(Spacer(1, 12))

    # ======================
    # DAILY SUMMARY (match budget structure)
    # ======================
    daily = location.daily
    daily_status_key = daily.status.value
    daily_style = STATUS_THEME[daily_status_key]
    daily_label = _yoy_status_label(daily_status_key, report_date=location.report_date)

    elements.append(
        Paragraph(
            f"<b>DAILY</b><br/>"
            f"<b>Status:</b> {daily_label} "
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

    # Add budget-like summary lines, but YoY values
    daily_completed = getattr(daily, "completed_exams", None)
    daily_prev = getattr(daily, "prev_year_exams", None)
    daily_delta = getattr(daily, "delta", None)
    daily_pct = getattr(daily, "pct", None)  # adapter appears to store percent as whole number

    elements.append(
        Paragraph(
            f"Completed Exams: {fmt_number(daily_completed)}<br/>"
            f"Previous Year Exams: {fmt_na(fmt_number(daily_prev))}<br/>"
            f"Variance to Previous Year: {fmt_na(fmt_number(daily_delta))} "
            f"({fmt_na(fmt_percent(daily_pct / 100)) if daily_pct is not None else 'N/A'})",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 8))

    # ======================
    # DAILY TABLE (match budget table feel)
    # ======================
    daily_table = [["Modality", "Exams", "Prev Year", "Δ", "Δ %", "Status"]]
    for m in daily.modalities:
        pct = fmt_percent(m.pct / 100) if m.pct is not None else "N/A"
        daily_table.append(
            [
                m.modality,
                fmt_number(m.completed_exams),
                fmt_number(m.prev_year_exams),
                fmt_number(m.delta),
                pct,
                "●",
            ]
        )

    daily_tbl = Table(
        daily_table,
        colWidths=[2.0 * inch, 0.85 * inch, 0.85 * inch, 0.75 * inch, 0.75 * inch, 0.55 * inch],
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

    STATUS_COL = 5
    for row_idx, modality in enumerate(daily.modalities, start=1):
        style = STATUS_THEME[modality.status.value]
        # Match budget: status column background fill
        daily_style_tbl.add(
            "BACKGROUND",
            (STATUS_COL, row_idx),
            (STATUS_COL, row_idx),
            style.fill_color,
        )

    daily_tbl.setStyle(daily_style_tbl)
    elements.append(daily_tbl)

    # ======================
    # MTD SUMMARY (match budget structure)
    # ======================
    mtd = location.mtd
    mtd_status_key = mtd.status.value
    mtd_style = STATUS_THEME[mtd_status_key]
    mtd_label = _yoy_status_label(mtd_status_key, report_date=location.report_date)

    elements.append(Spacer(1, 16))
    elements.append(
        Paragraph(
            f"<b>MONTH-TO-DATE</b>"
            f" (Business Days: {getattr(mtd, 'business_days_elapsed', 'N/A')})<br/>"
            f"<b>MTD Status:</b> {mtd_label} "
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

    mtd_completed = getattr(mtd, "completed_exams", None)
    mtd_prev = getattr(mtd, "prev_year_exams", None)
    mtd_delta = getattr(mtd, "delta", None)
    mtd_pct = getattr(mtd, "pct", None)

    elements.append(
        Paragraph(
            f"MTD Completed Exams: {fmt_number(mtd_completed)}<br/>"
            f"MTD Previous Year Exams: {fmt_na(fmt_number(mtd_prev))}<br/>"
            f"MTD Variance to Previous Year: {fmt_na(fmt_number(mtd_delta))} "
            f"({fmt_na(fmt_percent(mtd_pct / 100)) if mtd_pct is not None else 'N/A'})",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 8))

    # ======================
    # MTD TABLE (match budget table feel)
    # ======================
    mtd_table = [["Modality", "MTD Exams", "MTD Prev", "Δ", "Δ %", "Status"]]
    for m in mtd.modalities:
        pct = fmt_percent(m.pct / 100) if m.pct is not None else "N/A"
        mtd_table.append(
            [
                m.modality,
                fmt_number(m.completed_exams),
                fmt_number(m.prev_year_exams),
                fmt_number(m.delta),
                pct,
                "●",
            ]
        )

    mtd_tbl = Table(
        mtd_table,
        colWidths=[2.0 * inch, 0.95 * inch, 0.95 * inch, 0.75 * inch, 0.75 * inch, 0.55 * inch],
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
        style = STATUS_THEME[modality.status.value]
        mtd_style_tbl.add(
            "BACKGROUND",
            (STATUS_COL, row_idx),
            (STATUS_COL, row_idx),
            style.fill_color,
        )

    mtd_tbl.setStyle(mtd_style_tbl)
    elements.append(mtd_tbl)

    # ======================
    # FOOTER LEGEND (YoY-specific wording)
    # ======================
    elements.append(Spacer(1, 14))
    footer_style = ParagraphStyle("FooterLegend", fontSize=8, textColor=colors.grey)

    legend = (
        "<b>Status Legend:</b> "
        f'<font color="{STATUS_THEME[Status.GREEN.value].legend_color}">●</font> '
        "GREEN = 5%+ Growth &nbsp;&nbsp; "
        f'<font color="{STATUS_THEME[Status.YELLOW.value].legend_color}">●</font> '
        "YELLOW = Within ±5% &nbsp;&nbsp; "
        f'<font color="{STATUS_THEME[Status.RED.value].legend_color}">●</font> '
        "RED = -5%+ Decline &nbsp;&nbsp; "
        f'<font color="{STATUS_THEME[Status.INFO.value].legend_color}">●</font> '
        "INFO = No Prior Data / Non-Business Day"
        "<br/>"
        "Comparisons are to the same period previous year. Saturday volumes included without adjustment."
    )
    elements.append(Paragraph(legend, footer_style))

    return elements


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
