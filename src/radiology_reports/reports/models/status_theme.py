from dataclasses import dataclass
from reportlab.lib import colors
from radiology_reports.reports.models.location_report import Status


@dataclass(frozen=True)
class StatusStyle:
    status: Status
    label: str
    fill_color: object      # ReportLab color
    legend_color: str       # HTML color name


STATUS_THEME = {
    Status.GREEN: StatusStyle(
        status=Status.GREEN,
        label="Met or Exceeded Budget",
        fill_color=colors.lightgreen,
        legend_color="green",
    ),
    Status.YELLOW: StatusStyle(
        status=Status.YELLOW,
        label="Slightly Below Budget",
        fill_color=colors.gold,
        legend_color="gold",
    ),
    Status.RED: StatusStyle(
        status=Status.RED,
        label="Below Budget",
        fill_color=colors.lightcoral,
        legend_color="red",
    ),
    Status.INFO: StatusStyle(
        status=Status.INFO,
        label="Non-Business Day",
        fill_color=colors.lightblue,
        legend_color="blue",
    ),
}
