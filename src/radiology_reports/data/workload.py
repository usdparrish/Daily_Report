# src/radiology_reports/data/workload.py
from __future__ import annotations
# src/radiology_reports/data/workload.py
import warnings
warnings.filterwarnings("ignore", category=UserWarning)  # Nuclear option — zero warnings

import pyodbc
import pandas as pd
from contextlib import contextmanager
from datetime import date, datetime
import calendar

from radiology_reports.utils.config import config


@contextmanager
def get_connection():
    conn = pyodbc.connect(config.SQLALCHEMY_DATABASE_URI)
    try:
        yield conn
    finally:
        conn.close()


# ===================================================================
# DAILY REPORT QUERIES
# ===================================================================

def get_data_by_date(target_date: str | datetime | date) -> pd.DataFrame:
    """Replaces the old Daily.databydate()"""
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d")
    if isinstance(target_date, datetime):
        target_date = target_date.date()

    sql = """
        SELECT 
            ScheduleStartDate,
            d.LocationName,
            ProcedureCategory,
            l.Region,
            SUM(Unit) AS Unit,
            YEAR(ScheduleStartDate) AS Year
        FROM DAILY d
        INNER JOIN LOCATIONS l ON d.LocationName = l.LocationName
        WHERE CAST(ScheduleStartDate AS DATE) = ?
        GROUP BY ScheduleStartDate, d.LocationName, ProcedureCategory, l.Region
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[target_date])


def get_outside_reads_by_date(target_date: str | datetime | date) -> pd.DataFrame:
    """Single Outside Reads total for the given DOS"""
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    sql = """
        SELECT YEAR(ScheduleStartDate) AS Year, SUM(Unit) AS Unit
        FROM DAILY
        WHERE CAST(ScheduleStartDate AS DATE) = ?
          AND ProcedureCategory = 'Outside Reads'
        GROUP BY YEAR(ScheduleStartDate)
    """
    with get_connection() as conn:
        df = pd.read_sql(sql, conn, params=[target_date])

    if df.empty:
        return pd.DataFrame({"Year": [target_date.year], "Unit": [0]})
    return df


def get_mammography_comparison(start_date: str | datetime | date,
                               end_date:   str | datetime | date) -> pd.DataFrame:
    """Used by the old mammodf() function"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    sql = """
        SELECT 
            LocationName,
            ProcedureCategory,
            SUM(Unit) AS Unit,
            YEAR(ScheduleStartDate) AS Year
        FROM DAILY
        WHERE ScheduleStartDate BETWEEN ? AND ?
          AND ProcedureCategory LIKE '%Mammo%'
        GROUP BY LocationName, ProcedureCategory, YEAR(ScheduleStartDate)
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[start_date, end_date])


# ===================================================================
# Your original capacity functions (keep them exactly as they were – they are perfect)
# ===================================================================

def get_active_locations() -> pd.DataFrame:
    sql = "SELECT LocationName FROM dbo.v_Active_Locations"
    with get_connection() as conn:
        return pd.read_sql(sql, conn)


# ===================================================================
# CAPACITY & WORKLOAD SNAPSHOT QUERIES (your existing excellent ones)
# ===================================================================

def get_active_locations() -> pd.DataFrame:
    """All currently active imaging centers"""
    sql = "SELECT LocationName FROM dbo.v_Active_Locations"
    with get_connection() as conn:
        return pd.read_sql(sql, conn)


def get_daily_completed_workload(dos: str | date | datetime) -> pd.DataFrame:
    """Actual completed weighted exams for a given DOS"""
    if isinstance(dos, (date, datetime)):
        dos = dos.strftime("%Y-%m-%d")
    sql = """
        SELECT location, modality, volume, modality_weight, weighted_units
        FROM dbo.v_Daily_Workload_Weighted
        WHERE dos = ?
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[dos])


def get_scheduled_snapshot(dos: str | date | datetime) -> pd.DataFrame:
    """Morning scheduled snapshot (inserted = dos) aggregated with weights applied"""

    if isinstance(dos, (date, datetime)):
        dos = dos.strftime("%Y-%m-%d")

    sql = """
        SELECT
            s.location,
            s.modality,

            -- keep legacy column name
            SUM(s.volume) AS volume,

            -- keep legacy column name (same for all rows in group)
            MAX(w.weight) AS modality_weight,

            -- correct aggregated workload
            CAST(SUM(s.volume * w.weight) AS DECIMAL(10,2)) AS weighted_units

        FROM dbo.SCHEDULED s
        JOIN dbo.v_Active_Locations a
            ON s.location = a.LocationName
        JOIN dbo.Modality_Weight_Governance w
            ON UPPER(LTRIM(RTRIM(w.modality))) =
               UPPER(LTRIM(RTRIM(s.modality)))
           AND s.dos BETWEEN w.effective_start
                          AND ISNULL(w.effective_end, '9999-12-31')

        WHERE s.inserted = s.dos
          AND s.dos = ?

        GROUP BY
            s.location,
            s.modality

        ORDER BY
            s.location,
            s.modality;
    """

    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[dos])





def get_location_capacity_90th() -> pd.DataFrame:
    """90th percentile capacity per location"""
    sql = """
        SELECT location, capacity_weighted_90th
        FROM dbo.v_Capacity_Model
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn)


