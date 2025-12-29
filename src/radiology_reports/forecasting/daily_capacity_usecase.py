from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple, Set
import pandas as pd

from radiology_reports.data.workload import get_scheduled_snapshot
from radiology_reports.data.capacity import (
    get_capacity_weighted_90th_by_location,
    get_capacity_weighted_90th_by_modality,
)
from radiology_reports.utils.logger import get_logger

from radiology_reports.forecasting.capacity_models import (
    DailyCapacityResult,
    LocationCapacityResult,
    ModalityCapacityResult,
    NetworkCapacitySummary,
)

logger = get_logger(__name__)


def _parse_start_date(start_date: Optional[str]) -> date:
    if start_date:
        return datetime.strptime(start_date, "%Y-%m-%d").date()
    return date.today()


def run_daily_capacity_forecast(
    start_date: Optional[str],
    days: int = 30,
) -> List[DailyCapacityResult]:
    """
    Produces the SAME dataset the original daily_capacity_forecast.py produced:
    - Multi-day rollup start_date -> end_date
    - Location rollup table
    - Modality detail table
    - Unknown modalities tracking
    """
    start = _parse_start_date(start_date)
    end = start + timedelta(days=days - 1)

    logger.info(
        "Running Daily Capacity Forecast | start_date=%s | days=%s",
        start,
        days,
    )

    cap_loc: Dict[str, float] = get_capacity_weighted_90th_by_location()
    cap_mod: Dict[Tuple[str, str], float] = get_capacity_weighted_90th_by_modality()

    unknown_modalities: Set[str] = set()

    # Aggregate across date range (same behavior as original)
    loc_map: Dict[Tuple[date, str], Dict[str, float]] = {}
    detail_rows: List[Tuple[date, str, str, int, float]] = []
    total_scheduled_weighted = 0.0

    cur = start
    while cur <= end:
        df = get_scheduled_snapshot(cur)  # accepts date per your current workload layer
        if df is None or df.empty:
            cur += timedelta(days=1)
            continue

        # expected columns: location, modality, volume, modality_weight, weighted_units
        for _, r in df.iterrows():
            loc = r["location"]
            mod = r["modality"]
            vol = float(r.get("volume") or 0)

            weight = r.get("modality_weight", None)
            w_units = r.get("weighted_units", None)

            # Preserve original behavior: missing weight => unknown modality => weighted=0
            if weight is None or (isinstance(weight, float) and pd.isna(weight)):
                unknown_modalities.add(mod or "(NULL)")
                w_units_f = 0.0
            else:
                try:
                    w_units_f = float(w_units or 0)
                except Exception:
                    w_units_f = 0.0

            key = (cur, loc)
            if key not in loc_map:
                loc_map[key] = {"volume": 0.0, "weighted_units": 0.0}
            loc_map[key]["volume"] += vol
            loc_map[key]["weighted_units"] += w_units_f

            total_scheduled_weighted += w_units_f

            # modality detail list (same behavior as original)
            try:
                vol_i = int(vol)
            except Exception:
                vol_i = 0
            detail_rows.append((cur, loc, mod, vol_i, float(w_units_f)))

        cur += timedelta(days=1)

    # Build location output rows (same structure + status thresholds as original)
    loc_rows: List[LocationCapacityResult] = []
    for (dos, loc), vals in sorted(loc_map.items(), key=lambda x: (x[0][0], x[0][1])):
        exams = int(vals["volume"])
        weighted = round(float(vals["weighted_units"]), 2)

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

        loc_rows.append(
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

    # Match original sort intent: by DOS then pct desc (reverse=True)
    loc_rows_sorted = sorted(
        loc_rows,
        key=lambda r: (r.dos, (r.pct_of_capacity or 0.0)),
        reverse=True,
    )

    # Modality output rows (same structure + thresholds as original)
    mod_rows: List[ModalityCapacityResult] = []
    for dos, loc, mod, exams, weighted in detail_rows:
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

        mod_rows.append(
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

    # Network summary (same behavior as original)
    total_capacity = sum(v for v in cap_loc.values() if v is not None)
    network_util_pct = round((total_scheduled_weighted / total_capacity) * 100, 1) if total_capacity else 0.0

    sites_over = sum(1 for r in loc_rows if r.status == "OVER CAPACITY")
    sites_at = sum(1 for r in loc_rows if "AT CAPACITY" in r.status)
    sites_under = len(loc_rows) - sites_over - sites_at

    summary = NetworkCapacitySummary(
        report_date=date.today(),
        start_date=start,
        end_date=end,
        total_active_sites=len(loc_rows),
        network_scheduled_weighted=float(round(total_scheduled_weighted, 2)),
        network_capacity_90th=float(round(total_capacity, 2)),
        network_utilization_pct=float(network_util_pct),
        sites_over=sites_over,
        sites_at=sites_at,
        sites_under=sites_under,
    )

    return [
        DailyCapacityResult(
            summary=summary,
            locations=loc_rows_sorted,
            modalities=mod_rows,
            unknown_modalities=unknown_modalities,
        )
    ]
