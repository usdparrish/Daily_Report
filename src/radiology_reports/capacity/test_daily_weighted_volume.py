#!/usr/bin/env python

import argparse
from datetime import date
from typing import Optional

from sqlalchemy import create_engine, text


# ---------------------------------------------------------
# Build SQLAlchemy engine
# ---------------------------------------------------------
def build_engine() -> "Engine":
    connection_url = (
        "mssql+pyodbc://@phiSQL1.rrc.center/RRC_Daily_Report"
        "?driver=ODBC+Driver+17+for+SQL+Server"
        "&trusted_connection=yes"
    )
    return create_engine(connection_url, fast_executemany=True)


# ---------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily weighted workload by active RRC location."
    )
    parser.add_argument("--date", "-d", help="DOS (YYYY-MM-DD). Defaults to today.")

    parser.add_argument(
        "--detail",
        action="store_true",
        help="Show per-location / per-modality detail instead of only location rollup.",
    )
    return parser.parse_args()


def resolve_date(arg: Optional[str]) -> str:
    if arg:
        return arg
    return date.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------
# Simple table printer
# ---------------------------------------------------------
def print_table(rows, headers):
    rows = list(rows)
    widths = [len(h) for h in headers]

    for row in rows:
        for i, col in enumerate(row):
            widths[i] = max(widths[i], len(str(col)))

    def fmt_row(values):
        return "  ".join(str(v).ljust(widths[i]) for i, v in enumerate(values))

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))

    for row in rows:
        print(fmt_row(row))


# ---------------------------------------------------------
# Main logic
# ---------------------------------------------------------
def main():
    args = parse_args()
    target_date = resolve_date(args.date)

    engine = build_engine()

    # ------------------------------
    # DETAIL QUERY — optional
    # ------------------------------
    detail_sql = text(
        """
        SELECT
            w.dos,
            w.location,
            w.modality,
            SUM(w.volume) AS total_exams,
            SUM(w.weighted_units) AS total_weighted_units,
            CAST(
                SUM(w.weighted_units) / NULLIF(SUM(w.volume), 0)
                AS DECIMAL(5,2)
            ) AS weighted_units_per_exam
        FROM dbo.v_Daily_Workload_Weighted w
        JOIN dbo.v_Active_Locations a ON w.location = a.LocationName
        WHERE w.dos = :dos
        GROUP BY w.dos, w.location, w.modality
        ORDER BY w.location, w.modality;
        """
    )

    # ------------------------------
    # LOCATION ROLLUP — default output
    # ------------------------------
    rollup_sql = text(
        """
        SELECT
            w.dos,
            w.location,
            SUM(w.volume) AS total_exams,
            SUM(w.weighted_units) AS total_weighted_units,
            CAST(
                SUM(w.weighted_units) / NULLIF(SUM(w.volume), 0)
                AS DECIMAL(5,2)
            ) AS weighted_units_per_exam
        FROM dbo.v_Daily_Workload_Weighted w
        JOIN dbo.LOCATIONS l
          ON w.location = l.LocationName
         AND ISNULL(l.Active,1) = 1
        WHERE w.dos = :dos
        GROUP BY w.dos, w.location
        ORDER BY w.location;
        """
    )

    with engine.connect() as conn:

        # ----------------------------------------
        # OPTIONAL DETAIL
        # ----------------------------------------
        if args.detail:
            print(f"\n=== Per-location / modality detail for DOS {target_date} ===\n")
            detail_rows = list(conn.execute(detail_sql, {"dos": target_date}))

            if detail_rows:
                print_table(
                    detail_rows,
                    headers=[
                        "dos",
                        "location",
                        "modality",
                        "total_exams",
                        "total_weighted_units",
                        "weighted_units_per_exam",
                    ],
                )
            else:
                print("No detail rows returned.")

        # ----------------------------------------
        # ALWAYS SHOW ROLLUP
        # ----------------------------------------
        print(f"\n=== Location rollup for DOS {target_date} ===\n")
        rollup_rows = list(conn.execute(rollup_sql, {"dos": target_date}))

        if rollup_rows:
            print_table(
                rollup_rows,
                headers=[
                    "dos",
                    "location",
                    "total_exams",
                    "total_weighted_units",
                    "weighted_units_per_exam",
                ],
            )
        else:
            print("No rollup rows returned.")


if __name__ == "__main__":
    main()
