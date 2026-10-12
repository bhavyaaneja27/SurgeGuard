import React, { useState, useEffect } from 'react';
import {
  Scale,
  Play,
  AlertTriangle,
  Info,
  Sliders,
  CheckCircle2,
  FileSpreadsheet,
  FileCode,
  ShieldAlert,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { apiClient } from '../../lib/api-client';
import type {
  ScenarioType,
  PolicyType,
  PolicyComparisonResponse,
} from '../../lib/types';

const SCENARIO_OPTIONS: { id: ScenarioType; name: string }[] = [
  { id: 'unusual_supply_drop', name: 'Unusual Supply Drop (Driver Deficit)' },
  { id: 'natural_shortage', name: 'Natural Shortage (Severe Weather)' },
  { id: 'demand_led_surge', name: 'Demand-Led Surge (Major Event)' },
  { id: 'normal_marketplace', name: 'Normal Marketplace (Equilibrium)' },
];

const ZONE_OPTIONS = [
  { id: 'zone_midtown_core', name: 'Midtown Core (High Volume)' },
  { id: 'zone_downtown_financial', name: 'Downtown Financial (Commuter Hub)' },
  { id: 'zone_airport_terminal', name: 'Airport Terminal (Steady Queue)' },
  { id: 'zone_uptown_residential', name: 'Uptown Residential (Dispersed)' },
];

const POLICY_COLORS: Record<PolicyType, string> = {
  no_intervention: '#64748b', // Slate
  targeted_driver_incentive: '#059669', // Emerald
  rider_discount: '#e11d48', // Rose (warns of congestion risk)
  supply_recovery_support: '#0284c7', // Sky blue
  cooldown_freeze: '#8b5cf6', // Violet
};

export const PolicyLabPage: React.FC = () => {
  // Config state
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('unusual_supply_drop');
  const [selectedZone, setSelectedZone] = useState<string>('zone_midtown_core');
  const [seed, setSeed] = useState<number>(42);
  const [incentivePct, setIncentivePct] = useState<number>(25);
  const [discountPct, setDiscountPct] = useState<number>(20);
  const [recoveryPct, setRecoveryPct] = useState<number>(30);

  // Active chart metric view
  const [activeChartMetric, setActiveChartMetric] = useState<'drivers' | 'wait_time' | 'fare_pressure'>('drivers');

  // Execution state
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonData, setComparisonData] = useState<PolicyComparisonResponse | null>(null);
  const [selectedPolicyType, setSelectedPolicyType] = useState<PolicyType>('targeted_driver_incentive');

  const runComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.comparePolicies({
        scenario_type: selectedScenario,
        zone_id: selectedZone,
        seed: seed,
        duration_minutes: 120,
        event_intensity: 0.75,
        policies: [
          'no_intervention',
          'targeted_driver_incentive',
          'rider_discount',
          'supply_recovery_support',
        ],
        incentive_amount_pct: incentivePct,
        discount_amount_pct: discountPct,
        recovery_support_pct: recoveryPct,
      });
      setComparisonData(response);
    } catch (err) {
      console.error('Policy comparison failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to execute policy comparison simulation.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runComparison();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeComp = comparisonData?.comparisons.find((c) => c.policy_type === selectedPolicyType) || comparisonData?.comparisons[1];

  // Prepare combined timeline data for Recharts
  const chartTimeline = React.useMemo(() => {
    if (!comparisonData || comparisonData.comparisons.length === 0) return [];
    const baseline = comparisonData.comparisons[0];
    return baseline.timeline.map((step, idx) => {
      const row: Record<string, number | string> = {
        step: `T+${step.step_number * 5}m`,
        step_number: step.step_number,
      };

      comparisonData.comparisons.forEach((comp) => {
        const compStep = comp.timeline[idx];
        if (compStep) {
          if (activeChartMetric === 'drivers') {
            row[`drivers_${comp.policy_type}`] = compStep.available_drivers;
          } else if (activeChartMetric === 'wait_time') {
            row[`wait_${comp.policy_type}`] = compStep.wait_time_minutes;
          } else {
            row[`fare_${comp.policy_type}`] = compStep.fare_pressure_index;
          }
        }
      });
      return row;
    });
  }, [comparisonData, activeChartMetric]);

  // Export handlers
  const handleExport = (format: 'csv' | 'json') => {
    if (!comparisonData) return;
    const url = apiClient.getPolicyExportUrl(comparisonData.run_id, format, {
      incentive_pct: incentivePct,
      discount_pct: discountPct,
      recovery_pct: recoveryPct,
    });
    window.open(url, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Research Disclaimer */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-200">
              <Scale className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">What-If Policy Lab</h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-100/70 text-emerald-800 border border-emerald-200">
              Counterfactual Sandbox
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Simulate and contrast operational market interventions (targeted driver incentives, rider discounts, and shortage recovery support) against a deterministic Digital Twin baseline.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('csv')}
            disabled={!comparisonData || loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-sm"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            Export CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={!comparisonData || loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-sm"
          >
            <FileCode className="w-3.5 h-3.5 text-blue-600" />
            Export JSON
          </button>
        </div>
      </div>

      {/* Control & Parameter Tuning Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-800">
            <Sliders className="w-4 h-4 text-emerald-600" />
            <span>Policy Simulation Parameters &amp; Scenario Anchor</span>
          </div>
          <span className="text-[11px] text-slate-400">
            Seed #{seed} • 120 Minutes Timeline
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Scenario Selection */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Scenario Shock</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value as ScenarioType)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
            >
              {SCENARIO_OPTIONS.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.name}
                </option>
              ))}
            </select>
          </div>

          {/* Zone Selection */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Market Zone</label>
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
            >
              {ZONE_OPTIONS.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            </select>
          </div>

          {/* Seed Input */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Random Seed</label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(parseInt(e.target.value, 10) || 42)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
            />
          </div>

          {/* Execution Button */}
          <div className="flex items-end">
            <button
              onClick={runComparison}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50 transition-colors"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loading ? 'Simulating Policies...' : 'Run What-If Comparison'}
            </button>
          </div>
        </div>

        {/* Sliders for Interventions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-3 border-t border-slate-100">
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium text-slate-700">Driver Incentive Bonus</span>
              <span className="text-xs font-mono font-bold text-emerald-700">+{incentivePct}%</span>
            </div>
            <input
              type="range"
              min={5}
              max={100}
              step={5}
              value={incentivePct}
              onChange={(e) => setIncentivePct(parseInt(e.target.value, 10))}
              className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Supply elasticity $E_s = 0.50$; expands available fleet into zone.
            </p>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium text-slate-700">Rider Fare Discount</span>
              <span className="text-xs font-mono font-bold text-rose-600">-{discountPct}%</span>
            </div>
            <input
              type="range"
              min={5}
              max={50}
              step={5}
              value={discountPct}
              onChange={(e) => setDiscountPct(parseInt(e.target.value, 10))}
              className="w-full accent-rose-600 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Demand elasticity $E_d = 0.60$; risk of worsening shortages if unmitigated.
            </p>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium text-slate-700">Supply Recovery Floor</span>
              <span className="text-xs font-mono font-bold text-sky-600">{recoveryPct}% Floor</span>
            </div>
            <input
              type="range"
              min={10}
              max={60}
              step={5}
              value={recoveryPct}
              onChange={(e) => setRecoveryPct(parseInt(e.target.value, 10))}
              className="w-full accent-sky-600 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Triggers conditionally when ratio &lt; 0.85 to arrest driver churn.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Side-by-Side KPI Deltas Grid */}
      {comparisonData && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Card 1: Completed Rides */}
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Completed Rides</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              {activeComp?.metrics.completed_rides.toLocaleString()}
            </div>
            <div className="flex items-center gap-1 mt-1 text-[11px]">
              {activeComp?.deltas_versus_baseline.rides_delta !== 0 ? (
                <span className={activeComp?.deltas_versus_baseline.rides_delta! > 0 ? 'text-emerald-600 font-semibold flex items-center' : 'text-rose-600 font-semibold flex items-center'}>
                  {activeComp?.deltas_versus_baseline.rides_delta! > 0 ? '+' : ''}
                  {activeComp?.deltas_versus_baseline.rides_delta} vs base
                </span>
              ) : (
                <span className="text-slate-400">Baseline control</span>
              )}
            </div>
          </div>

          {/* Card 2: Unfulfilled Requests */}
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Unfulfilled Req.</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              {activeComp?.metrics.unfulfilled_requests.toLocaleString()}
            </div>
            <div className="flex items-center gap-1 mt-1 text-[11px]">
              {activeComp?.deltas_versus_baseline.unfulfilled_delta !== 0 ? (
                <span className={activeComp?.deltas_versus_baseline.unfulfilled_delta! < 0 ? 'text-emerald-600 font-semibold' : 'text-rose-600 font-semibold'}>
                  {activeComp?.deltas_versus_baseline.unfulfilled_delta! > 0 ? '+' : ''}
                  {activeComp?.deltas_versus_baseline.unfulfilled_delta} vs base
                </span>
              ) : (
                <span className="text-slate-400">Baseline control</span>
              )}
            </div>
          </div>

          {/* Card 3: Average Wait Time */}
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Avg Rider Wait</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              {activeComp?.metrics.average_wait_time_minutes.toFixed(1)}m
            </div>
            <div className="flex items-center gap-1 mt-1 text-[11px]">
              {activeComp?.deltas_versus_baseline.wait_time_delta !== 0 ? (
                <span className={activeComp?.deltas_versus_baseline.wait_time_delta! < 0 ? 'text-emerald-600 font-semibold' : 'text-rose-600 font-semibold'}>
                  {activeComp?.deltas_versus_baseline.wait_time_delta! > 0 ? '+' : ''}
                  {activeComp?.deltas_versus_baseline.wait_time_delta.toFixed(1)}m vs base
                </span>
              ) : (
                <span className="text-slate-400">Baseline control</span>
              )}
            </div>
          </div>

          {/* Card 4: Fare Pressure Index */}
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Avg Fare Pressure</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              {activeComp?.metrics.fare_pressure_index.toFixed(1)}
            </div>
            <div className="flex items-center gap-1 mt-1 text-[11px]">
              {activeComp?.deltas_versus_baseline.fare_pressure_delta !== 0 ? (
                <span className={activeComp?.deltas_versus_baseline.fare_pressure_delta! < 0 ? 'text-emerald-600 font-semibold' : 'text-rose-600 font-semibold'}>
                  {activeComp?.deltas_versus_baseline.fare_pressure_delta! > 0 ? '+' : ''}
                  {activeComp?.deltas_versus_baseline.fare_pressure_delta.toFixed(1)} pts
                </span>
              ) : (
                <span className="text-slate-400">Baseline (100.0)</span>
              )}
            </div>
          </div>

          {/* Card 5: Estimated Platform Cost */}
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Intervention Cost</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              ${activeComp?.metrics.estimated_intervention_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Platform out-of-pocket
            </div>
          </div>

          {/* Card 6: Cost per Recovered Ride */}
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Cost / Recov. Ride</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              {activeComp?.metrics.cost_per_recovered_ride != null
                ? `$${activeComp.metrics.cost_per_recovered_ride.toFixed(2)}`
                : 'N/A'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 truncate">
              Incremental clearing efficiency
            </div>
          </div>
        </div>
      )}

      {/* Comparative Visualizations & Active Policy Selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Comparative Dynamic Trajectories</h3>
            <p className="text-xs text-slate-500">
              Evaluating step-by-step market clearing trajectories under each policy intervention
            </p>
          </div>

          {/* Metric Selector Tabs */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setActiveChartMetric('drivers')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                activeChartMetric === 'drivers'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Available Drivers
            </button>
            <button
              onClick={() => setActiveChartMetric('wait_time')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                activeChartMetric === 'wait_time'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Passenger Wait Time
            </button>
            <button
              onClick={() => setActiveChartMetric('fare_pressure')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                activeChartMetric === 'fare_pressure'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Fare Pressure Index
            </button>
          </div>
        </div>

        {/* Chart View */}
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartTimeline} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="step" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '8px',
                  fontSize: '12px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />

              {comparisonData?.comparisons.map((comp) => {
                const keyPrefix =
                  activeChartMetric === 'drivers'
                    ? 'drivers_'
                    : activeChartMetric === 'wait_time'
                    ? 'wait_'
                    : 'fare_';
                return (
                  <Line
                    key={comp.policy_type}
                    type="monotone"
                    dataKey={`${keyPrefix}${comp.policy_type}`}
                    name={comp.policy_name}
                    stroke={POLICY_COLORS[comp.policy_type] || '#059669'}
                    strokeWidth={comp.policy_type === selectedPolicyType ? 2.5 : 1.5}
                    strokeDasharray={comp.policy_type === 'no_intervention' ? '4 4' : undefined}
                    dot={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Side-by-Side Detailed Comparison Table */}
      {comparisonData && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="p-4 bg-slate-50/50 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Policy Performance &amp; Cost-Benefit Matrix
              </h3>
              <p className="text-xs text-slate-500">
                Direct side-by-side comparison across all simulated intervention regimes
              </p>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              Base Fare: $18.50/trip
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Intervention Policy</th>
                  <th className="py-2.5 px-3 text-right">Avg Drivers</th>
                  <th className="py-2.5 px-3 text-right">Completed Rides</th>
                  <th className="py-2.5 px-3 text-right">Unfulfilled</th>
                  <th className="py-2.5 px-3 text-right">Fulfillment %</th>
                  <th className="py-2.5 px-3 text-right">Avg Wait</th>
                  <th className="py-2.5 px-3 text-right">Avg Surge</th>
                  <th className="py-2.5 px-3 text-right">Intervention Cost</th>
                  <th className="py-2.5 px-3 text-right">Cost / Recov. Ride</th>
                  <th className="py-2.5 px-3 text-center">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 font-mono">
                {comparisonData.comparisons.map((comp) => {
                  const isSelected = comp.policy_type === selectedPolicyType;
                  const isBaseline = comp.policy_type === 'no_intervention';
                  const d = comp.deltas_versus_baseline;
                  return (
                    <tr
                      key={comp.policy_type}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        isSelected ? 'bg-emerald-50/40 font-medium' : ''
                      }`}
                    >
                      <td className="py-2.5 px-3 font-sans">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2.5 h-2.5 rounded-full"
                            style={{ backgroundColor: POLICY_COLORS[comp.policy_type] }}
                          />
                          <span className="font-semibold text-slate-900">{comp.policy_name}</span>
                          {isBaseline && (
                            <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.2 rounded font-sans">
                              Control
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {comp.metrics.available_drivers.toFixed(1)}
                        {!isBaseline && d.available_drivers_delta !== 0 && (
                          <span className="text-[10px] text-emerald-600 block">
                            +{d.available_drivers_delta.toFixed(1)}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                        {comp.metrics.completed_rides.toLocaleString()}
                        {!isBaseline && d.rides_delta !== 0 && (
                          <span className={`text-[10px] block ${d.rides_delta > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {d.rides_delta > 0 ? '+' : ''}{d.rides_delta}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {comp.metrics.unfulfilled_requests.toLocaleString()}
                        {!isBaseline && d.unfulfilled_delta !== 0 && (
                          <span className={`text-[10px] block ${d.unfulfilled_delta < 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {d.unfulfilled_delta > 0 ? '+' : ''}{d.unfulfilled_delta}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {comp.metrics.fulfillment_rate_pct.toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {comp.metrics.average_wait_time_minutes.toFixed(1)}m
                        {!isBaseline && d.wait_time_delta !== 0 && (
                          <span className={`text-[10px] block ${d.wait_time_delta < 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {d.wait_time_delta > 0 ? '+' : ''}{d.wait_time_delta.toFixed(1)}m
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {comp.metrics.fare_pressure_index.toFixed(1)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                        ${comp.metrics.estimated_intervention_cost.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {comp.metrics.cost_per_recovered_ride != null
                          ? `$${comp.metrics.cost_per_recovered_ride.toFixed(2)}`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-center font-sans">
                        <button
                          onClick={() => setSelectedPolicyType(comp.policy_type)}
                          className={`px-2.5 py-1 text-[11px] rounded transition-colors ${
                            isSelected
                              ? 'bg-emerald-600 text-white font-medium'
                              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                          }`}
                        >
                          {isSelected ? 'Active' : 'Select'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Assumptions, Economic Trade-offs & Limitations Card */}
      {activeComp && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Info className="w-4 h-4 text-emerald-600" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Selected Policy Breakdown: {activeComp.policy_name}
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Economic Assumptions */}
            <div className="space-y-2">
              <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Mathematical Assumptions &amp; Elasticities
              </span>
              <ul className="space-y-1.5 text-xs text-slate-600 list-disc list-inside bg-slate-50 p-3 rounded-lg border border-slate-200">
                {activeComp.assumptions.map((assump, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {assump}
                  </li>
                ))}
              </ul>
            </div>

            {/* Operational Trade-offs & Limitations */}
            <div className="space-y-2">
              <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                Trade-offs, Risks &amp; Real-World Limitations
              </span>
              <ul className="space-y-1.5 text-xs text-slate-600 list-disc list-inside bg-amber-50/50 p-3 rounded-lg border border-amber-200">
                {activeComp.trade_offs_and_limitations.map((lim, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {lim}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PolicyLabPage;
