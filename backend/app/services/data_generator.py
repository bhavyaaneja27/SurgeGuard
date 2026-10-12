"""
Synthetic Marketplace Data Generator Service.
Generates reproducible, realistic, and explicitly labeled time-series data
for ride-hailing demand and driver availability dynamics across four core scenarios:
1. normal_marketplace
2. demand_led_surge
3. natural_shortage
4. unusual_supply_drop

Uses deterministic pseudo-random generators with mathematical shock modeling.
Designed with pure-Python robustness (math + random) and optional Pandas integration.
"""

from datetime import datetime, timedelta, timezone
import math
import random
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.schemas.simulation import ScenarioType

# Optional pandas import with graceful fallback
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False


ZONE_BASELINES: Dict[str, Dict[str, float]] = {
    "zone_midtown_core": {
        "baseline_demand": 120.0,
        "baseline_supply": 135.0,
        "demand_volatility": 6.0,
        "supply_volatility": 4.5,
    },
    "zone_downtown_financial": {
        "baseline_demand": 95.0,
        "baseline_supply": 110.0,
        "demand_volatility": 5.0,
        "supply_volatility": 4.0,
    },
    "zone_airport_terminal": {
        "baseline_demand": 80.0,
        "baseline_supply": 90.0,
        "demand_volatility": 7.0,
        "supply_volatility": 3.5,
    },
    "zone_uptown_residential": {
        "baseline_demand": 50.0,
        "baseline_supply": 60.0,
        "demand_volatility": 4.0,
        "supply_volatility": 3.0,
    },
}

SCENARIO_METADATA: Dict[ScenarioType, Dict[str, str]] = {
    "normal_marketplace": {
        "name": "Normal Marketplace",
        "description": "Ordinary organic fluctuations in ride demand and driver availability near equilibrium.",
        "context_type": "regular_operations",
        "ground_truth_label": "normal",
    },
    "demand_led_surge": {
        "name": "Demand-Led Surge",
        "description": "Sudden sharp increase in passenger requests (e.g., event/concert exit) while supply catches up with a delay.",
        "context_type": "concert_or_event",
        "ground_truth_label": "demand_spike",
    },
    "natural_shortage": {
        "name": "Natural Shortage (Weather Disruption)",
        "description": "Simulated heavy rainfall causing simultaneous demand increase (+35%) and driver supply reduction (-45%).",
        "context_type": "weather_rainstorm",
        "ground_truth_label": "natural_shortage",
    },
    "unusual_supply_drop": {
        "name": "Unusual Supply Drop",
        "description": "Controlled anomaly: driver availability drops precipitously (-60%) while demand remains flat, simulating artificial shortage.",
        "context_type": "unexplained_availability_shock",
        "ground_truth_label": "unusual_supply_drop",
    },
}


