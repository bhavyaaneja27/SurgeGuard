#!/usr/bin/env python3
"""
CLI Script: Generate and Export Synthetic Marketplace Scenarios.
Usage:
    python scripts/generate_synthetic_data.py --scenario all --format csv --output-dir ../data/synthetic
"""
import argparse
import csv
import json
import os
import sys

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.services.data_generator import data_generator, SCENARIO_METADATA, ZONE_BASELINES


def main():
    parser = argparse.ArgumentParser(
        description="SurgeGuard: Generate reproducible synthetic marketplace data for training and simulation."
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="all",
        choices=["all", "normal_marketplace", "demand_led_surge", "natural_shortage", "unusual_supply_drop"],
        help="Scenario archetype to generate ('all' generates all 4 scenarios)"
    )
    parser.add_argument(
        "--zone",
        type=str,
        default="zone_midtown_core",
        choices=list(ZONE_BASELINES.keys()),
        help="Zone identifier"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for reproducibility"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Duration in simulated minutes/steps (e.g., 60, 120, 180)"
    )
    parser.add_argument(
        "--intensity",
        type=float,
        default=0.7,
        help="Event shock intensity multiplier (0.1 to 1.0)"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="csv",
        choices=["csv", "json"],
        help="Export file format ('csv' or 'json')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="../data/synthetic",
        help="Output folder for generated datasets"
    )

    args = parser.parse_args()

    target_scenarios = (
        list(SCENARIO_METADATA.keys())
        if args.scenario == "all"
        else [args.scenario]
    )

    output_path = os.path.abspath(args.output_dir)
    os.makedirs(output_path, exist_ok=True)

    print(f"[SurgeGuard] Synthetic Data Generator")
    print(f"  Target Scenarios: {', '.join(target_scenarios)}")
    print(f"  Zone:             {args.zone}")
    print(f"  Seed:             {args.seed}")
    print(f"  Duration:         {args.duration}m")
    print(f"  Intensity:        {args.intensity}")
    print(f"  Format:           {args.format}")
    print(f"  Output Directory: {output_path}\n")

    for s_type in target_scenarios:
        records = data_generator.generate_scenario_records(
            scenario_type=s_type,
            zone_id=args.zone,
            duration_minutes=args.duration,
            event_intensity=args.intensity,
            seed=args.seed,
        )

        filename = f"synthetic_{s_type}_{args.zone}_seed{args.seed}.{args.format}"
        file_path = os.path.join(output_path, filename)

        if args.format == "csv":
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                if records:
                    writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
                    writer.writeheader()
                    writer.writerows(records)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)

        print(f"  [OK] Exported: {filename} ({len(records)} records)")

    print(f"\n[Success] Generated {len(target_scenarios)} dataset file(s) for ML training & simulation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
