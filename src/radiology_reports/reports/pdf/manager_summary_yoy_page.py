# src/radiology_reports/reports/pdf/manager_summary_yoy_page.py

from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from radiology_reports.reports.models.location_report import Status
from radiology_reports.reports.models.status_theme import STATUS_THEME
from radiology_reports.reports.pdf.formatting import fmt_number, fmt_percent


# -------------------------------------------------
# YoY-specific status labels (do NOT use budget text)
# -------------------------------------------------
YOY_STATUS_LABELS = {
    Status.GREEN: "5%+ Growth",
    Status.YELLOW: "Within ±5%",
    Status.RED: "-5%+ Decline",
    Status.INFO: "No Prior Data / Non-Business Day",
}


def build_manager_summary_yoy_page(reports):
    """
    Page 1 management summary for YoY report.
    Presentation-layer only.
    """

    styles = getSampleStyleSheet()
    elements = []

    report_date = reports[0].report_date

    # ======================
    # HEADER (MATCH LOCATION PAGE)
    # ======================
    elements.append(
        Paragraph(
            f"<b>Radiology Regional – Daily Operations Report (YoY)</b><br/>"
            f"Date: {report_date.strftime('%b %d, %Y')}",
            styles["Title"],
        )
    )
    elements.append(Spacer(1, 12))

    # ======================
    # ENTERPRISE MTD SUMMARY
    # ======================
    total_completed = sum(r.mtd.completed_exams for r in reports)
    total_prev = sum(r.mtd.prev_year_exams for r in reports)

    delta = total_completed - total_prev
    pct = delta / total_prev if total_prev > 0 else None

    if pct is None:
        status = Status.INFO
    elif pct >= 0.05:
        status = Status.GREEN
    elif pct <= -0.05:
        status = Status.RED
    else:
        status = Status.YELLOW

    style = STATUS_THEME[status.value]
    label = YOY_STATUS_LABELS[status]

    elements.append(
        Paragraph(
            f"<b>MONTH-TO-DATE</b><br/>"
            f"<b>MTD Status:</b> {label} "
            f'<font color="{style.legend_color}">●</font>',
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 6))

    enterprise_tbl = Table(
        [
            ["MTD Completed Exams", "MTD Previous Year Exams", "Δ", "Δ %", "Status"],
            [
                fmt_number(total_completed),
                fmt_number(total_prev),
                fmt_number(delta),
                fmt_percent(pct),
                "●",
            ],
        ],
        colWidths=[2.2 * inch, 2.4 * inch, 1.2 * inch, 1.2 * inch, 0.8 * inch],
    )

    enterprise_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (4, 1), (4, 1), style.fill_color),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )

    elements.append(enterprise_tbl)
    elements.append(Spacer(1, 16))

    # ======================
    # LOCATION MTD SUMMARY TABLE (UNCHANGED)
    # ======================
    data = [["Location", "MTD Exams", "MTD Prev", "Δ", "Δ %", "Status"]]

    for r in sorted(reports, key=lambda x: x.location_name):
        data.append(
            [
                r.location_name,
                fmt_number(r.mtd.completed_exams),
                fmt_number(r.mtd.prev_year_exams),
                fmt_number(r.mtd.delta),
                fmt_percent(r.mtd.pct),
                "●",
            ]
        )

    tbl = Table(
        data,
        colWidths=[
            2.4 * inch,
            1.2 * inch,
            1.2 * inch,
            1.1 * inch,
            1.1 * inch,
            0.6 * inch,
        ],
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

    STATUS_COL = 5
    for idx, r in enumerate(sorted(reports, key=lambda x: x.location_name), start=1):
        tbl_style.add(
            "BACKGROUND",
            (STATUS_COL, idx),
            (STATUS_COL, idx),
            STATUS_THEME[r.mtd.status.value].fill_color,
        )

    tbl.setStyle(tbl_style)
    elements.append(tbl)
    elements.append(Spacer(1, 16))

    # ======================
    # ENTERPRISE MTD YOY BY MODALITY
    # (Aggregated from existing location modality rollups)
    # ======================
    modality_totals = {}

    for r in reports:
        for m in r.mtd.modalities:
            entry = modality_totals.setdefault(
                m.modality,
                {"completed": 0, "prev": 0},
            )
            entry["completed"] += m.completed_exams
            entry["prev"] += m.prev_year_exams

    modality_rows = []
    for modality, vals in modality_totals.items():
        completed = vals["completed"]
        prev = vals["prev"]
        delta = completed - prev
        pct = delta / prev if prev > 0 else None

        if pct is None:
            status = Status.INFO
        elif pct >= 0.05:
            status = Status.GREEN
        elif pct <= -0.05:
            status = Status.RED
        else:
            status = Status.YELLOW

        modality_rows.append(
            {
                "modality": modality,
                "completed": completed,
                "prev": prev,
                "delta": delta,
                "pct": pct,
                "status": status,
            }
        )

    # Worst → Best by Δ %
    modality_rows.sort(
        key=lambda x: (x["pct"] is None, x["pct"]),
    )

    mod_data = [["Modality", "MTD Exams", "MTD Prev", "Δ", "Δ %", "Status"]]

    for row in modality_rows:
        mod_data.append(
            [
                row["modality"],
                fmt_number(row["completed"]),
                fmt_number(row["prev"]),
                fmt_number(row["delta"]),
                fmt_percent(row["pct"]),
                "●",
            ]
        )

    mod_tbl = Table(
        mod_data,
        colWidths=[
            2.0 * inch,
            1.2 * inch,
            1.2 * inch,
            1.1 * inch,
            1.1 * inch,
            0.6 * inch,
        ],
        repeatRows=1,
    )

    mod_style = TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-2, -1), "CENTER"),
            ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    )

    STATUS_COL = 5
    for idx, row in enumerate(modality_rows, start=1):
        mod_style.add(
            "BACKGROUND",
            (STATUS_COL, idx),
            (STATUS_COL, idx),
            STATUS_THEME[row["status"].value].fill_color,
        )

    mod_tbl.setStyle(mod_style)
    elements.append(mod_tbl)

    # ======================
    # FOOTER LEGEND (UNCHANGED, BELOW ALL TABLES)
    # ======================
    elements.append(Spacer(1, 14))
    footer_style = ParagraphStyle(
        "FooterLegend",
        fontSize=8,
        textColor=colors.grey,
    )

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
        "Comparisons are to the same period previous year. "
        "Saturday volumes included without adjustment."
    )

    elements.append(Paragraph(legend, footer_style))
    elements.append(PageBreak())

    return elements
