import os
import sys
sys.path.insert(0, ".")

from app.services.anomaly_detection import AnomalyDetector
from app.services.data_generator import data_generator

det = AnomalyDetector()

print("\n--- PHASE 3 DETECTOR PERFORMANCE ACROSS HELD-OUT SCENARIOS (SEED 44) ---")
for sc in ['normal_marketplace', 'demand_led_surge', 'natural_shortage', 'unusual_supply_drop']:
    recs = data_generator.generate_scenario_records(sc, seed=44)
    assessments = det.assess_simulation_run(recs)
    scores = [a.score for a in assessments]
    mean_s = sum(scores) / len(scores)
    max_s = max(scores)
    watch_cnt = sum(1 for a in assessments if a.risk_category == 'watch')
    inv_cnt = sum(1 for a in assessments if a.risk_category == 'investigate')
    norm_cnt = sum(1 for a in assessments if a.risk_category == 'normal')
    print(f"[{sc:<22}] Mean={mean_s:5.2f}, Max={max_s:5.2f} | Normal={norm_cnt:3d}, Watch={watch_cnt:3d}, Investigate={inv_cnt:3d}")
    top_a = max(assessments, key=lambda a: a.score)
    print(f"    Top Step {top_a.step_number}: score={top_a.score}, risk={top_a.risk_category}, interp='{top_a.interpretation}'")
    if top_a.supporting_reasons:
        print(f"    Supporting: {top_a.supporting_reasons[0]}")
    if top_a.weakening_reasons:
        print(f"    Weakening: {top_a.weakening_reasons[0]}")
