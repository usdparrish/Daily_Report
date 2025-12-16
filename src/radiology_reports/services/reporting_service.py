# src/radiology_reports/services/reporting_service.py

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, List
import calendar
import pandas as pd

from radiology_reports.data.workload import (
    get_data_by_date,
    get_mammography_comparison
)
from radiology_reports.services.budget import Budget


class DailyReportingService:
    def __init__(self, target_date: str | datetime | None = None):
        if target_date is None:
            self.target_date = datetime.today().date()
        elif isinstance(target_date, str):
            self.target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            self.target_date = target_date.date()

        self.this_year = self.target_date.year
        self.last_year = self.this_year - 1
        self.two_years = self.this_year - 2

    # ============================================================
    # OPERATIONAL MATRIX (Daily + YoY + Budget)
    # ============================================================

    def get_operational_matrix(self) -> Dict[str, pd.DataFrame]:
        """
        Returns modality × location matrices for:
        - actual
        - YoY variance (Actual - Last Year)
        - Budget variance (Actual - Budget)
        """

        df_actual = get_data_by_date(self.target_date)
        df_last   = get_data_by_date(self.target_date - timedelta(days=364))

        budget = Budget(self.target_date.month, self.target_date.year)
        df_budget = budget.getbudgetdf()

        actual_pivot = self._pivot_volume(df_actual)
        last_pivot   = self._pivot_volume(df_last)
        budget_pivot = self._pivot_volume(df_budget)

        yoy_variance = actual_pivot - last_pivot
        budget_variance = actual_pivot - budget_pivot

        return {
            "actual": actual_pivot,
            "yoy": yoy_variance,
            "budget": budget_variance
        }

    # ============================================================
    # EXISTING / LEGACY METHODS (UNCHANGED)
    # ============================================================

    def _pivot_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame({"Message": ["No data available"]})

        pivot = (
            df.groupby(["ProcedureCategory", "LocationName"])["Unit"]
              .sum()
              .unstack(fill_value=0)
        )

        modality_order = [
            "CT SCANS", "DEXA", "DIAGNOSTIC", "MAM D", "MAMMOGRAPHY",
            "MRI", "NUCLEAR MED", "PET SCAN", "SPECIALS", "ULTRASOUND"
        ]

        pivot = pivot.reindex(modality_order, fill_value=0)
        pivot.loc["Total"] = pivot.sum()
        pivot["Total Result"] = pivot.sum(axis=1)

        return pivot.astype(int)

    # ============================================================
    # LOCATION PAGES (Manager View)
    # ============================================================

    def get_location_modality_pages(self):
        """
        One page per location.
        Shows all modalities (alphabetical) with YoY comparison.
        """

        df_this = get_data_by_date(self.target_date)
        df_last = get_data_by_date(self.target_date - timedelta(days=364))

        if df_this.empty:
            return []

        pages = []

        locations = sorted(df_this["LocationName"].unique())
        modalities = sorted(df_this["ProcedureCategory"].unique())

        for location in locations:
            rows = []

            for modality in modalities:
                curr = df_this.loc[
                    (df_this["LocationName"] == location) &
                    (df_this["ProcedureCategory"] == modality),
                    "Unit"
                ].sum()

                prev = df_last.loc[
                    (df_last["LocationName"] == location) &
                    (df_last["ProcedureCategory"] == modality),
                    "Unit"
                ].sum()

                delta = int(curr - prev)
                pct = (delta / prev * 100) if prev else None

                if pct is None:
                    status = "yellow"
                elif pct >= 5:
                    status = "green"
                elif pct <= -5:
                    status = "red"
                else:
                    status = "yellow"

                rows.append({
                    "modality": modality,
                    "prev": int(prev),
                    "curr": int(curr),
                    "delta": delta,
                    "pct": pct,
                    "status": status
                })

            pages.append({
                "location": location,
                "rows": rows
            })

        return pages
