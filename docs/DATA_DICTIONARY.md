# SurgeGuard Data Dictionary

## 1. Synthetic Marketplace Data Schema (Phase 1 Simulator)

The synthetic marketplace generator (`SyntheticDataGenerator`) produces time-series records containing the following fields:

| Field Name | Type | Range / Format | Description & Assumptions |
| :--- | :--- | :--- | :--- |
| `step_number` | Integer | `[0, duration - 1]` | Sequential time index representing the simulation minute. |
| `timestamp` | String (ISO-8601) | `YYYY-MM-DDTHH:MM:SSZ` | UTC timestamp anchored at the scenario start window, incrementing 1 minute per step. |
| `zone_id` | String | e.g. `zone_midtown_core` | Urban zone identifier (`midtown_core`, `downtown_financial`, `airport_terminal`, `uptown_residential`). |
| `scenario_id` | String | e.g. `scenario_unusual_supply_drop` | Identifier of the scenario category generating this time series. |
| `scenario_type` | String | Category Enum | One of 4 core archetypes: `normal_marketplace`, `demand_led_surge`, `natural_shortage`, `unusual_supply_drop`. |
| `random_seed` | Integer | e.g. `42` | Deterministic seed for reproducible pseudorandom noise generation. |
| `ride_requests` | Float | `≥ 5.0` | Passenger ride hail volume initiated in the target zone within that minute. |
| `available_drivers` | Float | `≥ 4.0` | Unassigned drivers actively online and eligible for dispatch in the zone. |
| `completed_rides` | Integer | `[0, requests]` | Number of successfully fulfilled trips, bounded by dispatch efficiency (`≤ available_drivers * 0.94`). |
| `unfulfilled_requests`| Integer | `≥ 0` | Requests not served immediately due to vehicle scarcity (`requests - completed_rides`). |
| `estimated_wait_time_minutes` | Float | `≥ 2.0` | Estimated dispatch latency from passenger booking to driver arrival. Scales nonlinearly during shortages. |
| `fare_pressure_index`| Float | `[88.0, 320.0]` | Dynamic pricing pressure indicator (Baseline = `100.0` at equilibrium). Escalates during driver deficits. |
| `supply_demand_ratio`| Float | `≥ 0.0` | Driver supply divided by passenger demand (`available_drivers / max(ride_requests, 1.0)`). |
| `driver_earnings_index`| Float | `[50.0, 220.0]` | Relative driver gross earnings metric (Baseline = `100.0`), influenced by surge multiplier and trip completion density. |
| `context_type` | String | Text Label | Environmental scenario context: `regular_operations`, `concert_or_event`, `weather_rainstorm`, `unexplained_availability_shock`. |
| `ground_truth_label` | String | Label Enum | Simulation ground truth for algorithmic benchmarking: `normal`, `demand_spike`, `natural_shortage`, `unusual_supply_drop`. **Does not prove real-world collusion.** |
| `annotation` | String / Null | Text string | Event milestone marker (e.g. onset of shock, peak deficit point, recovery phase). |

---

## 2. Feature Engineering Definitions (PRD Section 8.2)

Signals calculated across rolling windows for downstream anomaly detection models:

| Feature Name | Type | Description |
| :--- | :--- | :--- |
| `supply_drop_pct` | Float | Percentage reduction in available drivers over the rolling window. |
| `supply_drop_velocity` | Float | Rate of supply change per simulated minute. |
| `demand_change_pct` | Float | Percentage change in ride requests over the rolling window. |
| `supply_demand_ratio` | Float | Available supply divided by requests, safely handled when demand is zero. |
| `baseline_supply_deviation` | Float | Observed available supply relative to the expected zone/time baseline. |
| `shortage_duration` | Integer | Number of consecutive time steps supply remains below baseline threshold. |
| `recovery_speed` | Float | Rate at which driver supply rebounds toward expected baseline. |
| `time_context` | Dict | Hour of day, day of week, and zone encoded without lookahead leakage. |
| `scenario_context` | Dict | Metadata flags (e.g. weather storm simulation); omitted unless observed. |
| `data_quality_flags` | List[str] | Flags indicating missing values, stale data, unexpected telemetry gaps. |

---

## 3. Core Database Entities (PRD Section 11)

### Scenarios (`scenarios`)
- `id`: UUID primary key.
- `name`: Human-readable identifier.
- `description`: Detailed scenario objective and conditions.
- `scenario_type`: Category (`normal_marketplace`, `demand_led_surge`, `natural_shortage`, `unusual_supply_drop`).
- `seed`: Deterministic random seed.
- `parameters_json`: Configuration parameters (intensity, duration, zone).
- `created_at`: UTC timestamp.

### Simulation Runs (`simulation_runs`)
- `id`: UUID primary key.
- `scenario_id`: Foreign key reference to `scenarios.id`.
- `seed`: Seed used for this run.
- `status`: Execution state (`completed`, `running`, `failed`).
- `started_at`, `completed_at`: UTC execution timestamps.
- `config_json`: Snapshot of configuration at execution time.
- `model_version`: Forecaster and anomaly detector version string.

### Simulation Steps (`simulation_steps`)
- `id`: UUID primary key.
- `run_id`: Foreign key reference to `simulation_runs.id`.
- `timestamp_step`: Integer time step index (simulated minutes).
- `zone_id`: Zone identifier (e.g. `zone_midtown_core`).
- `ride_requests`: Simulated ride request volume.
- `available_drivers`: Active simulated online drivers.
- `completed_rides`: Count of fulfilled trips.
- `fare_pressure_index`: Simulated pricing pressure multiplier relative to baseline (100.0).
- `wait_time_minutes`: Estimated average passenger dispatch latency.
- `earnings_index`: Relative driver earnings index (baseline 100.0).
- `context_json`: Environmental context (e.g. rain intensity, traffic congestion).
