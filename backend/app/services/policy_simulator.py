"""
What-If Policy Lab Simulator Service.
Simulates and evaluates operational policy interventions against a reproducible Digital Twin baseline.
Interventions supported:
1. no_intervention (Baseline control)
2. targeted_driver_incentive (Dynamic supply inducement)
3. rider_discount (Price stimulus)
4. supply_recovery_support (Targeted deficit stabilization floor)
5. cooldown_freeze (Surge suppression ceiling)
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.policy import (
    PolicyComparisonRequest,
    PolicyComparisonResponse,
    PolicyOutcomeDeltas,
    PolicyOutcomeMetrics,
    PolicyRunComparison,
    PolicyTimelineStep,
    PolicyType,
)
from app.schemas.simulation import (
    SimulationCreateRequest,
    SimulationRunResponse,
)
from app.services.data_generator import ZONE_BASELINES
from app.services.persistence import persistence_service
from app.services.simulator import simulator_service

BASE_FARE_PER_RIDE = 18.50  # Baseline benchmark fare for cost calculations ($)


class PolicySimulator:
    """
    Simulation engine for comparative marketplace interventions.
    """

    def __init__(self):
        logger.info("Initialized PolicySimulator service")

    def compare_policies(
        self, request: PolicyComparisonRequest
    ) -> PolicyComparisonResponse:
        """
        Executes counterfactual policy evaluations against a shared baseline run.
        """
        # 1. Resolve or generate baseline simulation run
        baseline_run, baseline_steps = self._get_or_create_baseline(request)

        # 2. Extract baseline characteristics
        zone_id = baseline_run.zone_id
        scenario_type = baseline_run.scenario_type
        seed = baseline_run.seed
        zone_baseline_supply = ZONE_BASELINES.get(zone_id, {}).get(
            "baseline_supply", 100.0
        )

        # 3. Simulate baseline ("no_intervention") metrics and timeline
        baseline_comparison = self._simulate_policy(
            policy_type="no_intervention",
            baseline_steps=baseline_steps,
            zone_baseline_supply=zone_baseline_supply,
            incentive_pct=request.incentive_amount_pct,
            discount_pct=request.discount_amount_pct,
            recovery_pct=request.recovery_support_pct,
            baseline_metrics=None,
        )
        base_metrics = baseline_comparison.metrics

        # 4. Simulate each requested policy intervention
        comparisons: List[PolicyRunComparison] = [baseline_comparison]

        for p_type in request.policies:
            if p_type == "no_intervention":
                continue  # already added as first baseline entry

            comp = self._simulate_policy(
                policy_type=p_type,
                baseline_steps=baseline_steps,
                zone_baseline_supply=zone_baseline_supply,
                incentive_pct=request.incentive_amount_pct,
                discount_pct=request.discount_amount_pct,
                recovery_pct=request.recovery_support_pct,
                baseline_metrics=base_metrics,
            )
            comparisons.append(comp)

        return PolicyComparisonResponse(
            run_id=baseline_run.run_id,
            scenario_type=scenario_type,
            zone_id=zone_id,
            seed=seed,
            baseline_policy="no_intervention",
            comparisons=comparisons,
        )

    def _get_or_create_baseline(
        self, request: PolicyComparisonRequest
    ) -> Tuple[SimulationRunResponse, List[Dict[str, Any]]]:
        """
        Retrieves existing run or generates a deterministic new simulation.
        """
        if request.run_id:
            run = simulator_service.get_run(request.run_id)
            steps = simulator_service.get_run_steps(request.run_id)
            if run and steps:
                return run, steps

        # Generate new deterministic baseline run
        sim_payload = SimulationCreateRequest(
            scenario_type=request.scenario_type or "unusual_supply_drop",
            zone_id=request.zone_id or "zone_midtown_core",
            duration_minutes=request.duration_minutes or 120,
            event_intensity=request.event_intensity or 0.75,
            seed=request.seed if request.seed is not None else 42,
        )
        run, steps = simulator_service.run_simulation(sim_payload)
        return run, steps

    def _simulate_policy(
        self,
        policy_type: PolicyType,
        baseline_steps: List[Dict[str, Any]],
        zone_baseline_supply: float,
        incentive_pct: float,
        discount_pct: float,
        recovery_pct: float,
        baseline_metrics: Optional[PolicyOutcomeMetrics],
    ) -> PolicyRunComparison:
        """
        Executes counterfactual calculations step-by-step for a specific policy.
        """
        timeline: List[PolicyTimelineStep] = []
        tot_requests = 0
        tot_completed = 0
        tot_unfulfilled = 0
        sum_supply = 0.0
        sum_wait = 0.0
        max_wait = 0.0
        sum_fare_pressure = 0.0
        max_fare_pressure = 0.0
        sum_earnings = 0.0
        driver_incentive_cost = 0.0
        rider_discount_cost = 0.0
        intervention_cost = 0.0

        for step in baseline_steps:
            step_num = step["step_number"]
            ts = step["timestamp"]
            base_d = float(step["ride_requests"])
            base_s = float(step["available_drivers"])
            base_ratio = float(step.get("supply_demand_ratio", base_s / max(1.0, base_d)))

            curr_d = base_d
            curr_s = base_s
            step_incentive_cost = 0.0
            step_discount_cost = 0.0
            step_recovery_cost = 0.0

            if policy_type == "no_intervention":
                curr_d = base_d
                curr_s = base_s

            elif policy_type == "targeted_driver_incentive":
                # Supply responds with elasticity Es = 0.50
                # Capped at +55% maximum expansion
                s_boost = min(0.55, 0.50 * (incentive_pct / 100.0))
                curr_s = round(base_s * (1.0 + s_boost), 1)
                curr_d = base_d

            elif policy_type == "rider_discount":
                # Demand responds with price elasticity Ed = 0.60
                # Capped at +40% expansion
                d_boost = min(0.40, 0.60 * (discount_pct / 100.0))
                curr_d = round(base_d * (1.0 + d_boost), 1)
                curr_s = base_s

            elif policy_type == "supply_recovery_support":
                # Conditionally activates when supply/demand ratio is constrained (< 0.85)
                if base_ratio < 0.85:
                    deficit = max(0.0, zone_baseline_supply - base_s)
                    recovery_ratio = min(0.55, 0.70 * (recovery_pct / 100.0))
                    recovered_drivers = deficit * recovery_ratio
                    curr_s = round(base_s + recovered_drivers, 1)
                    # Support cost: hourly platform floor supplement per active driver
                    step_recovery_cost = round(curr_s * 4.50 * (recovery_pct / 30.0), 2)
                else:
                    curr_s = base_s
                curr_d = base_d

            elif policy_type == "cooldown_freeze":
                # Surge ceiling cooling: slight demand dampening and baseline supply
                curr_d = round(base_d * 0.95, 1)
                curr_s = base_s

            # Marketplace clearing mechanics
            dispatchable = curr_s * 0.94
            completed = int(min(curr_d, dispatchable))
            unfulfilled = int(max(0.0, curr_d - completed))
            ratio = round(curr_s / max(curr_d, 1.0), 3)

            # Re-compute dynamic fare pressure & wait times grounded in ratio physics
            if ratio < 1.0:
                shortage_intensity = (1.0 - ratio) / (ratio + 0.15)
                fp = 100.0 + min(220.0, 110.0 * (shortage_intensity ** 1.15))
                wt = 3.5 + min(18.0, 9.5 * ((1.0 - ratio) ** 1.3))
            else:
                surplus = min(1.0, ratio - 1.0)
                fp = max(88.0, 100.0 - (12.0 * surplus))
                wt = max(2.2, 3.5 - min(1.2, 0.8 * (ratio - 1.0)))

            if policy_type == "cooldown_freeze":
                fp = min(120.0, fp)

            fp = round(fp, 1)
            wt = round(max(2.0, wt), 1)

            earnings_mult = (fp / 100.0) * min(1.3, completed / max(curr_s, 1.0))
            earnings_idx = round(100.0 * earnings_mult, 1)

            # Cost accounting
            if policy_type == "targeted_driver_incentive":
                step_incentive_cost = round(completed * BASE_FARE_PER_RIDE * (incentive_pct / 100.0), 2)
            elif policy_type == "rider_discount":
                step_discount_cost = round(completed * BASE_FARE_PER_RIDE * (discount_pct / 100.0), 2)

            driver_incentive_cost += step_incentive_cost
            rider_discount_cost += step_discount_cost
            intervention_cost += (step_incentive_cost + step_discount_cost + step_recovery_cost)

            tot_requests += int(curr_d)
            tot_completed += completed
            tot_unfulfilled += unfulfilled
            sum_supply += curr_s
            sum_wait += wt
            max_wait = max(max_wait, wt)
            sum_fare_pressure += fp
            max_fare_pressure = max(max_fare_pressure, fp)
            sum_earnings += earnings_idx

            timeline.append(
                PolicyTimelineStep(
                    step_number=step_num,
                    timestamp=ts,
                    ride_requests=curr_d,
                    available_drivers=curr_s,
                    completed_rides=completed,
                    unfulfilled_requests=unfulfilled,
                    wait_time_minutes=wt,
                    fare_pressure_index=fp,
                )
            )

        n_steps = max(1, len(baseline_steps))
        avg_wait = round(sum_wait / n_steps, 2)
        avg_fp = round(sum_fare_pressure / n_steps, 1)
        avg_supply = round(sum_supply / n_steps, 1)
        avg_earnings = round(sum_earnings / n_steps, 1)
        fulfillment_pct = round((tot_completed / max(1, tot_requests)) * 100.0, 1)

        metrics = PolicyOutcomeMetrics(
            ride_requests=tot_requests,
            available_drivers=avg_supply,
            completed_rides=tot_completed,
            unfulfilled_requests=tot_unfulfilled,
            fulfillment_rate_pct=fulfillment_pct,
            average_wait_time_minutes=avg_wait,
            max_wait_time_minutes=round(max_wait, 1),
            fare_pressure_index=avg_fp,
            peak_fare_pressure=round(max_fare_pressure, 1),
            driver_earnings_index=avg_earnings,
            simulated_driver_incentive_cost=round(driver_incentive_cost, 2),
            simulated_rider_discount_cost=round(rider_discount_cost, 2),
            estimated_intervention_cost=round(intervention_cost, 2),
        )

        # Compute deltas versus baseline
        if baseline_metrics is not None:
            rides_delta = tot_completed - baseline_metrics.completed_rides
            cost_delta = round(intervention_cost - baseline_metrics.estimated_intervention_cost, 2)
            cost_per_recov = (
                round(cost_delta / rides_delta, 2)
                if rides_delta > 0 and cost_delta > 0
                else None
            )
            metrics.cost_per_recovered_ride = cost_per_recov

            deltas = PolicyOutcomeDeltas(
                ride_requests_delta=tot_requests - baseline_metrics.ride_requests,
                available_drivers_delta=round(avg_supply - baseline_metrics.available_drivers, 1),
                rides_delta=rides_delta,
                unfulfilled_delta=tot_unfulfilled - baseline_metrics.unfulfilled_requests,
                fulfillment_rate_delta=round(fulfillment_pct - baseline_metrics.fulfillment_rate_pct, 1),
                wait_time_delta=round(avg_wait - baseline_metrics.average_wait_time_minutes, 2),
                fare_pressure_delta=round(avg_fp - baseline_metrics.fare_pressure_index, 1),
                earnings_delta=round(avg_earnings - baseline_metrics.driver_earnings_index, 1),
                cost_delta=cost_delta,
            )
        else:
            deltas = PolicyOutcomeDeltas(
                ride_requests_delta=0,
                available_drivers_delta=0.0,
                rides_delta=0,
                unfulfilled_delta=0,
                fulfillment_rate_delta=0.0,
                wait_time_delta=0.0,
                fare_pressure_delta=0.0,
                earnings_delta=0.0,
                cost_delta=0.0,
            )

        name, desc, assumptions, trade_offs = self._get_metadata(
            policy_type, incentive_pct, discount_pct, recovery_pct
        )

        params = {
            "policy_type": policy_type,
            "incentive_amount_pct": incentive_pct,
            "discount_amount_pct": discount_pct,
            "recovery_support_pct": recovery_pct,
            "base_fare_benchmark": BASE_FARE_PER_RIDE,
        }

        return PolicyRunComparison(
            policy_type=policy_type,
            policy_name=name,
            description=desc,
            parameters_json=params,
            metrics=metrics,
            deltas_versus_baseline=deltas,
            timeline=timeline,
            assumptions=assumptions,
            trade_offs_and_limitations=trade_offs,
        )

    def _get_metadata(
        self,
        policy_type: PolicyType,
        incentive_pct: float,
        discount_pct: float,
        recovery_pct: float,
    ) -> Tuple[str, str, List[str], List[str]]:
        if policy_type == "no_intervention":
            return (
                "No Intervention (Baseline Control)",
                "Market clearing under organic conditions and scenario shocks without platform intervention.",
                [
                    "Marketplace dynamics proceed purely from scenario shock curves and baseline driver/rider behavior.",
                    "No financial platform subsidies or artificial pricing floors deployed.",
                    "Deterministic starting seed identical across all policy comparisons.",
                ],
                [
                    "Zero platform intervention cost ($0.00).",
                    "Leaves passenger waiting times and fare surges unmitigated during sudden supply shortages.",
                    "Higher unfulfilled request volume when drivers exit the network.",
                ],
            )
        elif policy_type == "targeted_driver_incentive":
            return (
                f"Targeted Driver Incentive (+{incentive_pct}%)",
                f"Deploy a +{incentive_pct}% per-ride incentive bonus to attract and reposition drivers to the affected zone.",
                [
                    "Driver supply responds with empirical elasticity Es = 0.50 (repositioning from adjacent zones).",
                    "Per-ride bonus funded entirely from platform reserves ($18.50 base fare * incentive %).",
                    "Diminishing marginal supply returns capped at +55% maximum expansion.",
                ],
                [
                    "Directly expands driver availability and lowers passenger wait times.",
                    "Significant platform budgetary commitment ($" + str(round(BASE_FARE_PER_RIDE * incentive_pct / 100.0, 2)) + "/completed ride).",
                    "Cannot overcome physical external blockades (e.g., severe road flooding or blizzards).",
                ],
            )
        elif policy_type == "rider_discount":
            return (
                f"Rider Fare Discount (-{discount_pct}%)",
                f"Offer a {discount_pct}% fare discount to riders to stimulate bookings and maintain platform loyalty.",
                [
                    "Passenger demand responds with price elasticity Ed = 0.60.",
                    "Platform absorbs the discount difference without reducing base driver payouts.",
                    "Available driver supply remains at baseline levels (unsubsidized).",
                ],
                [
                    "Increases passenger demand and booking intent.",
                    "CRITICAL COUNTERPRODUCTIVE RISK: In supply-depressed scenarios, stimulating rider demand without adding drivers worsens the vehicle deficit, inflating wait times and unfulfilled requests.",
                    "Generates substantial platform discount expenses without improving driver retention.",
                ],
            )
        elif policy_type == "supply_recovery_support":
            return (
                f"Supply Recovery Support ({recovery_pct}% Floor)",
                f"Deploy a targeted {recovery_pct}% supply stabilization floor to protect driver revenue and expedite recovery during shortages.",
                [
                    "Intervention triggers conditionally when supply-to-demand ratio drops below 0.85.",
                    "Minimum revenue guarantee mitigates driver offline churn and recovers up to 55% of the deficit.",
                    "Platform funds standby floor subsidies ($4.50/step normalized) for active drivers in deficit windows.",
                ],
                [
                    "Cost-effective targeted expenditure: only incurs subsidies during acute shortage steps.",
                    "Accelerates marketplace recovery and reduces peak fare pressure spikes.",
                    "Requires rapid automated anomaly detection; detection latency delays intervention activation.",
                ],
            )
        else:
            return (
                "Dynamic Surge Cap Freeze",
                "Impose a strict ceiling on surge pricing (max 120.0 index) to prevent excessive rider fare inflation.",
                [
                    "Surge pricing capped at 120.0 index regardless of shortage severity.",
                    "Consumer demand slightly throttled (-5%) by platform throttle.",
                ],
                [
                    "Protects passengers from extreme price spikes.",
                    "Reduces driver surge earnings, slightly disincentivizing driver repositioning into the zone.",
                ],
            )


policy_simulator = PolicySimulator()
