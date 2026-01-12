# src/radiology_reports/reports/models/status_theme.py

from dataclasses import dataclass
from reportlab.lib import colors


@dataclass(frozen=True)
class StatusStyle:
    """
    Presentation-only status styling.
    This layer must NOT depend on domain enums.
    """
    status: str
    label: str
    fill_color: object      # ReportLab color
    legend_color: str       # HTML color name


STATUS_THEME = {
    "GREEN": StatusStyle(
        status="GREEN",
        label="Met or Exceeded Budget",
        fill_color=colors.lightgreen,
        legend_color="green",
    ),
    "YELLOW": StatusStyle(
        status="YELLOW",
        label="Slightly Below Budget",
        fill_color=colors.gold,
        legend_color="gold",
    ),
    "RED": StatusStyle(
        status="RED",
        label="Below Budget",
        fill_color=colors.lightcoral,
        legend_color="red",
    ),
    "INFO": StatusStyle(
        status="INFO",
        label="Non-Business Day",
        fill_color=colors.lightblue,
        legend_color="blue",
    ),
}
