"""
Capacity data access layer.

IMPORTANT:
This matches the ORIGINAL scripts you provided in src.zip:
- dbo.v_Capacity_Model (location capacity)
- dbo.v_Modality_Capacity_Model (modality capacity)
"""

from __future__ import annotations

from typing import Dict, Tuple
import pandas as pd

from radiology_reports.data.workload import get_connection


def get_capacity_weighted_90th_by_location() -> Dict[str, float]:
    """
    Original source: dbo.v_Capacity_Model

    Expected columns:
      - location
      - capacity_weighted_90th
    """
    sql = """
        SELECT location, capacity_weighted_90th
        FROM dbo.v_Capacity_Model
    """
    with get_connection() as conn:
        df = pd.read_sql(sql, conn)

    # Match original behavior: dict lookup by location
    return {
        str(row["location"]): float(row["capacity_weighted_90th"])
        for _, row in df.iterrows()
        if row["location"] is not None and row["capacity_weighted_90th"] is not None
    }


def get_capacity_weighted_90th_by_modality() -> Dict[Tuple[str, str], float]:
    """
    Original source: dbo.v_Modality_Capacity_Model

    Expected columns:
      - location
      - modality
      - capacity_weighted_90th_modality
    """
    sql = """
        SELECT location, modality, capacity_weighted_90th_modality
        FROM dbo.v_Modality_Capacity_Model
    """
    with get_connection() as conn:
        df = pd.read_sql(sql, conn)

    return {
        (str(row["location"]), str(row["modality"])): float(row["capacity_weighted_90th_modality"])
        for _, row in df.iterrows()
        if row["location"] is not None
        and row["modality"] is not None
        and row["capacity_weighted_90th_modality"] is not None
    }
