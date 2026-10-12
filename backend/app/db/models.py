"""
Database Schema Definitions.
Corresponds to PRD Section 11 specifications:
- scenarios
- simulation_runs
- simulation_steps
- alerts
- policy_runs
- model_registry
"""
from typing import Any, Dict


SCHEMA_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "scenarios": {
        "columns": [
            "id UUID PRIMARY KEY",
            "name VARCHAR(255) NOT NULL",
            "description TEXT",
            "scenario_type VARCHAR(64) NOT NULL",
            "seed INTEGER NOT NULL",
            "parameters_json JSONB NOT NULL",
            "created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        ],
        "purpose": "Reusable scenario definitions"
    },
    "simulation_runs": {
        "columns": [
            "id UUID PRIMARY KEY",
            "scenario_id UUID REFERENCES scenarios(id)",
            "seed INTEGER NOT NULL",
            "status VARCHAR(32) NOT NULL",
            "started_at TIMESTAMP WITH TIME ZONE NOT NULL",
            "completed_at TIMESTAMP WITH TIME ZONE",
            "config_json JSONB NOT NULL",
            "model_version VARCHAR(64) NOT NULL"
        ],
        "purpose": "One execution of a scenario"
    },
    "simulation_steps": {
        "columns": [
            "id UUID PRIMARY KEY",
            "run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE",
            "timestamp_step INTEGER NOT NULL",
            "zone_id VARCHAR(64) NOT NULL",
            "demand DOUBLE PRECISION NOT NULL",
            "available_supply DOUBLE PRECISION NOT NULL",
            "completed_rides INTEGER NOT NULL",
            "fare_pressure_index DOUBLE PRECISION NOT NULL",
            "wait_time_minutes DOUBLE PRECISION NOT NULL",
            "earnings_index DOUBLE PRECISION NOT NULL",
            "context_json JSONB"
        ],
        "indices": ["CREATE INDEX idx_sim_steps_run_zone ON simulation_steps(run_id, zone_id, timestamp_step)"],
        "purpose": "Time-series output for replay and charts"
    },
    "alerts": {
        "columns": [
            "id UUID PRIMARY KEY",
            "run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE",
            "zone_id VARCHAR(64) NOT NULL",
            "event_time TIMESTAMP WITH TIME ZONE NOT NULL",
            "score DOUBLE PRECISION NOT NULL",
            "severity VARCHAR(32) NOT NULL",
            "interpretation VARCHAR(64) NOT NULL",
            "reasons_json JSONB NOT NULL",
            "model_version VARCHAR(64) NOT NULL",
            "data_quality_json JSONB"
        ],
        "purpose": "Explainable alerts generated from runs"
    },
    "policy_runs": {
        "columns": [
            "id UUID PRIMARY KEY",
            "run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE",
            "policy_type VARCHAR(64) NOT NULL",
            "parameters_json JSONB NOT NULL",
            "metrics_json JSONB NOT NULL",
            "created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        ],
        "purpose": "Intervention comparisons"
    },
    "model_registry": {
        "columns": [
            "id UUID PRIMARY KEY",
            "name VARCHAR(128) NOT NULL",
            "version VARCHAR(64) NOT NULL",
            "artifact_path_or_uri TEXT NOT NULL",
            "features_json JSONB NOT NULL",
            "metrics_json JSONB NOT NULL",
            "training_data_version VARCHAR(64) NOT NULL",
            "created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        ],
        "purpose": "Model metadata; never store secrets"
    }
}
