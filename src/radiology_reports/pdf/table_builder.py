# src/radiology_reports/pdf/table_builder.py

from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
import pandas as pd

from radiology_reports.pdf.styles import (
    RR_BLUE,
    RR_LIGHT,
    STATUS_GREEN,
    STATUS_YELLOW,
    STATUS_RED,
)

# ============================================================
# STYLES
# ============================================================

ROW_HEADER_STYLE = ParagraphStyle(
    name="RowHeader",
    alignment=TA_LEFT,
    fontName="Helvetica",
    fontSize=8.5,
    leading=9.5,
)

# ============================================================
# OPERATIONAL MATRIX (LANDSCAPE)
# ============================================================

def build_operational_matrix_table(
    df: pd.DataFrame,
    title: str,
    pagesize
):
    """
    Modality × Location matrix

    Design rules (LOCKED):
    - Full location names (no abbreviations)
    - No word breaking
    - Single-line headers
    - Subtle column separators
    - Slightly tighter first column
    """

    # -----------------------------
    # Header row (PLAIN STRINGS)
    # -----------------------------
    data = [[
        title
    ] + [
        col.replace("_", " ")
        for col in df.columns
    ]]

    # -----------------------------
    # Data rows
    # -----------------------------
    for idx, row in df.iterrows():
        data.append(
            [Paragraph(str(idx), ROW_HEADER_STYLE)] +
            row.tolist()
        )

    num_cols = len(data[0])

    # -----------------------------
    # Column width calculation
    # -----------------------------
    page_width, _ = pagesize
    usable_width = page_width - (1.0 * inch)

    # ↓ Slightly reduced per Option A
    first_col_width = 1.4 * inch
    remaining_width = usable_width - first_col_width
    other_col_width = remaining_width / (num_cols - 1)

    col_widths = [first_col_width] + \
                 [other_col_width] * (num_cols - 1)

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1
    )

    # -----------------------------
    # Table styling
    # -----------------------------
    style = [
        # Header
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor(RR_BLUE)),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 7.5),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("TOPPADDING", (0,0), (-1,0), 9),
        ("BOTTOMPADDING", (0,0), (-1,0), 9),

        # Strong header separators
        ("LINEBEFORE", (1,0), (-1,0), 1.0, colors.HexColor("#E6E6E6")),

        # Lighter body separators
        ("LINEBEFORE", (1,1), (-1,-1), 0.25, colors.lightgrey),

        # Body
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (1,1), (-1,-1), 8),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),

        # Zebra striping
        ("ROWBACKGROUNDS", (0,1), (-1,-1),
        [colors.white, colors.HexColor(RR_LIGHT)]),

        # Grid
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),

        # Total Result emphasis
        ("BACKGROUND", (-1,0), (-1,-1), colors.HexColor("#0A5FA5")),
        ("FONTNAME", (-1,0), (-1,0), "Helvetica-Bold"),
    ]


    # -----------------------------
    # Variance coloring (YoY / Budget)
    # -----------------------------
    for r in range(1, len(data)):
        for c in range(1, num_cols):
            val = data[r][c]
            if isinstance(val, (int, float)):
                if val > 0:
                    style.append(
                        ("TEXTCOLOR", (c,r), (c,r),
                         colors.HexColor(STATUS_GREEN))
                    )
                elif val < 0:
                    style.append(
                        ("TEXTCOLOR", (c,r), (c,r),
                         colors.HexColor(STATUS_RED))
                    )

    table.setStyle(TableStyle(style))
    return table


# ============================================================
# LOCATION DETAIL TABLE (PER-LOCATION PAGES)
# ============================================================

def build_location_modality_table(rows: list[dict]):
    """
    One-location modality table for manager pages.
    """

    data = [
        ["Modality", "2024", "2025", "Δ Units", "Δ %", "Status"]
    ]

    for r in rows:
        pct = "" if r.get("pct") is None else f"{int(round(r['pct']))}%"
        data.append([
            r["modality"],
            r["prev"],
            r["curr"],
            r["delta"],
            pct,
            "●"
        ])

    col_widths = [
        2.2 * inch,
        0.9 * inch,
        0.9 * inch,
        1.0 * inch,
        0.8 * inch,
        0.6 * inch,
    ]

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1
    )

    style = [
        # Header
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor(RR_BLUE)),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("BOTTOMPADDING", (0,0), (-1,0), 10),

        # Body
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("ALIGN", (1,1), (-2,-1), "RIGHT"),
        ("ALIGN", (-1,1), (-1,-1), "CENTER"),

        # Zebra
        ("ROWBACKGROUNDS", (0,1), (-1,-1),
         [colors.white, colors.HexColor(RR_LIGHT)]),

        # Borders
        ("BOX", (0,0), (-1,-1), 0.75, colors.grey),
        ("LINEBELOW", (0,0), (-1,0), 1, colors.grey),
    ]

    for i, r in enumerate(rows, start=1):
        color = {
            "green": STATUS_GREEN,
            "yellow": STATUS_YELLOW,
            "red": STATUS_RED,
        }.get(r.get("status"), "#000000")

        style.append(
            ("TEXTCOLOR", (-1,i), (-1,i), colors.HexColor(color))
        )

    table.setStyle(TableStyle(style))
    return table
