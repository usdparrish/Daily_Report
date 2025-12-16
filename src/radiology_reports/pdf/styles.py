# src/radiology_reports/pdf/styles.py
"""
Centralized corporate styling for all Radiology Regional PDFs
"""
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

REPORT_TITLE = ParagraphStyle('ReportTitle', fontSize=20, leading=24, alignment=TA_CENTER, textColor=colors.HexColor("#003087"))
SECTION_HEADER = ParagraphStyle('SectionHeader', fontSize=14, leading=18, alignment=TA_CENTER, backColor=colors.HexColor("#D3D3D3"), spaceBefore=30, spaceAfter=15)
DATE_HEADER = ParagraphStyle('TableHeader', fontSize=11, alignment=TA_CENTER, textColor=colors.white)

# Radiology Regional Corporate Styles

RR_BLUE = "#0071BC"     # Primary brand blue
RR_GRAY = "#A7A9AC"     # Secondary gray
RR_DARK = "#2F3A4A"     # Neutral dark (text only)
RR_LIGHT = "#F5F7FA"    # Table zebra

STATUS_GREEN = "#2E7D32"
STATUS_YELLOW = "#F9A825"
STATUS_RED = "#C62828"

