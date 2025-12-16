# rrc/services/capacity.py

"""
Capacity logic service.

Takes in workload + scheduled + capacity DataFrames
and produces unified per-location analytics:

    - scheduled weighted units
    - completed weighted units
    - capacity weighted units
    - pct scheduled of capacity
    - pct completed of capacity
    - delta scheduled -> completed
    - delta completed -> capacity
    - status
"""

import pandas as pd


def compute_capacity_summary(
    scheduled_df: pd.DataFrame,
    completed_df: pd.DataFrame,
    capacity_df: pd.DataFrame
) -> pd.DataFrame:

    # ---------------------------------------------------------
    # Aggregate scheduled weighted units per location
    # ---------------------------------------------------------
    sched = (
        scheduled_df
        .groupby("location")["weighted_units"]
        .sum()
        .rename("scheduled_wu")
    )

    # ---------------------------------------------------------
    # Aggregate completed weighted units
    # ---------------------------------------------------------
    comp = (
        completed_df
        .groupby("location")["weighted_units"]
        .sum()
        .rename("completed_wu")
    )

    # ---------------------------------------------------------
    # Load capacity (already filtered to active sites)
    # ---------------------------------------------------------
    cap = capacity_df.set_index("location")["capacity_weighted_90th"]
    cap.name = "capacity_wu"

    # ---------------------------------------------------------
    # Join all 3
    # ---------------------------------------------------------
    df = pd.concat([sched, comp, cap], axis=1).fillna(0)

    # % of capacity (safe division: avoid inf / NaN when capacity_wu == 0)
    df["scheduled_pct"] = (df["scheduled_wu"] / df["capacity_wu"] * 100).where(df["capacity_wu"] > 0, 0).round(1)
    df["completed_pct"] = (df["completed_wu"] / df["capacity_wu"] * 100).where(df["capacity_wu"] > 0, 0).round(1)

    # deltas
    df["delta_sched_comp"] = (df["scheduled_wu"] - df["completed_wu"]).round(2)
    df["delta_comp_cap"] = (df["completed_wu"] - df["capacity_wu"]).round(2)

    # status classification
    def classify(row):
        if row["capacity_wu"] == 0:
            return "NO CAP"
        ratio = row["completed_wu"] / row["capacity_wu"]
        if ratio > 1.05:
            return "OVER CAPACITY"
        if ratio >= 0.95:
            return "AT CAPACITY"
        return "UNDER CAPACITY"

    df["status"] = df.apply(classify, axis=1)

    return df.reset_index()