def get_modality_capacity_detail() -> pd.DataFrame:
    """Modality-level 90th percentile capacity + status"""
    sql = """
        SELECT 
            location, modality,
            capacity_weighted_90th_modality,
            pct_of_capacity,
            capacity_status
        FROM dbo.v_Modality_Capacity_Model
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn)


def get_daily_weight_summary(dos: Optional[str | date | datetime] = None) -> pd.DataFrame:
    """Full weighted summary for a DOS — used by many dashboards"""
    if dos is None:
        dos = date.today()
    if isinstance(dos, (date, datetime)):
        dos = dos.strftime("%Y-%m-%d")
    sql = """
        SELECT dos, location, modality, volume, modality_weight, weighted_units
        FROM dbo.v_Daily_Workload_Weighted
        WHERE dos = ?
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[dos])


# ===================================================================
# BONUS: TOP PERFORMING LOCATION/MODALITY (from modalitylocationtop())
# ===================================================================

def get_top_performing_day_per_category_and_location() -> pd.DataFrame:
    """
    Returns the single highest-volume day for every Location + ProcedureCategory combo
    Used by the \"Modality\\Location Top Day\" text report
    """
    sql = """
        WITH Ranked AS (
            SELECT 
                LocationName,
                ProcedureCategory,
                CAST(ScheduleStartDate AS DATE) AS ScheduleDate,
                SUM(Unit) AS TotalUnits,
                ROW_NUMBER() OVER (
                    PARTITION BY LocationName, ProcedureCategory 
                    ORDER BY SUM(Unit) DESC
                ) AS rn
            FROM DAILY
            GROUP BY LocationName, ProcedureCategory, CAST(ScheduleStartDate AS DATE)
        )
        SELECT LocationName, ProcedureCategory, ScheduleDate, TotalUnits
        FROM Ranked
        WHERE rn = 1
        ORDER BY ProcedureCategory, TotalUnits DESC
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn)

def get_daily_units_for_top(start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
    """
    Fetch all daily units for top day calculation (grouped by date, location, category).
    Optional date range to limit (default: all time).
    """
    sql = """
        SELECT CAST(ScheduleStartDate AS DATE) AS ScheduleStartDate, LocationName, ProcedureCategory, SUM(Unit) AS Unit
        FROM DAILY
    """
    params = []
    if start_date or end_date:
        sql += " WHERE ScheduleStartDate BETWEEN ? AND ?"
        start_date = start_date or datetime.min
        end_date = end_date or datetime.max
        params = [start_date, end_date]
    sql += " GROUP BY CAST(ScheduleStartDate AS DATE), LocationName, ProcedureCategory"
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=params)
        
        
def get_budget_for_month(year: int, month: int) -> pd.DataFrame:
    """Get projected volume for specific month"""
    sql = """
        SELECT Location as LocationName, Modality as ProcedureCategory, Year, Month, ProjectedVolume as Unit
        FROM BUDGET 
        WHERE Year = ? AND Month = ?
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[year, month])

def get_budget_daily_volume(year: int, month: int) -> pd.DataFrame:
    """Get daily projected volume for month"""
    sql = """
        SELECT b.Location as LocationName, b.Modality as ProcedureCategory, b.Year, b.Month, b.ProjectedDailyVolume as Unit, l.Region 
        FROM BUDGET b
        INNER JOIN LOCATIONS l ON b.Location = l.LocationName 
        WHERE b.Year = ? AND b.Month = ?
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[year, month])

def get_budget_mtd(year: int, month: int, businessdays: int) -> pd.DataFrame:
    """Get MTD budget"""
    df = get_budget_daily_volume(year, month)
    df['Unit'] = df['Unit'] * businessdays
    return df

def get_year_budget_proj_daily(year: int) -> pd.DataFrame:
    """Get yearly projected daily budget (using stored proc)"""
    sql = "EXEC getYearBudgetProjDaily @year = ?"
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[year])
        
        
# src/radiology_reports/data/workload.py
# ← Add this function somewhere in the file

def get_budget_daily_volume(year: int, month: int) -> pd.DataFrame:
    """Centralized query for daily projected budget volume"""
    sql = """
        SELECT 
            b.Location as LocationName,
            b.Modality as ProcedureCategory,
            b.Year,
            b.Month,
            b.ProjectedDailyVolume as Unit,
            l.Region
        FROM BUDGET b
        INNER JOIN LOCATIONS l ON b.Location = l.LocationName 
        WHERE b.Year = ? AND b.Month = ?
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[year, month])

def get_units_by_range(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Fetches exam units between a specified start and end date.
    """
    sql = """
        SELECT ScheduleStartDate, LocationName, ProcedureCategory, Unit
        FROM DAILY
        WHERE ScheduleStartDate BETWEEN ? AND ?
    """
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[start_date, end_date])
# ===================================================================
# END OF FILE
# ===================================================================