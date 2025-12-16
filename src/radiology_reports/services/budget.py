# src/radiology_reports/services/budget.py
"""
Clean Budget service — NO SQL, NO connections
Uses only the centralized data layer
"""

from __future__ import annotations

from radiology_reports.data.workload import get_budget_daily_volume


class Budget:
    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year

    def getbudgetdf(self) -> pd.DataFrame:
        """Get daily projected budget for the month"""
        df = get_budget_daily_volume(self.year, self.month)
        if not df.empty:
            df['Year'] = 'Budget'
        return df

    def get_total_budget(self) -> int:
        """Convenient helper for summary"""
        df = self.getbudgetdf()
        return int(df['Unit'].sum()) if not df.empty else 0