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
class ModalityMetrics:
    modality: str
    completed_exams: int
    budget_exams: Optional[int]
    delta: Optional[int]
    status: Status

@dataclass
class PeriodMetrics:
    label: str          # "DAILY" or "MTD"
    is_business_day: bool
    business_days_elapsed: int
    business_days_total: Optional[int]  # Added to support MTD summary calculations
    completed_exams: int
    budget_exams: Optional[int]
    delta: Optional[int]
    status: Status
    modalities: List[ModalityMetrics]

@dataclass
class LocationReport:
    location_name: str
    report_date: date
    daily: PeriodMetrics
    mtd: PeriodMetrics