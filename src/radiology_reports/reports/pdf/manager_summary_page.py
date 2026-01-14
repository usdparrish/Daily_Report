# src/radiology_reports/reports/pdf/manager_summary_page.py

from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from radiology_reports.reports.models.location_report import Status
from radiology_reports.reports.models.status_theme import STATUS_THEME
from radiology_reports.reports.pdf.formatting import fmt_number


def build_manager_summary_page(reports):
    styles = getSampleStyleSheet()
    elements = []

    # ======================
    # HEADER (MATCH LOCATION PAGE)
    # ======================
    report_date = reports[0].report_date
    elements.append(
        Paragraph(
            f"<b>Radiology Regional – Daily Operations Report</b><br/>"
            f"Date: {report_date.strftime('%b %d, %Y')}",
            styles["Title"],
        )
    )
    elements.append(Spacer(1, 12))

    # ======================
    # ENTERPRISE MTD SUMMARY
    # ======================
    total_completed = sum(r.mtd.completed_exams for r in reports)
    total_budget = sum(
        r.mtd.budget_exams for r in reports if r.mtd.budget_exams is not None
    )

    delta = total_completed - total_budget
    pct = delta / total_budget if total_budget > 0 else None

    if pct is None:
        status = Status.INFO
    elif pct >= 0:
        status = Status.GREEN
    elif pct >= -0.05:
        status = Status.YELLOW
    else:
        status = Status.RED

    style = STATUS_THEME[status]

    elements.append(
        Paragraph(
            f"<b>MONTH-TO-DATE</b><br/>"
            f"<b>MTD Status:</b> {style.label} "
            f'<font color="{style.legend_color}">●</font>',
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 6))

    enterprise_tbl = Table(
        [
            ["MTD Completed Exams", "MTD Budgeted Exams", "Δ", "Status"],
            [
                fmt_number(total_completed),
                fmt_number(total_budget),
                fmt_number(delta),
                "●",
            ],
        ],
        colWidths=[2.2 * inch, 2.2 * inch, 1.4 * inch, 0.8 * inch],
    )

    enterprise_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (3, 1), (3, 1), style.fill_color),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )

    elements.append(enterprise_tbl)
    elements.append(Spacer(1, 16))

    # ======================
    # LOCATION MTD SUMMARY TABLE
    # ======================
    data = [["Location", "MTD Exams", "MTD Budget", "Δ", "Status"]]

    for r in sorted(reports, key=lambda x: x.location_name):
        data.append(
            [
                r.location_name,
                fmt_number(r.mtd.completed_exams),
                fmt_number(r.mtd.budget_exams),
                fmt_number(r.mtd.delta),
                "●",
            ]
        )

    tbl = Table(
        data,
        colWidths=[2.4 * inch, 1.4 * inch, 1.4 * inch, 1.2 * inch, 0.6 * inch],
        repeatRows=1,
    )

    tbl_style = TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-2, -1), "CENTER"),
            ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    )

    STATUS_COL = 4
    for idx, r in enumerate(sorted(reports, key=lambda x: x.location_name), start=1):
        tbl_style.add(
            "BACKGROUND",
            (STATUS_COL, idx),
            (STATUS_COL, idx),
            STATUS_THEME[r.mtd.status].fill_color,
        )

    tbl.setStyle(tbl_style)
    elements.append(tbl)

    # ======================
    # FOOTER LEGEND (VERBATIM)
    # ======================
    elements.append(Spacer(1, 14))
    footer_style = ParagraphStyle("FooterLegend", fontSize=8, textColor=colors.grey)

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
    elements.append(PageBreak())

    return elements
