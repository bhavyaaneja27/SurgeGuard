"""
Demand & Supply Baseline Forecasting Service.
Estimates expected normal demand and supply baselines by zone and time.

Implementation approach (Phase 2):
  - Trains a lookup table of mean demand and supply for each (zone_id, hour, day_of_week)
    from normal_marketplace scenario CSV files.
  - Falls back to zone-level mean if a cell is missing (sparse data).
  - Exposes compute_residuals() to enrich feature vectors with expected vs. observed deltas.

No ML model needed for a transparent rule-based baseline — the lookup table IS the model.
This keeps the forecasting step auditable and fast for streaming step-by-step scoring.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger


def _make_ds_dict() -> Dict[str, List[float]]:
    return {"demand": [], "supply": []}


def _make_inner_defaultdict() -> Dict[Tuple[int, int], Dict[str, List[float]]]:
    return defaultdict(_make_ds_dict)


class BaselineForecaster:
    """
    Computes expected demand and expected supply baselines:
    - Demand baseline: zone/hour/day-of-week mean from normal_marketplace data
    - Supply baseline: same conditioning

    Usage:
        forecaster = BaselineForecaster()
        forecaster.fit_from_csv_dir("data/synthetic")
        expected_demand, expected_supply = forecaster.predict_baseline("zone_midtown_core", 18, 0)
    """

    def __init__(self):
        # Nested dict: {zone_id: {(hour, dow): {"demand": [values], "supply": [values]}}}
        self._accumulator: Dict[str, Dict[Tuple[int, int], Dict[str, List[float]]]] = \
            defaultdict(_make_inner_defaultdict)

        # Compiled lookup after fit(): {zone_id: {(hour, dow): (mean_demand, mean_supply)}}
        self._lookup: Dict[str, Dict[Tuple[int, int], Tuple[float, float]]] = {}

        # Zone-level fallbacks: {zone_id: (mean_demand, mean_supply)}
        self._zone_fallback: Dict[str, Tuple[float, float]] = {}

        self._fitted = False
        logger.info("Initialized BaselineForecaster (Phase 2)")

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit_from_records(self, records: List[Dict[str, Any]]) -> "BaselineForecaster":
        """
        Accumulate baseline statistics from a list of step records.
        Only records with scenario_type == 'normal_marketplace' contribute.
        Call compile() after all records are ingested.
        """
        for rec in records:
            if rec.get("scenario_type") != "normal_marketplace":
                continue
            ts_str = rec.get("timestamp", "")
            hour, dow = _parse_hour_dow(ts_str)
            zone = str(rec.get("zone_id", "unknown"))
            demand = float(rec.get("ride_requests", 0))
            supply = float(rec.get("available_drivers", 0))
            self._accumulator[zone][(hour, dow)]["demand"].append(demand)
            self._accumulator[zone][(hour, dow)]["supply"].append(supply)
        return self

    def fit_from_csv_dir(self, csv_dir: str) -> "BaselineForecaster":
        """
        Scan csv_dir for all *normal_marketplace*.csv files and fit from them.
        """
        if not os.path.isdir(csv_dir):
            logger.warning(f"BaselineForecaster: directory not found: {csv_dir}")
            return self

        found = 0
        for fname in os.listdir(csv_dir):
            if "normal_marketplace" in fname and fname.endswith(".csv"):
                fpath = os.path.join(csv_dir, fname)
                records = _read_csv_records(fpath)
                self.fit_from_records(records)
                found += 1
                logger.info(f"BaselineForecaster: loaded {len(records)} records from {fname}")

        if found == 0:
            logger.warning("BaselineForecaster: no normal_marketplace CSV files found; using synthetic zone defaults")
            self._use_synthetic_defaults()

        self.compile()
        return self

    def compile(self) -> None:
        """Compute mean lookup tables from accumulated data."""
        self._lookup = {}
        self._zone_fallback = {}

        for zone, cell_map in self._accumulator.items():
            self._lookup[zone] = {}
            all_demand: List[float] = []
            all_supply: List[float] = []

            for (hour, dow), arrays in cell_map.items():
                d_vals = arrays["demand"]
                s_vals = arrays["supply"]
                if d_vals:
                    mean_d = sum(d_vals) / len(d_vals)
                    mean_s = sum(s_vals) / len(s_vals) if s_vals else mean_d
                    self._lookup[zone][(hour, dow)] = (mean_d, mean_s)
                    all_demand.extend(d_vals)
                    all_supply.extend(s_vals)

            if all_demand:
                self._zone_fallback[zone] = (
                    sum(all_demand) / len(all_demand),
                    sum(all_supply) / len(all_supply),
                )

        self._fitted = True
        n_cells = sum(len(v) for v in self._lookup.values())
        logger.info(
            f"BaselineForecaster compiled: {len(self._lookup)} zones, {n_cells} lookup cells"
        )

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_baseline(self, zone_id: str, hour: int, day_of_week: int) -> Tuple[float, float]:
        """
        Returns (expected_demand, expected_supply) for the given zone/time slot.
        Falls back to zone mean, then to hardcoded synthetic zone defaults.
        """
        if not self._fitted:
            raise RuntimeError("BaselineForecaster must be fitted before calling predict_baseline()")

        key = (int(hour) % 24, int(day_of_week) % 7)

        # 1. Exact cell lookup
        zone_table = self._lookup.get(zone_id)
        if zone_table:
            result = zone_table.get(key)
            if result:
                return result

        # 2. Zone-level fallback
        fallback = self._zone_fallback.get(zone_id)
        if fallback:
            return fallback

        # 3. Hardcoded synthetic zone defaults (from ZONE_BASELINES in data_generator)
        return _ZONE_DEFAULTS.get(zone_id, (100.0, 110.0))

    def compute_residuals(
        self,
        zone_id: str,
        hour: int,
        day_of_week: int,
        observed_demand: float,
        observed_supply: float,
    ) -> Dict[str, float]:
        """
        Returns {demand_residual_pct, supply_residual_pct, supply_residual_abs}
        comparing observed vs. expected baseline.
        """
        exp_demand, exp_supply = self.predict_baseline(zone_id, hour, day_of_week)

        demand_residual_pct = (observed_demand - exp_demand) / max(exp_demand, 1.0)
        supply_residual_pct = (observed_supply - exp_supply) / max(exp_supply, 1.0)
        supply_residual_abs = observed_supply - exp_supply

        return {
            "expected_demand": round(exp_demand, 2),
            "expected_supply": round(exp_supply, 2),
            "demand_residual_pct": round(demand_residual_pct, 4),
            "supply_residual_pct": round(supply_residual_pct, 4),
            "supply_residual_abs": round(supply_residual_abs, 2),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _use_synthetic_defaults(self) -> None:
        """Seed accumulators with zone default values so compile() produces valid lookups."""
        for zone, (base_d, base_s) in _ZONE_DEFAULTS.items():
            for hour in range(24):
                for dow in range(7):
                    self._accumulator[zone][(hour, dow)]["demand"].append(base_d)
                    self._accumulator[zone][(hour, dow)]["supply"].append(base_s)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

# Hardcoded defaults matching ZONE_BASELINES in data_generator.py
_ZONE_DEFAULTS: Dict[str, Tuple[float, float]] = {
    "zone_midtown_core": (120.0, 135.0),
    "zone_downtown_financial": (95.0, 110.0),
    "zone_airport_terminal": (80.0, 90.0),
    "zone_uptown_residential": (50.0, 60.0),
}


def _parse_hour_dow(timestamp_str: str) -> Tuple[int, int]:
    """Parse ISO timestamp string into (hour, day_of_week). Returns (0, 0) on failure."""
    try:
        from datetime import datetime
        # Handle both naive and offset-aware ISO strings
        ts = timestamp_str.replace("+00:00", "").replace("Z", "")
        dt = datetime.fromisoformat(ts)
        return dt.hour, dt.weekday()  # Monday=0, Sunday=6
    except Exception:
        return 0, 0


def _read_csv_records(filepath: str) -> List[Dict[str, str]]:
    """Read all rows from a CSV file as dicts."""
    records = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
    except Exception as exc:
        logger.warning(f"Could not read CSV {filepath}: {exc}")
    return records


# Module-level singleton (lazy; fit separately)
baseline_forecaster = BaselineForecaster()

