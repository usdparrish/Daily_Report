from __future__ import annotations

from datetime import date, datetime
import pandas as pd

from radiology_reports.data.workload import get_connection


def get_completed_snapshot(dos: str | date | datetime) -> pd.DataFrame:
    """
    Completed exams snapshot for a single DOS.

    Source:
      dbo.DAILY (completed exams)

    Output columns (match scheduled snapshot shape):
      - location
      - modality
      - volume
      - modality_weight
      - weighted_units
    """

    if isinstance(dos, (date, datetime)):
        dos = dos.strftime("%Y-%m-%d")

    sql = """
        SELECT
            d.LocationName AS location,
            d.ProcedureCategory AS modality,

            -- completed exam count
            COUNT(*) AS volume,

            -- governed modality weight
            MAX(w.weight) AS modality_weight,

            -- completed weighted units
            CAST(COUNT(*) * MAX(w.weight) AS DECIMAL(10,2)) AS weighted_units

        FROM dbo.DAILY d
        JOIN dbo.v_Active_Locations a
            ON d.LocationName = a.LocationName

        JOIN dbo.Modality_Weight_Governance w
            ON UPPER(LTRIM(RTRIM(w.modality))) =
               UPPER(LTRIM(RTRIM(d.ProcedureCategory)))
           AND d.ScheduleStartDate BETWEEN w.effective_start
                                       AND ISNULL(w.effective_end, '9999-12-31')

        WHERE d.ScheduleStartDate = ?

        GROUP BY
            d.LocationName,
            d.ProcedureCategory

        ORDER BY
            d.LocationName,
            d.ProcedureCategory;
    """

    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=[dos])
