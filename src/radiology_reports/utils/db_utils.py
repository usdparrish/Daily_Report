# utils/db.py
import os
import pyodbc
from datetime import date
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

def get_connection() -> pyodbc.Connection:
    """Return a trusted Windows auth connection to the reporting DB."""
    conn_str = (
        f"DRIVER={os.getenv('DB_DRIVER')};"
        f"SERVER={os.getenv('DB_SERVER')};"
        f"DATABASE={os.getenv('DB_DATABASE')};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str, autocommit=True)

def load_current_weights(cursor) -> Dict[str, float]:
    """
    Load active modality weights from governance table.
    Normalizes modality names for matching.
    """
    today = date.today()
    sql = """
        SELECT modality, weight
        FROM dbo.Modality_Weight_Governance
        WHERE effective_start <= ?
          AND (effective_end IS NULL OR effective_end > ?)
    """
    cursor.execute(sql, (today, today))
    weights = {}
    for row in cursor.fetchall():
        mod_raw = row[0].strip()
        mod_key = mod_raw.upper().replace(" ", "").replace("-", "")
        weights[mod_key] = float(row[1])
    return weights