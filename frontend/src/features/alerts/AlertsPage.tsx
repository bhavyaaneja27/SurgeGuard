import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Eye,
  CheckCircle2,
  TrendingDown,
  TrendingUp,
  Activity,
  HelpCircle,
  Filter,
  RefreshCw,
  ChevronRight,
  Info,
  Sparkles,
  Search,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';
import { apiClient } from '../../lib/api-client';
import type {
  RunAssessmentResponse,
  StepAssessment,
  ScenarioType,
} from '../../lib/types';

const ZONE_NAMES: Record<string, string> = {
  zone_midtown_core: 'Midtown Core',
  zone_downtown_financial: 'Downtown Financial',
  zone_airport_terminal: 'Airport Terminal',
  zone_uptown_residential: 'Uptown Residential',
};

const SCENARIOS = [
  { id: 'unusual_supply_drop' as ScenarioType, name: 'Unusual Supply Drop (Target Anomaly)' },
  { id: 'natural_shortage' as ScenarioType, name: 'Natural Weather Shortage (Organic)' },
  { id: 'demand_led_surge' as ScenarioType, name: 'Demand-Led Surge (Normal Peak)' },
  { id: 'normal_marketplace' as ScenarioType, name: 'Normal Marketplace (Equilibrium)' },
];

export const AlertsPage: React.FC = () => {
  // Run Execution & Assessment States
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('unusual_supply_drop');
  const [selectedZone, setSelectedZone] = useState<string>('zone_midtown_core');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [assessmentData, setAssessmentData] = useState<RunAssessmentResponse | null>(null);

  // Filters
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchStep, setSearchStep] = useState<string>('');

  // Selected Step Detail Modal/Panel
  const [selectedStep, setSelectedStep] = useState<StepAssessment | null>(null);

  // Execute or Fetch Demo Simulation & Assessment
  const runAssessment = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Create a quick deterministic simulation run
      const simRun = await apiClient.createSimulation({
        scenario_type: selectedScenario,
        zone_id: selectedZone,
        duration_minutes: 120,
        event_intensity: 0.75,
        seed: 42,
      });

      // 2. Run Phase 3 Contextual Anomaly Assessment
      const assessment = await apiClient.assessRun(simRun.run_id);
      setAssessmentData(assessment);

      // Default select the peak alert step
      if (assessment.alerts_only.length > 0) {
        setSelectedStep(assessment.alerts_only[0]);
      } else if (assessment.assessments.length > 0) {
        setSelectedStep(assessment.assessments[Math.floor(assessment.assessments.length / 2)]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to assess simulation run';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runAssessment();
  }, [selectedScenario, selectedZone]);

  const summary = assessmentData?.summary;
  const allAssessments = assessmentData?.assessments || [];

  // Filtered Steps
  const filteredAssessments = allAssessments.filter((a) => {
    if (filterCategory === 'investigate' && a.risk_category !== 'investigate') return false;
    if (filterCategory === 'watch' && a.risk_category !== 'watch') return false;
    if (filterCategory === 'normal' && a.risk_category !== 'normal') return false;
    if (filterCategory === 'alerts' && a.risk_category === 'normal') return false;
    if (searchStep && !a.step_number.toString().includes(searchStep)) return false;
    return true;
  });

  // Chart data formatting
  const chartData = allAssessments.map((a) => ({
    step: a.step_number,
    score: a.score,
    obs_supply: a.baseline_comparison.observed_supply,
    exp_supply: a.baseline_comparison.expected_supply,
    obs_demand: a.baseline_comparison.observed_demand,
    exp_demand: a.baseline_comparison.expected_demand,
    risk: a.risk_category,
  }));

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Badges */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700">
              <Sparkles className="w-3.5 h-3.5" /> CONTEXTUAL INTEGRITY DETECTOR
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
              SYNTHETIC DEMO
            </span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900">
            Marketplace Integrity Alerts &amp; Explanations
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Demand-conditioned anomaly scoring combining fixed-baseline deviation, shortage persistence,
            and Isolation Forest cross-validation with plain-language explanations.
          </p>
        </div>

        {/* Scenario Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value as ScenarioType)}
            className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 font-medium text-slate-800 focus:ring-2 focus:ring-indigo-500"
          >
            {SCENARIOS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <select
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 font-medium text-slate-800 focus:ring-2 focus:ring-indigo-500"
          >
            {Object.entries(ZONE_NAMES).map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>

          <button
            onClick={runAssessment}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Evaluating...' : 'Re-evaluate'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium">
          Error: {error}
        </div>
      )}

      {/* Risk Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Investigate Card */}
        <div className="bg-white p-5 rounded-xl border border-rose-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-600">Investigate</span>
            <div className="w-7 h-7 rounded-lg bg-rose-100 flex items-center justify-center text-rose-600">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-rose-700">
              {summary ? summary.investigate_steps_count : '—'}
            </span>
            <span className="text-xs text-rose-500 font-medium">steps (&ge; 60 pts)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
            High priority operational review: severe supply plunge with flat demand.
          </p>
        </div>

        {/* Watch Card */}
        <div className="bg-white p-5 rounded-xl border border-amber-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-600">Watch</span>
            <div className="w-7 h-7 rounded-lg bg-amber-100 flex items-center justify-center text-amber-600">
              <Eye className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-amber-700">
              {summary ? summary.watch_steps_count : '—'}
            </span>
            <span className="text-xs text-amber-500 font-medium">steps (30–59 pts)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
            Moderate priority: potential weather onset, shift rotation, or emerging deficit.
          </p>
        </div>

        {/* Normal Card */}
        <div className="bg-white p-5 rounded-xl border border-emerald-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-600">Normal</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-600">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-emerald-700">
              {summary ? summary.normal_steps_count : '—'}
            </span>
            <span className="text-xs text-emerald-500 font-medium">steps (&lt; 30 pts)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
            Market equilibrium or natural demand surges with adequate supply response.
          </p>
        </div>

        {/* Max Risk Score Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Peak Risk Score</span>
            <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900">
              {summary ? summary.max_score.toFixed(1) : '—'}
            </span>
            <span className="text-xs text-slate-500 font-medium">/ 100</span>
          </div>
          <div className="mt-2 text-[11px] font-semibold text-indigo-600 truncate">
            {summary?.dominant_interpretation || 'Normal equilibrium'}
          </div>
        </div>
      </div>

      {/* Main Charts: Observed vs Expected & Risk Score Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Observed vs Expected Supply */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Observed vs. Expected Normal Supply</h3>
              <p className="text-[11px] text-slate-500">
                Fixed forecast baseline prevents short rolling-window adaptation during sustained drops.
              </p>
            </div>
            <span className="text-[11px] px-2 py-0.5 bg-slate-100 rounded text-slate-600 font-mono">
              Zone: {ZONE_NAMES[selectedZone] || selectedZone}
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="step" tick={{ fontSize: 10 }} label={{ value: 'Minute Step', position: 'insideBottom', offset: -5, fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} domain={['dataMin - 10', 'dataMax + 10']} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', fontSize: '11px', border: '1px solid #e2e8f0' }}
                  formatter={(val: any) => [`${typeof val === 'number' ? val.toFixed(1) : (val ?? '0')}`, '']}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Line
                  type="monotone"
                  dataKey="exp_supply"
                  stroke="#94a3b8"
                  strokeDasharray="4 4"
                  name="Expected Supply Baseline"
                  dot={false}
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="obs_supply"
                  stroke="#4f46e5"
                  name="Observed Drivers"
                  dot={false}
                  strokeWidth={2.5}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Anomaly Risk Score Timeline with Category Bands */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Contextual Risk Score Timeline</h3>
              <p className="text-[11px] text-slate-500">
                Calibrated score (0–100) combining demand-conditioned rules and Isolation Forest.
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span> Investigate (&ge;60)
              <span className="w-2 h-2 rounded-full bg-amber-500 ml-2"></span> Watch (30–59)
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e11d48" stopOpacity={0.6} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="step" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', fontSize: '11px', border: '1px solid #e2e8f0' }}
                  formatter={(val: any) => [`${typeof val === 'number' ? val.toFixed(1) : (val ?? '0')} / 100`, '']}
                />
                <ReferenceLine y={60} stroke="#e11d48" strokeDasharray="3 3" label={{ value: 'Investigate (60)', fill: '#e11d48', fontSize: 10 }} />
                <ReferenceLine y={30} stroke="#d97706" strokeDasharray="3 3" label={{ value: 'Watch (30)', fill: '#d97706', fontSize: 10 }} />
                <Area
                  type="monotone"
                  dataKey="score"
                  stroke="#e11d48"
                  fill="url(#scoreGrad)"
                  name="Risk Score"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout: Alerts List (Left) and Detailed Explanation Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Filterable Alerts List (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
          {/* Table / List Filter Bar */}
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-bold text-slate-700">Filter Steps:</span>
              <div className="flex items-center gap-1 ml-2">
                {(['all', 'investigate', 'watch', 'normal'] as const).map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setFilterCategory(cat)}
                    className={`px-2.5 py-1 text-xs rounded-md font-semibold capitalize transition ${
                      filterCategory === cat
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter step #..."
                  value={searchStep}
                  onChange={(e) => setSearchStep(e.target.value)}
                  className="pl-8 pr-2.5 py-1 text-xs bg-white border border-slate-200 rounded-md text-slate-800 placeholder-slate-400 w-28 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div className="text-xs text-slate-500 font-medium">
                Showing <span className="font-bold text-slate-800">{filteredAssessments.length}</span> steps
              </div>
            </div>
          </div>

          {/* List Content */}
          <div className="divide-y divide-slate-100 max-h-[560px] overflow-y-auto">
            {filteredAssessments.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                No steps match the selected filter criteria.
              </div>
            ) : (
              filteredAssessments.map((step) => {
                const isSelected = selectedStep?.step_number === step.step_number;
                const isInvestigate = step.risk_category === 'investigate';
                const isWatch = step.risk_category === 'watch';

                return (
                  <div
                    key={step.step_number}
                    onClick={() => setSelectedStep(step)}
                    className={`p-3.5 flex items-center justify-between gap-4 cursor-pointer transition hover:bg-slate-50 ${
                      isSelected ? 'bg-indigo-50/70 border-l-4 border-indigo-600' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono text-xs font-bold ${
                          isInvestigate
                            ? 'bg-rose-100 text-rose-700'
                            : isWatch
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        m{step.step_number}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                              isInvestigate
                                ? 'bg-rose-100 text-rose-700'
                                : isWatch
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {step.risk_category}
                          </span>
                          <span className="text-xs font-bold text-slate-900">
                            {step.interpretation}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-3">
                          <span>
                            Obs Supply: <strong>{step.baseline_comparison.observed_supply}</strong> (
                            {step.baseline_comparison.supply_delta_pct > 0 ? '-' : '+'}
                            {Math.abs(step.baseline_comparison.supply_delta_pct * 100).toFixed(0)}%)
                          </span>
                          <span>•</span>
                          <span>
                            Demand: <strong>{step.demand_trend}</strong>
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="text-sm font-black text-slate-900">{step.score.toFixed(1)}</div>
                        <div className="text-[10px] text-slate-400">Score / 100</div>
                      </div>
                      <ChevronRight className={`w-4 h-4 ${isSelected ? 'text-indigo-600' : 'text-slate-300'}`} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Detailed Explanation Panel (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          {selectedStep ? (
            <>
              {/* Card Header */}
              <div className="border-b border-slate-200 pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-slate-500">
                    Step {selectedStep.step_number} • {selectedStep.timestamp.slice(11, 19)}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-slate-500">Uncertainty:</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        selectedStep.uncertainty === 'low'
                          ? 'bg-emerald-100 text-emerald-700'
                          : selectedStep.uncertainty === 'medium'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-rose-100 text-rose-700'
                      }`}
                    >
                      {selectedStep.uncertainty}
                    </span>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between">
                  <h3 className="text-lg font-black text-slate-900">{selectedStep.interpretation}</h3>
                  <div className="text-right">
                    <span className="text-2xl font-black text-indigo-600">{selectedStep.score.toFixed(1)}</span>
                    <span className="text-xs text-slate-400 font-medium">/100</span>
                  </div>
                </div>
              </div>

              {/* Baseline Comparison Grid */}
              <div className="bg-slate-50 rounded-lg p-3.5 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 text-[11px] block">Expected Normal Supply</span>
                  <strong className="text-slate-900 text-sm">
                    {selectedStep.baseline_comparison.expected_supply} drivers
                  </strong>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Observed Active Supply</span>
                  <strong
                    className={`text-sm ${
                      selectedStep.baseline_comparison.supply_delta_pct > 0.2
                        ? 'text-rose-600 font-bold'
                        : 'text-slate-900'
                    }`}
                  >
                    {selectedStep.baseline_comparison.observed_supply} drivers (
                    {selectedStep.baseline_comparison.supply_delta_pct > 0 ? '-' : '+'}
                    {Math.abs(selectedStep.baseline_comparison.supply_delta_pct * 100).toFixed(0)}%)
                  </strong>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Expected Normal Demand</span>
                  <strong className="text-slate-900 text-sm">
                    {selectedStep.baseline_comparison.expected_demand} rides
                  </strong>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Observed Demand Trend</span>
                  <strong className="text-slate-900 text-sm">{selectedStep.demand_trend}</strong>
                </div>
              </div>

              {/* Top Contributing Signals */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Top Contributing Signals</h4>
                <div className="space-y-1.5">
                  {selectedStep.top_signals.map((sig, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg border border-slate-100 bg-white shadow-xs flex items-center justify-between text-xs"
                    >
                      <div>
                        <span className="font-semibold text-slate-800">{sig.name}</span>
                        <p className="text-[11px] text-slate-500">{sig.description}</p>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          sig.direction === 'supporting'
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : sig.direction === 'weakening'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-slate-50 text-slate-600'
                        }`}
                      >
                        {sig.direction === 'supporting' ? '+ Anomaly' : sig.direction === 'weakening' ? '- Discounter' : 'Neutral'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Supporting Evidence */}
              {selectedStep.supporting_reasons.length > 0 && (
                <div className="space-y-1.5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-rose-700 flex items-center gap-1">
                    <TrendingDown className="w-3.5 h-3.5" /> Signals Supporting Investigation
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-700 bg-rose-50/60 p-3 rounded-lg border border-rose-100">
                    {selectedStep.supporting_reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-rose-500 font-bold">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Weakening Evidence (Counter-Evidence) */}
              {selectedStep.weakening_reasons.length > 0 && (
                <div className="space-y-1.5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-700 flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5" /> Counter-Evidence &amp; Mitigating Factors
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-700 bg-emerald-50/60 p-3 rounded-lg border border-emerald-100">
                    {selectedStep.weakening_reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-500 font-bold">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Prototype Limitations Disclaimer */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-500 leading-relaxed">
                <Info className="w-3.5 h-3.5 text-slate-400 inline mr-1" />
                <strong>Research Prototype Limitation:</strong> {selectedStep.caveat}
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-xs text-slate-400 space-y-2">
              <HelpCircle className="w-8 h-8 text-slate-300 mx-auto" />
              <p>Select any step from the list on the left to inspect its explainable feature signals and counter-evidence.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlertsPage;
