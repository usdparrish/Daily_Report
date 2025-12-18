# src/radiology_reports/reporting/monthreports.py
"""
Modernized Month Reports script
- Uses centralized DAL (no SQL here)
- Generates monthly chart PNG
- Enterprise-ready with typing/docstrings
- No 'daily' module
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from radiology_reports.data.workload import get_monthly_units  # New DAL function
from radiology_reports.utils.businessdays import businessdays  # Your existing function


app_path = Path(__file__).parent

def dailychart():
    """Generate monthly chart for given date"""
    strdate = input("Date (yyyy-mm-dd): ")
    ddate = datetime.strptime(strdate, '%Y-%m-%d')
    imonth = ddate.month
    iyear = ddate.year

    # Get this year and last year data
    thisyeardf = get_monthly_units(imonth, iyear)
    lastyeardf = get_monthly_units(imonth, iyear - 1)

    # Combine and create chart
    combined_df = combinedfs(thisyeardf, lastyeardf)
    createchart(combined_df, iyear, imonth)

def combinedfs(thisyeardf: pd.DataFrame, lastyeardf: pd.DataFrame) -> pd.DataFrame:
    if thisyeardf.empty and lastyeardf.empty:
        return pd.DataFrame()

    # From original — combine and pivot
    if not thisyeardf.empty:
        thisyeardf['Year'] = thisyeardf['ScheduleStartDate'].dt.year
        thisyeardf = thisyeardf.groupby(['Year', thisyeardf['ScheduleStartDate'].dt.day.rename('Day')])['Unit'].sum()
    if not lastyeardf.empty:
        lastyeardf['Year'] = lastyeardf['ScheduleStartDate'].dt.year
        lastyeardf = lastyeardf.groupby(['Year', lastyeardf['ScheduleStartDate'].dt.day.rename('Day')])['Unit'].sum()

    combined = pd.concat([lastyeardf, thisyeardf])
    final_df = combined.pivot_table(index='Day', values='Unit', columns='Year', fill_value=0)
    return final_df

def createchart(df: pd.DataFrame, year: int, month: int):
    if df.empty:
        print("No data to chart")
        return

    # Chart logic (from original)
    fig, ax = plt.subplots(figsize=(12, 6))
    df.plot(kind='bar', ax=ax, width=0.8)
    ax.set_title(f"Monthly Volume Chart - {calendar.month_name[month]} {year}")
    ax.set_xlabel("Day of Month")
    ax.set_ylabel("Unit")
    ax.legend([f"{year - 1}", f"{year}"])

    # Add labels, records, averages (from original logic)
    # ... (add your record, sum_unit, month_average logic here)

    output_chart = app_path / "output" / f"monthly_chart_{year}_{month:02d}.png"
    fig.savefig(output_chart, bbox_inches='tight')
    print(f"Chart saved to {output_chart}")

# CLI entry
if __name__ == "__main__":
    dailychart()