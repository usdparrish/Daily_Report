import pandas as pd
import pyodbc
from datetime import date

# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=YourServerName;"
        "DATABASE=RRC_Daily_Report;"
        "Trusted_Connection=yes;"
    )


# ============================================================
# LOAD DATASETS
# ============================================================

def load_rrc_locations(conn):
    """Load active RRC locations from the enterprise view."""
    query = """
        SELECT LocationName FROM dbo.v_Active_Locations;
    """
    return pd.read_sql(query, conn)


def load_daily_weighted_summary(conn, target_date=None):
    """
    Load from the enterprise workload view (already filtered to active locations).
    """
    base_query = """
        SELECT
            dos,
            location,
            modality,
            volume,
            modality_weight,
            weighted_units
        FROM dbo.v_Daily_Workload_Weighted
    """

    if target_date:
        base_query += " WHERE dos = ?"

    return pd.read_sql(base_query, conn, params=[target_date] if target_date else None)


# ============================================================
# MAIN ANALYTIC FUNCTION
# ============================================================

def run_daily_weight_analysis(target_date=None):
    conn = get_connection()

    # Load weighted dataset (already filtered to active locations)
    df = load_daily_weighted_summary(conn, target_date)

    if df.empty:
        print("No data found for the selected date.")
        conn.close()
        return

    # =======================================================
    # BUILD SUMMARIES
    # =======================================================

    # --- 1. Total by location ---
    by_location = (
        df.groupby("location")
        .agg(
            total_exams=("volume", "sum"),
            total_weighted=("weighted_units", "sum"),
            avg_weight_per_exam=("weighted_units", lambda x: x.sum() / df.loc[x.index, "volume"].sum())
        )
        .reset_index()
        .sort_values("total_weighted", ascending=False)
    )

    # --- 2. Total by modality ---
    by_modality = (
        df.groupby("modality")
        .agg(
            total_exams=("volume", "sum"),
            total_weighted=("weighted_units", "sum"),
            weight_value=("modality_weight", "first")
        )
        .reset_index()
        .sort_values("total_weighted", ascending=False)
    )

    # --- 3. Enterprise daily totals ---
    daily_totals = {
        "Total Exams": int(df["volume"].sum()),
        "Total Weighted Units": float(df["weighted_units"].sum()),
        "Weighted Units Per Exam": round(df["weighted_units"].sum() / df["volume"].sum(), 2)
    }

    conn.close()

    # Return all 3 structures
    return daily_totals, by_location, by_modality


# ============================================================
# RUN TEST
# ============================================================

if __name__ == "__main__":
    target_dos = date(2025, 12, 9)

    totals, loc_summary, mod_summary = run_daily_weight_analysis(target_dos)

    print("\n===== ENTERPRISE DAILY TOTALS =====")
    print(totals)

    print("\n===== WEIGHTED BY LOCATION =====")
    print(loc_summary)

    print("\n===== WEIGHTED BY MODALITY =====")
    print(mod_summary)
