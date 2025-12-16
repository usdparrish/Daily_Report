#!/usr/bin/env python3
"""
scheduled_capacity_check.py

Reads:
  - v_Scheduled_Current (latest scheduled snapshot)
  - dbo.Modality_Weight_Governance (active weights as-of the report date)
  - v_Capacity_Model (location-level capacity)
  - v_Modality_Capacity_Model (modality-level capacity)

Outputs:
  - location rollup (dos, location, exams, weighted_units, capacity_90th, pct_of_capacity, gap, status)
  - modality detail (dos, location, modality, exams, weighted_units, capacity_90th_modality, pct, status)

Notes:
  - Uses Windows Trusted Connection via pyodbc.
  - No zero-rows are synthesized; only modalities present in the snapshot are shown.
"""

import argparse
from collections import defaultdict
from datetime import date, timedelta, datetime
import pyodbc
import sys
import math

# -------------------------
# DB connection
# -------------------------
def get_conn():
    return pyodbc.connect(
        r"DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=phiSQL1.rrc.center;"
        r"DATABASE=RRC_Daily_Report;"
        r"Trusted_Connection=yes;",
        autocommit=True,
    )

# -------------------------
# CLI
# -------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Look-ahead weighted scheduled volumes vs capacity")
    p.add_argument("--start-date", "-s", help="Start DOS (YYYY-MM-DD). Defaults to today.", required=False)
    p.add_argument("--days", "-n", type=int, default=30, help="Number of days to include (default 30)")
    return p.parse_args()

# -------------------------
# Utilities
# -------------------------
def rows_to_dicts(cursor, rows):
    cols = [c[0].lower() for c in cursor.description]
    dicts = []
    for r in rows:
        d = {cols[i]: r[i] for i in range(len(cols))}
        dicts.append(d)
    return dicts

def print_table(rows, headers, max_rows=None):
    rows = list(rows)
    if max_rows is not None and len(rows) > max_rows:
        show_rows = rows[:max_rows]
    else:
        show_rows = rows

    widths = [len(h) for h in headers]
    for row in show_rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))

    def fmt_row(r):
        return "  ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers)))

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in show_rows:
        print(fmt_row(row))
    if max_rows is not None and len(rows) > max_rows:
        print(f"... ({len(rows) - max_rows} more rows omitted) ...")

# -------------------------
# Fetch active weights from Modality_Weight_Governance for a given effective date
# -------------------------
def fetch_weights(cursor, effective_date):
    """
    Returns a dict mapping normalized modality text -> float(weight).
    Uses effective_date to select the currently effective weights.
    """
    # We'll fetch rows that are effective for the date (effective_start <= date AND (effective_end IS NULL OR >= date))
    sql = """
        SELECT modality, weight
        FROM dbo.Modality_Weight_Governance
        WHERE effective_start <= ?
          AND (effective_end IS NULL OR effective_end >= ?)
    """
    cursor.execute(sql, (effective_date, effective_date))
    rows = cursor.fetchall()
    weights = {}
    for r in rows:
        mod = (r[0] or "").strip().upper()
        try:
            w = float(r[1])
        except Exception:
            w = None
        if mod:
            weights[mod] = w
    return weights

