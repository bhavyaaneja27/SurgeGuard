# SurgeGuard Data Architecture & Governance

## 1. Distinction: Public Context vs. Synthetic Simulation

SurgeGuard maintains a strict separation between historical mobility records and generated simulation events:

| Data Type | Intended Use | Origin & Constraints |
| :--- | :--- | :--- |
| **Public Context Data** | Historical trip-volume and time-of-day zone patterns | NYC Taxi & Limousine Commission (TLC) public trip records. **Does not contain Uber private telemetry, driver IDs, or live driver status.** |
| **Synthetic Simulation Data** | Driver availability shocks, dynamic demand shifts, ground-truth scenario evaluation | Deterministically generated using seeded stochastic generators (`SyntheticDataGenerator`). **Explicitly labelled as synthetic/simulated.** |

## 2. Public Data Sources & Licensing

- **NYC TLC Trip Record Data:**
  - URL: [https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
  - Terms: Open Data Law / Public domain dataset provided by the City of New York.
  - Scope: Aggregated zone-to-zone pickup/drop-off counts.

## 3. Responsible Research Disclaimer

- SurgeGuard is a research prototype.
- Ground-truth scenario labels in synthetic datasets are valid solely for benchmarking anomaly detection algorithms in the simulated sandbox.
- Synthetic labels must **never** be cited as evidence of real-world driver collusion or individual wrongdoing.

## 4. Directory Structure

```
data/
├── raw/          # Raw public trip downloads (gitignored)
├── processed/    # Aggregated zone-level historical baselines (gitignored)
└── synthetic/    # Seeded simulation run outputs (gitignored)
```
