"""
Daily Capacity Utilization Use Case (Exec-facing)

Purpose:
- Snapshot scheduled volume vs known capacity for ONE DOS
- Identify utilization, gaps, and risk
- Mirrors legacy daily_capacity_forecast.py behavior

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

    # ------------------------------------------------------------------
    # Load capacity benchmarks (same sources as legacy)
    # ------------------------------------------------------------------
    cap_loc: Dict[str, float] = get_capacity_weighted_90th_by_location()
    cap_mod: Dict[Tuple[str, str], float] = get_capacity_weighted_90th_by_modality()

    # ------------------------------------------------------------------
    # Load scheduled snapshot for DOS
    # ------------------------------------------------------------------
    df = get_scheduled_snapshot(dos)

    if df is None or df.empty:
        logger.warning("No scheduled data found for DOS=%s", dos)
        df = pd.DataFrame(
            columns=[
                "location",
                "modality",
                "volume",
                "modality_weight",
                "weighted_units",
            ]
        )

    # ------------------------------------------------------------------
    # Aggregation (verbatim legacy behavior)
    # ------------------------------------------------------------------
    unknown_modalities: Set[str] = set()

    loc_map: Dict[str, Dict[str, float]] = {}
    modality_rows: List[Tuple[str, str, int, float]] = []

    for _, r in df.iterrows():
        loc = r["location"]
        mod = r["modality"]

        volume = float(r.get("volume") or 0)
        weight = r.get("modality_weight", None)
        weighted_units = r.get("weighted_units", None)

        # Legacy rule: missing weight → unknown modality → weighted = 0
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

        modality_rows.append(
            (
                loc,
                mod,
                int(volume),
                float(w_units),
            )
        )

    # ------------------------------------------------------------------
    # Build Location Rollup (same thresholds & wording)
    # ------------------------------------------------------------------
    location_results: List[LocationCapacityResult] = []

    for loc, vals in loc_map.items():
        exams = int(vals["exams"])
        weighted = round(vals["weighted"], 2)

        cap = cap_loc.get(loc)
        pct = round(weighted / cap, 3) if cap and cap > 0 else None
        gap = round(cap - weighted, 2) if cap and weighted < cap else None

        if cap is None:
            status = "NO CAP"
        else:
            if weighted > cap * 1.05:
                status = "OVER CAPACITY"
            elif weighted >= cap * 0.95:
                status = "AT CAPACITY"
            else:
                status = "UNDER CAPACITY (GAP)"

        location_results.append(
            LocationCapacityResult(
                dos=dos,
                location=loc,
                exams=exams,
                weighted_units=weighted,
                capacity_90th=cap if cap is not None else None,
                pct_of_capacity=pct,
                gap_units=gap,
                status=status,
            )
        )

    # Sort exactly like legacy: by % of capacity DESC
    location_results_sorted = sorted(
        location_results,
        key=lambda r: (r.pct_of_capacity or 0.0),
        reverse=True,
    )

    # ------------------------------------------------------------------
    # Build Modality Detail (same thresholds & wording)
    # ------------------------------------------------------------------
    modality_results: List[ModalityCapacityResult] = []

    for loc, mod, exams, weighted in modality_rows:
        capm = cap_mod.get((loc, mod))
        pct = round(weighted / capm, 3) if capm and capm > 0 else None

        if capm is None:
            status = "NO CAP"
        else:
            if weighted > capm * 1.05:
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
                cap_mod=capm if capm is not None else None,
                pct_of_capacity=pct,
                status=status,
            )
        )

    # ------------------------------------------------------------------
    # Network Summary (legacy semantics)
    # ------------------------------------------------------------------
    total_weighted = sum(r.weighted_units for r in location_results_sorted)
    total_capacity = sum(v for v in cap_loc.values() if v is not None)

    network_util_pct = (
        round((total_weighted / total_capacity) * 100, 1)
        if total_capacity
        else 0.0
    )

    sites_over = sum(1 for r in location_results_sorted if r.status == "OVER CAPACITY")
    sites_at = sum(1 for r in location_results_sorted if r.status == "AT CAPACITY")
    sites_under = len(location_results_sorted) - sites_over - sites_at

    summary = NetworkCapacitySummary(
        report_date=date.today(),
        start_date=dos,
        end_date=dos,
        total_active_sites=len(location_results_sorted),
        network_scheduled_weighted=round(total_weighted, 2),
        network_capacity_90th=round(total_capacity, 2),
        network_utilization_pct=network_util_pct,
        sites_over=sites_over,
        sites_at=sites_at,
        sites_under=sites_under,
    )

    # ------------------------------------------------------------------
    # Final Report Object
    # ------------------------------------------------------------------
    return DailyCapacityResult(
        summary=summary,
        locations=location_results_sorted,
        modalities=modality_results,
        unknown_modalities=unknown_modalities,
    )