# -------------------------
# Main logic
# -------------------------
def main():
    args = parse_args()
    start = args.start_date or date.today().strftime("%Y-%m-%d")
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
    except Exception:
        print("Invalid --start-date format; expected YYYY-MM-DD")
        sys.exit(1)
    end_date = start_date + timedelta(days=args.days - 1)

    conn = get_conn()
    cursor = conn.cursor()

    # 0) Determine weight effective date: use start_date (reporting perspective)
    effective_date = start_date

    # Fetch weights from governance table
    try:
        weights = fetch_weights(cursor, effective_date)
    except Exception as e:
        print("ERROR fetching modality weights from Modality_Weight_Governance:", e)
        weights = {}

    # 1) Pull scheduled rows from v_Scheduled_Current (latest snapshot)
    scheduled_sql = """
        SELECT s.dos, s.location, s.modality, SUM(s.volume) AS volume
        FROM dbo.v_Scheduled_Current s
        JOIN dbo.LOCATIONS l
          ON s.location = l.LocationName
         AND ISNULL(l.Active, 1) = 1
        WHERE s.dos BETWEEN ? AND ?
        GROUP BY s.dos, s.location, s.modality
        ORDER BY s.dos, s.location, s.modality;
    """
    try:
        cursor.execute(scheduled_sql, (start_date, end_date))
    except pyodbc.ProgrammingError as e:
        print("\nERROR: v_Scheduled_Current or dbo.LOCATIONS not found or invalid permissions.")
        print("SQL error:", e)
        sys.exit(1)

    scheduled_rows = rows_to_dicts(cursor, cursor.fetchall())
    if not scheduled_rows:
        print(f"No scheduled rows found in v_Scheduled_Current between {start_date} and {end_date}.")
        return

    # 2) Compute weighted units in Python and aggregate
    unknown_modalities = set()
    detail_map = defaultdict(lambda: {"volume": 0.0, "weighted_units": 0.0})
    # key = (dos (date), location (str), modality (str))

    for r in scheduled_rows:
        dos = r["dos"].date() if isinstance(r["dos"], datetime) else r["dos"]
        loc = r["location"]
        mod_raw = (r["modality"] or "").strip()
        mod = mod_raw.upper()
        vol = float(r["volume"] or 0)

        weight = weights.get(mod)
        if weight is None:
            # track unknown text (so we can add it to governance). DO NOT silently assume a weight.
            unknown_modalities.add(mod_raw)
            # fallback to 1.0 so we still show numbers rather than crash. We'll call these out at the end.
            weight = 1.0

        weighted = vol * weight

        key = (dos, loc, mod_raw)   # store original formatting for display
        detail_map[key]["volume"] += vol
        detail_map[key]["weighted_units"] += weighted

    # Build a sorted detail list
    detail_list = []
    for (dos, loc, mod), vals in sorted(detail_map.items()):
        detail_list.append((dos.isoformat(), loc, mod, int(vals["volume"]), round(vals["weighted_units"], 2)))

    # 3) Location rollup (by dos+location)
    loc_map = defaultdict(lambda: {"volume": 0.0, "weighted_units": 0.0})
    for (dos, loc, _), vals in detail_map.items():
        loc_map[(dos, loc)]["volume"] += vals["volume"]
        loc_map[(dos, loc)]["weighted_units"] += vals["weighted_units"]

    loc_list = []
    for (dos, loc), vals in sorted(loc_map.items()):
        loc_list.append((dos.isoformat(), loc, int(vals["volume"]), round(vals["weighted_units"], 2)))

    # 4) Read capacity (location-level) from v_Capacity_Model
    cap_loc_sql = "SELECT DISTINCT location, capacity_weighted_90th FROM dbo.v_Capacity_Model;"
    try:
        cursor.execute(cap_loc_sql)
        cap_loc = {r[0]: float(r[1]) if r[1] is not None else None for r in cursor.fetchall()}
    except pyodbc.ProgrammingError:
        print("\nWARNING: v_Capacity_Model not found. Location capacity comparison will be skipped.")
        cap_loc = {}

    # 5) Read modality capacity from v_Modality_Capacity_Model
    cap_mod_sql = "SELECT DISTINCT location, modality, capacity_weighted_90th_modality FROM dbo.v_Modality_Capacity_Model;"
    try:
        cursor.execute(cap_mod_sql)
        cap_mod = {(r[0], r[1]): float(r[2]) if r[2] is not None else None for r in cursor.fetchall()}
    except pyodbc.ProgrammingError:
        print("\nWARNING: v_Modality_Capacity_Model not found. Modality capacity comparison will be skipped.")
        cap_mod = {}

    # 6) Build location-level output with capacity fields (round display values)
    loc_output = []
    for dos_iso, loc, vol, weighted in loc_list:
        cap = cap_loc.get(loc)
        pct = None
        gap = None
        status = "NO CAP" if cap is None else "UNKNOWN"
        if cap and cap > 0:
            pct = round(weighted / cap, 3)
            gap = round(cap - weighted, 2)
            if weighted > cap * 1.05:
                status = "OVER CAPACITY"
            elif weighted >= cap * 0.95:
                status = "AT CAPACITY"
            else:
                status = "UNDER CAPACITY (GAP)"
        # display rounding: capacity_90th and pct as friendly numbers
        display_cap = round(cap, 1) if (cap is not None and not math.isnan(cap)) else None
        display_pct = round(pct, 2) if pct is not None else None
        loc_output.append((dos_iso, loc, vol, round(weighted, 2), display_cap, display_pct, gap, status))

    # 7) Build modality-level output with capacity fields (round display)
    mod_output = []
    for dos_iso, loc, mod, vol, weighted in detail_list:
        capm = cap_mod.get((loc, mod))
        pct = None
        status = "NO CAP" if capm is None else "UNKNOWN"
        if capm and capm > 0:
            pct = round(weighted / capm, 3)
            if weighted > capm * 1.05:
                status = "OVER CAPACITY"
            elif weighted >= capm * 0.95:
                status = "AT CAPACITY"
            else:
                status = "UNDER (GAP)"
        display_capm = round(capm, 1) if (capm is not None and not math.isnan(capm)) else None
        display_pct = round(pct, 2) if pct is not None else None
        mod_output.append((dos_iso, loc, mod, vol, round(weighted, 2), display_capm, display_pct, status))

    # 8) Print summary tables
    print("\n============================================================")
    print(f" SCHEDULED WEIGHTED VOLUME — {start_date.isoformat()} -> {end_date.isoformat()}")
    print(" (latest snapshot from v_Scheduled_Current; active locations only)")
    print("============================================================\n")

    loc_sorted = sorted(loc_output, key=lambda r: (r[0], (r[5] or 0)), reverse=True)
    print("== Location Rollup (dos, location, exams, weighted_units, capacity_90th, pct_of_capacity, gap, status) ==\n")
    print_table(loc_sorted, headers=["dos", "location", "exams", "weighted_units", "capacity_90th", "pct_of_capacity", "gap_units", "status"], max_rows=200)

    print("\n\n== Modality Detail (dos, location, modality, exams, weighted_units, cap_mod, pct_of_capacity, status) ==\n")
    print_table(mod_output, headers=["dos", "location", "modality", "exams", "weighted_units", "cap_mod", "pct_of_capacity", "status"], max_rows=400)

    if unknown_modalities:
        print("\n\nNOTE: Unknown modalities encountered (no governance row found). Default weight=1.0 used for these while flagged:")
        for m in sorted(unknown_modalities):
            print("  -", repr(m))

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
