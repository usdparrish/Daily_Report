# src/radiology_reports/reports/models/location_report_yoy.py
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Optional

class Status(Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    INFO = "INFO"

@dataclass
class ModalityMetricsYoY:
    modality: str
    prev_year_exams: int
    completed_exams: int
    delta: int
    pct: Optional[float]  # Percentage change
    status: Status

@dataclass
class PeriodMetricsYoY:
    label: str          # "DAILY" or "MTD"
    is_business_day: bool
    business_days_elapsed: int
    business_days_total: Optional[int]
    prev_year_exams: int
    completed_exams: int
    delta: int
    pct: Optional[float]
    status: Status
    modalities: List[ModalityMetricsYoY]

@dataclass
class LocationReportYoY:
    location_name: str
    report_date: date
    prev_year: int
    curr_year: int
    daily: PeriodMetricsYoY
    mtd: PeriodMetricsYoY