class SyntheticDataGenerator:
    """
    Stochastic time-series generator with deterministic seeding.
    Produces valid, bounded records across time steps.
    """

    def __init__(self, default_seed: int = 42):
        self.default_seed = default_seed
        logger.info(f"Initialized SyntheticDataGenerator with default_seed={default_seed}")

    def generate_scenario_records(
        self,
        scenario_type: ScenarioType,
        zone_id: str = "zone_midtown_core",
        duration_minutes: int = 120,
        event_intensity: float = 0.7,
        seed: Optional[int] = None,
        start_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate time-series records for the requested scenario and parameters.
        Guaranteed to be deterministic for identical (scenario_type, zone_id, duration_minutes, event_intensity, seed).
        """
        active_seed = self.default_seed if seed is None else seed
        rng = random.Random(active_seed)

        if zone_id not in ZONE_BASELINES:
            zone_id = "zone_midtown_core"

        zone_cfg = ZONE_BASELINES[zone_id]
        scenario_meta = SCENARIO_METADATA.get(
            scenario_type, SCENARIO_METADATA["normal_marketplace"]
        )

        base_d = zone_cfg["baseline_demand"]
        base_s = zone_cfg["baseline_supply"]
        d_vol = zone_cfg["demand_volatility"]
        s_vol = zone_cfg["supply_volatility"]

        if start_time is None:
            # Fixed reference time for reproducible timestamps
            start_time = datetime(2026, 10, 12, 18, 0, 0, tzinfo=timezone.utc)

        # Event timing windows (typically centered between 25% and 75% of duration)
        t_start = int(duration_minutes * 0.25)
        t_peak = int(duration_minutes * 0.45)
        t_end = int(duration_minutes * 0.75)

        records: List[Dict[str, Any]] = []

        # Autoregressive states for smooth realistic transitions
        curr_demand = base_d
        curr_supply = base_s

        for step in range(duration_minutes):
            current_timestamp = start_time + timedelta(minutes=step)
            step_annotation: Optional[str] = None

            # Calculate scenario-specific shock multipliers
            demand_multiplier = 1.0
            supply_multiplier = 1.0

            if scenario_type == "normal_marketplace":
                # Subtle cyclic drift: sin wave over duration + Gaussian noise
                drift = math.sin((step / duration_minutes) * 2 * math.pi) * 0.08
                demand_multiplier = 1.0 + drift
                supply_multiplier = 1.0 + drift * 0.85
                if step == 0:
                    step_annotation = "Marketplace operating under normal equilibrium conditions"

            elif scenario_type == "demand_led_surge":
                # Sharp demand spike between t_start and t_end
                if t_start <= step <= t_end:
                    progress = (step - t_start) / max(1, t_end - t_start)
                    # Bell curve profile
                    bell = math.exp(-((progress - 0.4) ** 2) / 0.06)
                    demand_multiplier = 1.0 + (1.2 * event_intensity * bell)
                    # Supply responds with a delayed lagged adjustment (repositioning drivers)
                    delayed_progress = max(0.0, progress - 0.15)
                    supply_multiplier = 1.0 + (0.5 * event_intensity * delayed_progress)
                    if step == t_start:
                        step_annotation = f"Demand surge begins (+{int(event_intensity * 100)}% peak)"
                    elif step == t_peak:
                        step_annotation = "Peak passenger demand; drivers repositioning slowly"
                elif step == t_end + 1:
                    step_annotation = "Surge subsiding; supply returning toward baseline"

            elif scenario_type == "natural_shortage":
                # Simultaneous weather disruption: demand rises, supply drops
                if t_start <= step <= t_end:
                    progress = (step - t_start) / max(1, t_end - t_start)
                    bell = math.exp(-((progress - 0.5) ** 2) / 0.08)
                    demand_multiplier = 1.0 + (0.45 * event_intensity * bell)
                    supply_multiplier = max(0.3, 1.0 - (0.55 * event_intensity * bell))
                    if step == t_start:
                        step_annotation = "Severe rainstorm onset: demand rises, drivers go offline"
                    elif step == t_peak:
                        step_annotation = "Peak weather disruption: severe deficit observed"
                elif step == t_end + 1:
                    step_annotation = "Weather clears; driver availability recovering"

            elif scenario_type == "unusual_supply_drop":
                # Injected anomaly: supply plunges sharply while demand remains flat
                if t_start <= step <= t_end:
                    progress = (step - t_start) / max(1, t_end - t_start)
                    # Steep drop profile
                    drop_factor = math.exp(-((progress - 0.5) ** 2) / 0.07)
                    supply_multiplier = max(0.2, 1.0 - (0.75 * event_intensity * drop_factor))
                    # Demand has minor random noise only (no shock)
                    demand_multiplier = 1.0 + rng.gauss(0, 0.02)
                    if step == t_start:
                        step_annotation = f"Abrupt supply drop begins (-{int(event_intensity * 75)}%) with steady demand"
                    elif step == t_peak:
                        step_annotation = "Maximum supply depression; anomalous shortage state"
                elif step == t_end + 1:
                    step_annotation = "Drivers returning online; supply normalizing"

            # Apply AR(1) smoothing to avoid discontinuous jumps
            noise_d = rng.gauss(0, d_vol)
            noise_s = rng.gauss(0, s_vol)

            target_d = (base_d * demand_multiplier) + noise_d
            target_s = (base_s * supply_multiplier) + noise_s

            curr_demand = 0.7 * curr_demand + 0.3 * target_d
            curr_supply = 0.75 * curr_supply + 0.25 * target_s

            # Safe physical bounds
            ride_requests = max(5.0, round(curr_demand, 1))
            available_drivers = max(4.0, round(curr_supply, 1))

            # Dispatch and fulfillment economics
            max_dispatchable = available_drivers * 0.94
            completed_rides = int(min(ride_requests, max_dispatchable))
            unfulfilled_requests = int(max(0.0, ride_requests - completed_rides))

            # Supply-to-demand ratio (safe division)
            supply_demand_ratio = round(available_drivers / max(ride_requests, 1.0), 3)

            # Fare pressure index (baseline 100.0)
            if supply_demand_ratio < 1.0:
                shortage_intensity = (1.0 - supply_demand_ratio) / (supply_demand_ratio + 0.15)
                fare_pressure = 100.0 + min(220.0, 110.0 * (shortage_intensity ** 1.15))
            else:
                surplus = min(1.0, supply_demand_ratio - 1.0)
                fare_pressure = max(88.0, 100.0 - (12.0 * surplus))
            fare_pressure = round(fare_pressure + rng.gauss(0, 1.5), 1)

            # Estimated wait time (minutes)
            if supply_demand_ratio < 1.0:
                wait_time = 3.5 + min(18.0, 9.5 * ((1.0 - supply_demand_ratio) ** 1.3))
            else:
                wait_time = max(2.2, 3.5 - min(1.2, 0.8 * (supply_demand_ratio - 1.0)))
            wait_time = round(wait_time + rng.gauss(0, 0.2), 1)
            wait_time = max(2.0, wait_time)

            # Relative driver earnings index (baseline 100.0)
            earnings_mult = (fare_pressure / 100.0) * min(1.3, completed_rides / max(available_drivers, 1.0))
            driver_earnings_index = round(100.0 * earnings_mult, 1)

            record = {
                "step_number": step,
                "timestamp": current_timestamp.isoformat(),
                "zone_id": zone_id,
                "scenario_id": f"scenario_{scenario_type}",
                "scenario_type": scenario_type,
                "random_seed": active_seed,
                "ride_requests": ride_requests,
                "available_drivers": available_drivers,
                "completed_rides": completed_rides,
                "unfulfilled_requests": unfulfilled_requests,
                "estimated_wait_time_minutes": wait_time,
                "fare_pressure_index": fare_pressure,
                "supply_demand_ratio": supply_demand_ratio,
                "driver_earnings_index": driver_earnings_index,
                "context_type": scenario_meta["context_type"],
                "ground_truth_label": scenario_meta["ground_truth_label"],
                "annotation": step_annotation,
            }
            records.append(record)

        return records

    def to_dataframe(self, records: List[Dict[str, Any]]):
        """
        Convert records to a Pandas DataFrame if available.
        """
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        return records


data_generator = SyntheticDataGenerator()
