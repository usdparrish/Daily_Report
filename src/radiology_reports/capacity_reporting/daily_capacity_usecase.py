"""
Daily Capacity Utilization Use Case (Exec-facing)

Purpose:
- Snapshot scheduled volume vs known capacity for ONE DOS
- Identify utilization, gaps, and risk
- Mirrors legacy daily_capacity_forecast.py behavior

Phase 2A:
- Adds completed vs capacity (network level only)
- Preserves exec-safe daily semantics

Important:
- NOT a forecast
- ONE DOS per run
- DOS default handled by CLI (tomorrow)
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Tuple, Set, List

import pandas as pd

from radiology_reports.data.workload import get_scheduled_snapshot
from radiology_reports.data.completed import get_completed_snapshot
from radiology_reports.data.capacity import (
    get_capacity_weighted_90th_by_location,
    get_capacity_weighted_90th_by_modality,
)
from radiology_reports.utils.logger import get_logger

from radiology_reports.capacity_reporting.capacity_models import (
    DailyCapacityResult,
    LocationCapacityResult,
    ModalityCapacityResult,
    NetworkCapacitySummary,
)

logger = get_logger(__name__)


def run_daily_capacity_report(dos: date) -> DailyCapacityResult:
    """
    Run Daily Capacity Utilization Report for a single DOS.
    """

    logger.info("Running Daily Capacity Utilization Report | DOS=%s", dos)

    # ------------------------------------------------------------
    # Load capacity benchmarks (legacy-aligned)
    # ------------------------------------------------------------
    cap_loc: Dict[str, float] = get_capacity_weighted_90th_by_location()
    cap_mod: Dict[Tuple[str, str], float] = get_capacity_weighted_90th_by_modality()

    # ------------------------------------------------------------
    # Load scheduled snapshot (intent)
    # ------------------------------------------------------------
    df_sched = get_scheduled_snapshot(dos)

    # Snapshot metadata
    snapshot_date = None
    if df_sched is not None and not df_sched.empty and "snapshot_date" in df_sched.columns:
        try:
            snapshot_date = df_sched["snapshot_date"].iloc[0]
        except Exception:
            snapshot_date = None

    if df_sched is None or df_sched.empty:
        logger.warning("No scheduled data found for DOS=%s", dos)
        df_sched = pd.DataFrame(
            columns=[
                "location",
                "modality",
                "volume",
                "modality_weight",
                "weighted_units",
            ]
        )

    # ------------------------------------------------------------
    # Aggregate scheduled (legacy behavior)
    # ------------------------------------------------------------
    unknown_modalities: Set[str] = set()
    loc_map: Dict[str, Dict[str, float]] = {}
    modality_rows: List[Tuple[str, str, int, float]] = []

    for _, r in df_sched.iterrows():
        loc = r["location"]
        mod = r["modality"]

        volume = float(r.get("volume") or 0)
        weight = r.get("modality_weight", None)
        weighted_units = r.get("weighted_units", None)

        if weight is None or (isinstance(weight, float) and pd.isna(weight)):
            unknown_modalities.add(mod or "(NULL)")
            w_units = 0.0
        else:
            try:
                w_units = float(weighted_units or 0)
            except Exception:
                w_units = 0.0

        if loc not in loc_map:
            loc_map[loc] = {"exams": 0.0, "weighted": 0.0}

        loc_map[loc]["exams"] += volume
        loc_map[loc]["weighted"] += w_units

        modality_rows.append((loc, mod, int(volume), float(w_units)))

    # ------------------------------------------------------------
    # Build location rollups
    # ------------------------------------------------------------
    location_results: List[LocationCapacityResult] = []

    for loc, vals in loc_map.items():
        exams = int(vals["exams"])
        weighted = round(vals["weighted"], 2)

        cap = cap_loc.get(loc)
        pct = round(weighted / cap, 3) if cap and cap > 0 else None
        gap = round(cap - weighted, 2) if cap and weighted < cap else None

        if cap is None:
            status = "NO CAP"
        elif weighted > cap * 1.05:
            status = "OVER CAPACITY"
        elif weighted >= cap * 0.95:
            status = "AT CAPACITY"
        else:
            status = "UNDER (GAP)"

        location_results.append(
            LocationCapacityResult(
                dos=dos,
                location=loc,
                exams=exams,
                weighted_units=weighted,
                capacity_90th=cap,
                pct_of_capacity=pct,
                gap_units=gap,
                status=status,
            )
        )

    location_results_sorted = sorted(
        location_results,
        key=lambda r: (r.pct_of_capacity or 0.0),
        reverse=True,
    )

    # ------------------------------------------------------------
    # Build modality detail
    # ------------------------------------------------------------
    modality_results: List[ModalityCapacityResult] = []

    for loc, mod, exams, weighted in modality_rows:
        capm = cap_mod.get((loc, mod))
        pct = round(weighted / capm, 3) if capm and capm > 0 else None

        if capm is None:
            status = "NO CAP"
        elif weighted > capm * 1.05:
            status = "OVER CAPACITY"
        elif weighted >= capm * 0.95:
            status = "AT CAPACITY"
        else:
            status = "UNDER (GAP)"

        modality_results.append(
            ModalityCapacityResult(
                dos=dos,
                location=loc,
                modality=mod,
                exams=exams,
                weighted_units=weighted,
                cap_mod=capm,
                pct_of_capacity=pct,
                status=status,
            )
        )

    # ------------------------------------------------------------
    # Network scheduled vs capacity
    # ------------------------------------------------------------
    total_weighted = sum(r.weighted_units for r in location_results_sorted)
    total_capacity = sum(v for v in cap_loc.values() if v is not None)

    scheduled_util_pct = (
        round((total_weighted / total_capacity) * 100, 1)
        if total_capacity
        else 0.0
    )

    sites_over = sum(1 for r in location_results_sorted if r.status == "OVER CAPACITY")
    sites_at = sum(1 for r in location_results_sorted if r.status == "AT CAPACITY")
    sites_under = len(location_results_sorted) - sites_over - sites_at

    # ------------------------------------------------------------
    # Phase 2A: completed vs capacity (network-only)
    # ------------------------------------------------------------
    completed_weighted = None
    completed_util_pct = None
    delta_weighted = None
    delta_pct_points = None

    if dos <= date.today():
        df_completed = get_completed_snapshot(dos)

        if df_completed is not None and not df_completed.empty:
            completed_weighted = round(float(df_completed["weighted_units"].sum()), 2)

            if total_capacity:
                completed_util_pct = round(
                    (completed_weighted / total_capacity) * 100, 1
                )

            delta_weighted = round(completed_weighted - round(total_weighted, 2), 2)
            delta_pct_points = (
                round(completed_util_pct - scheduled_util_pct, 1)
                if completed_util_pct is not None
                else None
            )
        else:
            completed_weighted = 0.0
            completed_util_pct = 0.0
            delta_weighted = round(0.0 - round(total_weighted, 2), 2)
            delta_pct_points = round(0.0 - scheduled_util_pct, 1)

    # ------------------------------------------------------------
    # Build network summary
    # ------------------------------------------------------------
    summary = NetworkCapacitySummary(
        report_date=date.today(),
        start_date=dos,
        end_date=dos,
        total_active_sites=len(location_results_sorted),
        network_scheduled_weighted=round(total_weighted, 2),
        network_capacity_90th=round(total_capacity, 2),
        network_utilization_pct=scheduled_util_pct,
        sites_over=sites_over,
        sites_at=sites_at,
        sites_under=sites_under,
        network_completed_weighted=completed_weighted,
        network_completed_utilization_pct=completed_util_pct,
        execution_delta_weighted=delta_weighted,
        execution_delta_pct_points=delta_pct_points,
    )

    # ------------------------------------------------------------
    # Final report object
    # ------------------------------------------------------------
    return DailyCapacityResult(
        summary=summary,
        locations=location_results_sorted,
        modalities=modality_results,
        unknown_modalities=unknown_modalities,
        snapshot_date=snapshot_date,
    )
