import React, { useEffect, useState } from 'react';
import {
  Car,
  Users,
  Activity,
  Clock,
  Server,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ShieldAlert,
  ChevronRight,
  ArrowUpRight,
  Play,
  Cpu,
  LineChart as LineChartIcon,
  AlertOctagon,
  Sparkles,
  MapPin,
  Scale,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { apiClient, SurgeGuardApiError } from '../lib/api-client';
import type {
  HealthResponse,
  SimulationRunResponse,
  SimulationStep,
  StepAssessment,
  ScenarioType,
} from '../lib/types';
import type { ActiveTab } from '../components/Sidebar';

interface OverviewProps {
  onHealthLoaded?: (health: HealthResponse | null, error: string | null) => void;
  onNavigate?: (tab: ActiveTab) => void;
}

const ZONE_OPTIONS = [
  { id: 'zone_midtown_core', name: 'Midtown Core', profile: 'High Volume Commercial' },
  { id: 'zone_downtown_financial', name: 'Downtown Financial', profile: 'Commuter & Business Hub' },
  { id: 'zone_airport_terminal', name: 'Airport Terminal', profile: 'Steady Long-Queue Hub' },
  { id: 'zone_uptown_residential', name: 'Uptown Residential', profile: 'Dispersed Neighborhood' },
];

const SCENARIO_OPTIONS: { id: ScenarioType; name: string; description: string }[] = [
  {
    id: 'unusual_supply_drop',
    name: 'Unusual Supply Drop (Target Anomaly)',
    description: 'Sudden, coordinated withdrawal of driver supply while demand remains high.',
  },
  {
    id: 'natural_shortage',
    name: 'Natural Weather Shortage (Organic)',
    description: 'Adverse weather causing organic supply reduction and demand dampening.',
  },
  {
    id: 'demand_led_surge',
    name: 'Demand-Led Surge (Normal Peak)',
    description: 'Spike in ride requests during major event with normal driver supply response.',
  },
  {
    id: 'normal_marketplace',
    name: 'Normal Marketplace (Equilibrium)',
    description: 'Standard baseline equilibrium between passenger demand and driver supply.',
  },
];

export const OverviewPage: React.FC<OverviewProps> = ({ onHealthLoaded, onNavigate }) => {
  // System Health States
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  // Operational Simulation Telemetry States
  const [currentRun, setCurrentRun] = useState<SimulationRunResponse | null>(null);
  const [simulationSteps, setSimulationSteps] = useState<SimulationStep[] | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<StepAssessment[]>([]);
  const [simLoading, setSimLoading] = useState<boolean>(false);
  const [simError, setSimError] = useState<string | null>(null);

  // Quick Simulation Config
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('unusual_supply_drop');
  const [selectedZone, setSelectedZone] = useState<string>('zone_midtown_core');

  // Check Backend Health
  const checkHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await apiClient.getHealth();
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString());
      onHealthLoaded?.(data, null);
    } catch (err) {
      const message =
        err instanceof SurgeGuardApiError
          ? `${err.error_code}: ${err.message}`
          : err instanceof Error
          ? err.message
          : 'Unknown connection error';
      setHealthError(message);
      setHealth(null);
      setLastChecked(new Date().toLocaleTimeString());
      onHealthLoaded?.(null, message);
    } finally {
      setHealthLoading(false);
    }
  };

  // Fetch Session Alerts
  const fetchAlerts = async () => {
    try {
      const alerts = await apiClient.listAlerts({ min_score: 30 });
      setRecentAlerts(alerts);
    } catch {
      // If no alerts or backend not yet populated, keep empty
      setRecentAlerts([]);
    }
  };

  // Run Quick Simulation directly from Overview
  const handleRunSimulation = async (scenario = selectedScenario, zone = selectedZone) => {
    setSimLoading(true);
    setSimError(null);
    try {
      const runRes = await apiClient.createSimulation({
        scenario_type: scenario,
        zone_id: zone,
        duration_minutes: 120,
        event_intensity: 0.75,
        seed: 42,
      });

      const stepRecords = await apiClient.getSimulationSteps(runRes.run_id);
      try {
        localStorage.setItem('surgeguard_last_run_id', runRes.run_id);
      } catch {
        // ignore storage errors
      }

      setCurrentRun(runRes);
      setSimulationSteps(stepRecords);

      // Trigger assessment for anomaly detection
      try {
        await apiClient.assessRun(runRes.run_id);
      } catch {
        // non-blocking
      }

      await fetchAlerts();
    } catch (err) {
      const message =
        err instanceof SurgeGuardApiError
          ? `${err.error_code}: ${err.message}`
          : err instanceof Error
          ? err.message
          : 'Failed to execute simulation';
      setSimError(message);
    } finally {
      setSimLoading(false);
    }
  };

  // On mount: check health, fetch alerts, and load stored run if available
  useEffect(() => {
    checkHealth();
    fetchAlerts();

    const storedRunId = (() => {
      try {
        return localStorage.getItem('surgeguard_last_run_id');
      } catch {
        return null;
      }
    })();

    if (storedRunId) {
      (async () => {
        try {
          const runRes = await apiClient.getSimulationSummary(storedRunId);
          const steps = await apiClient.getSimulationSteps(storedRunId);
          setCurrentRun(runRes);
          setSimulationSteps(steps);
        } catch {
          // If stored run is expired/missing on server, remove from storage
          try {
            localStorage.removeItem('surgeguard_last_run_id');
          } catch {
            // ignore
          }
        }
      })();
    }
  }, []);

  // Compute operational KPI metrics from active simulation
  const metrics = currentRun?.summary_metrics;
  const latestStep =
    simulationSteps && simulationSteps.length > 0
      ? simulationSteps[simulationSteps.length - 1]
      : null;

  const availableDrivers = latestStep ? latestStep.available_drivers : null;
  const rideRequests = latestStep ? latestStep.ride_requests : null;
  const supplyDemandGap =
    availableDrivers !== null && rideRequests !== null ? availableDrivers - rideRequests : null;
  const estimatedWait = latestStep ? latestStep.estimated_wait_time_minutes : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Product Heading Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-mint-50 text-brand-900 text-xs font-semibold mb-2 border border-mint-200">
              <span className="w-2 h-2 rounded-full bg-brand-600 animate-pulse"></span>
              <span>Marketplace Intelligence Platform</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Marketplace Overview
            </h1>
            <p className="text-sm text-slate-600 mt-1 max-w-3xl">
              Real-time marketplace monitoring, supply-demand gap tracking, and explainable
              anomaly detection across urban ride-hailing networks.
            </p>
          </div>

          <div className="flex items-center space-x-3 self-start md:self-auto flex-wrap gap-2">
            <button
              onClick={checkHealth}
              disabled={healthLoading}
              className="inline-flex items-center space-x-2 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
              title="Ping backend API health status"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${healthLoading ? 'animate-spin' : ''}`} />
              <span>Ping API</span>
            </button>
            <button
              onClick={() => handleRunSimulation()}
              disabled={simLoading}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-brand-900 hover:bg-brand-950 text-white rounded-lg text-xs font-medium transition-colors shadow-sm disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 ${simLoading ? 'animate-spin' : ''}`} />
              <span>{simLoading ? 'Simulating...' : 'Simulate Scenario'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Operational Analytics KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Available Drivers */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Available Drivers</span>
            <div className="w-8 h-8 rounded-lg bg-mint-50 text-brand-800 flex items-center justify-center">
              <Car className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900">
              {availableDrivers !== null ? availableDrivers.toLocaleString() : '—'}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              {metrics
                ? `Avg supply: ${Math.round(metrics.average_supply)} · Min: ${metrics.min_supply}`
                : 'Awaiting simulation telemetry'}
            </p>
          </div>
        </div>

        {/* Ride Requests */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Ride Requests</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900">
              {rideRequests !== null ? rideRequests.toLocaleString() : '—'}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              {metrics
                ? `Avg demand: ${Math.round(metrics.average_demand)} · Peak: ${metrics.peak_demand}`
                : 'Awaiting simulation telemetry'}
            </p>
          </div>
        </div>

        {/* Supply-Demand Gap */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Supply-Demand Gap</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-black text-slate-900">
                {supplyDemandGap !== null
                  ? `${supplyDemandGap > 0 ? '+' : ''}${supplyDemandGap.toLocaleString()}`
                  : '—'}
              </span>
              {supplyDemandGap !== null && (
                <span
                  className={`text-[11px] font-semibold px-1.5 py-0.5 rounded ${
                    supplyDemandGap < 0
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-emerald-100 text-emerald-800'
                  }`}
                >
                  {supplyDemandGap < 0 ? 'Deficit' : 'Surplus'}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              {metrics
                ? `Fulfillment: ${metrics.fulfillment_rate_pct.toFixed(1)}%`
                : 'Awaiting simulation telemetry'}
            </p>
          </div>
        </div>

        {/* Estimated Waiting Time */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Est. Wait Time</span>
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900">
              {estimatedWait !== null ? `${estimatedWait.toFixed(1)} min` : '—'}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              {metrics
                ? `Avg wait: ${metrics.average_wait_time_minutes.toFixed(1)}m · Max: ${metrics.max_wait_time_minutes.toFixed(1)}m`
                : 'Awaiting simulation telemetry'}
            </p>
          </div>
        </div>
      </div>

      {/* Active Run Context / Simulation Empty State Bar */}
      {currentRun ? (
        <div className="bg-mint-50/70 border border-mint-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-3">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 flex-shrink-0"></span>
            <div>
              <span className="font-semibold text-brand-900">
                Active Scenario: {currentRun.scenario_name}
              </span>
              <span className="text-slate-500 ml-2">
                Zone: <span className="font-mono text-slate-700">{currentRun.zone_id}</span> ·{' '}
                {currentRun.duration_minutes} min ({currentRun.total_steps} steps) · Seed: {currentRun.seed}
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onNavigate?.('digital-twin')}
              className="inline-flex items-center space-x-1 px-3 py-1.5 bg-white border border-mint-200 hover:bg-mint-50 text-brand-900 rounded-md font-medium text-xs transition-colors shadow-xs"
            >
              <span>Inspect in Digital Twin</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="max-w-2xl mx-auto text-center space-y-4">
            <div className="w-12 h-12 bg-mint-50 text-brand-800 rounded-full flex items-center justify-center mx-auto">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">No Simulation Data Loaded</h3>
              <p className="text-xs text-slate-500 mt-1">
                Marketplace operational metrics require an active simulation run. Run a
                deterministic scenario to generate real-time supply, demand, and anomaly telemetry.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto text-left text-xs">
              <div>
                <label className="block text-slate-500 mb-1 font-medium">Scenario</label>
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value as ScenarioType)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 text-xs focus:ring-1 focus:ring-brand-800"
                >
                  {SCENARIO_OPTIONS.map((sc) => (
                    <option key={sc.id} value={sc.id}>
                      {sc.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-500 mb-1 font-medium">Zone</label>
                <select
                  value={selectedZone}
                  onChange={(e) => setSelectedZone(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 text-xs focus:ring-1 focus:ring-brand-800"
                >
                  {ZONE_OPTIONS.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={() => handleRunSimulation()}
                disabled={simLoading}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-brand-900 hover:bg-brand-950 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors disabled:opacity-50"
              >
                <Play className={`w-3.5 h-3.5 ${simLoading ? 'animate-spin' : ''}`} />
                <span>{simLoading ? 'Simulating...' : 'Run Simulation'}</span>
              </button>
              <button
                onClick={() => onNavigate?.('digital-twin')}
                className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Open Digital Twin</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
            {simError && (
              <p className="text-xs text-rose-600 font-medium">{simError}</p>
            )}
          </div>
        </div>
      )}

      {/* Demand-versus-Supply Time-Series Chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Demand vs. Supply Telemetry</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Time-series trajectory comparing passenger ride requests (demand) and available drivers (supply).
            </p>
          </div>
          {currentRun && (
            <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2.5 py-1 rounded">
              Run: {currentRun.run_id.slice(0, 8)}...
            </span>
          )}
        </div>

        {simulationSteps && simulationSteps.length > 0 ? (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={simulationSteps} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorDemand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorSupply" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f4c3a" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0f4c3a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="step_number"
                  tickFormatter={(val) => `T+${val * 5}m`}
                  stroke="#94a3b8"
                  fontSize={11}
                />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload as SimulationStep;
                      return (
                        <div className="bg-slate-900 text-white p-3 rounded-lg text-xs shadow-xl space-y-1">
                          <p className="font-bold text-mint-300">
                            Step {data.step_number} (T+{data.step_number * 5} min)
                          </p>
                          <p className="flex justify-between gap-4 text-slate-300">
                            <span>Ride Requests:</span>
                            <span className="font-mono font-bold text-indigo-300">{data.ride_requests}</span>
                          </p>
                          <p className="flex justify-between gap-4 text-slate-300">
                            <span>Available Drivers:</span>
                            <span className="font-mono font-bold text-emerald-400">{data.available_drivers}</span>
                          </p>
                          <p className="flex justify-between gap-4 text-slate-300">
                            <span>Est. Wait Time:</span>
                            <span className="font-mono font-bold text-amber-300">{data.estimated_wait_time_minutes.toFixed(1)}m</span>
                          </p>
                          <p className="flex justify-between gap-4 text-slate-300">
                            <span>Fare Pressure:</span>
                            <span className="font-mono font-bold text-slate-100">{data.fare_pressure_index.toFixed(1)}</span>
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend
                  verticalAlign="top"
                  height={36}
                  formatter={(value) => (
                    <span className="text-xs text-slate-600 font-medium">
                      {value === 'ride_requests' ? 'Passenger Demand (Requests)' : 'Driver Supply (Available)'}
                    </span>
                  )}
                />
                <Area
                  type="monotone"
                  dataKey="ride_requests"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorDemand)"
                  name="ride_requests"
                />
                <Area
                  type="monotone"
                  dataKey="available_drivers"
                  stroke="#0f4c3a"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorSupply)"
                  name="available_drivers"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-64 rounded-lg border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-center p-6 bg-slate-50/50">
            <LineChartIcon className="w-10 h-10 text-slate-300 mb-2" />
            <p className="text-xs font-semibold text-slate-600">Demand &amp; Supply Chart Standby</p>
            <p className="text-[11px] text-slate-400 max-w-sm mt-0.5">
              Simulate a scenario or launch the Digital Twin to view dynamic time-series curves.
            </p>
            <button
              onClick={() => handleRunSimulation()}
              disabled={simLoading}
              className="mt-3 inline-flex items-center space-x-1.5 px-3 py-1.5 bg-brand-900 text-white rounded-md text-xs font-medium hover:bg-brand-950 transition-colors"
            >
              <Play className="w-3 h-3" />
              <span>Simulate Now</span>
            </button>
          </div>
        )}
      </div>

      {/* Two-Column Layout: Recent Integrity Alerts & Zone Conditions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Integrity Alerts */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2">
              <AlertOctagon className="w-5 h-5 text-rose-600" />
              <h3 className="font-bold text-slate-900 text-base">Recent Integrity Alerts</h3>
            </div>
            {recentAlerts.length > 0 && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800">
                {recentAlerts.length} Flagged
              </span>
            )}
          </div>

          {recentAlerts.length > 0 ? (
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {recentAlerts.slice(0, 5).map((alert, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg border border-slate-200 bg-slate-50/60 hover:bg-slate-50 transition-colors space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          alert.risk_category === 'investigate'
                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                            : 'bg-amber-100 text-amber-800 border border-amber-200'
                        }`}
                      >
                        {alert.risk_category}
                      </span>
                      <span className="font-semibold text-slate-800">
                        Step {alert.step_number} · {alert.zone_id}
                      </span>
                    </div>
                    <span className="font-mono font-bold text-xs text-rose-700">
                      Score: {alert.score.toFixed(0)}/100
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">{alert.interpretation}</p>
                  {alert.top_signals && alert.top_signals.length > 0 && (
                    <p className="text-[11px] text-slate-400">
                      Primary factor: {alert.top_signals[0].name} ({alert.top_signals[0].description})
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center rounded-lg border border-slate-100 bg-slate-50/50 space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
              <p className="text-xs font-semibold text-slate-700">No Anomaly Alerts Recorded</p>
              <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                No active integrity alerts in current session. Run an anomaly scenario to test detection triggers.
              </p>
              <button
                onClick={() => onNavigate?.('alerts')}
                className="mt-2 text-xs font-medium text-brand-900 hover:underline inline-flex items-center space-x-1"
              >
                <span>Open Integrity Alerts Lab</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Zone-Level Marketplace Conditions */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-bold text-slate-900 text-base">Zone-Level Marketplace Conditions</h3>
            <span className="text-xs text-slate-400">NYC Centroids</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {ZONE_OPTIONS.map((zone) => {
              const isCurrent = currentRun?.zone_id === zone.id;
              return (
                <div
                  key={zone.id}
                  className={`p-3.5 rounded-lg border transition-all ${
                    isCurrent
                      ? 'border-brand-300 bg-mint-50/50 shadow-xs'
                      : 'border-slate-200 bg-slate-50/40'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-bold text-xs text-slate-900 block">{zone.name}</span>
                      <span className="text-[10px] text-slate-500 mt-0.5 block">{zone.profile}</span>
                    </div>
                    <span
                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                        isCurrent
                          ? 'bg-brand-900 text-white'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {isCurrent ? 'Active Run' : 'Standby'}
                    </span>
                  </div>

                  <div className="mt-3 pt-2 border-t border-slate-200/60 text-[11px] flex items-center justify-between text-slate-600">
                    <span>Baseline Status</span>
                    <span className="font-semibold text-brand-800">
                      {isCurrent ? currentRun.scenario_name : 'Equilibrium'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Grid: Model Insights, Quick Actions & Backend Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Model Insights */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-indigo-600" />
            <h3 className="font-bold text-slate-900 text-base">Model Insights</h3>
          </div>
          <p className="text-xs text-slate-500">
            Real-time inference and detector architecture operating across telemetry streams.
          </p>

          <div className="space-y-2 text-xs pt-1">
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
              <span className="text-slate-600">Unsupervised Classifier</span>
              <span className="font-semibold text-slate-900">Isolation Forest (5% Contam.)</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
              <span className="text-slate-600">Baseline Forecaster</span>
              <span className="font-semibold text-slate-900">Moving Median (MAE 5.2)</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
              <span className="text-slate-600">Contextual Rule Engine</span>
              <span className="font-semibold text-slate-900">3-Factor Weighted Scoring</span>
            </div>
          </div>

          <button
            onClick={() => onNavigate?.('model-evaluation')}
            className="w-full mt-2 py-2 text-xs font-semibold text-brand-900 bg-mint-50 hover:bg-mint-100 rounded-lg transition-colors border border-mint-200 flex items-center justify-center space-x-1"
          >
            <span>Inspect Model Evaluation &amp; Benchmarks</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
          <h3 className="font-bold text-slate-900 text-base">Quick Actions</h3>
          <p className="text-xs text-slate-500">
            Jump directly to operational intelligence modules:
          </p>

          <div className="space-y-2 pt-1">
            <button
              onClick={() => onNavigate?.('digital-twin')}
              className="w-full flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-brand-300 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-all text-left"
            >
              <div className="flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-brand-800" />
                <span>Digital Twin Simulator</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </button>

            <button
              onClick={() => onNavigate?.('policy-lab')}
              className="w-full flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40 text-xs font-medium text-slate-700 transition-all text-left"
            >
              <div className="flex items-center space-x-2">
                <Scale className="w-4 h-4 text-emerald-700" />
                <span>What-If Policy Lab</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </button>

            <button
              onClick={() => onNavigate?.('map')}
              className="w-full flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40 text-xs font-medium text-slate-700 transition-all text-left"
            >
              <div className="flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-emerald-700" />
                <span>City Map &amp; Spatial Intel</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </button>

            <button
              onClick={() => onNavigate?.('alerts')}
              className="w-full flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-brand-300 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-all text-left"
            >
              <div className="flex items-center space-x-2">
                <AlertOctagon className="w-4 h-4 text-rose-600" />
                <span>Integrity Alerts &amp; Explanations</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </button>

            <button
              onClick={() => onNavigate?.('model-evaluation')}
              className="w-full flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-brand-300 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-all text-left"
            >
              <div className="flex items-center space-x-2">
                <LineChartIcon className="w-4 h-4 text-indigo-600" />
                <span>Model Evaluation &amp; Baselines</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </button>

            <button
              onClick={() => onNavigate?.('settings')}
              className="w-full flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-brand-300 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-all text-left"
            >
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                <span>Governance &amp; Data Docs</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </button>
          </div>
        </div>

        {/* Runtime & Health Indicators (Preserved) */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Server className="w-5 h-5 text-brand-700" />
              <h3 className="font-bold text-slate-900 text-base">System Telemetry</h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">GET /health</span>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-2.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-600">Service API</span>
              {healthLoading ? (
                <span className="text-slate-400">Checking...</span>
              ) : health ? (
                <span className="inline-flex items-center space-x-1 text-brand-700 font-semibold bg-mint-100 px-2 py-0.5 rounded">
                  <CheckCircle2 className="w-3.5 h-3.5 text-brand-600" />
                  <span>{health.status}</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1 text-rose-700 font-semibold bg-rose-100 px-2 py-0.5 rounded">
                  <XCircle className="w-3.5 h-3.5 text-rose-600" />
                  <span>offline</span>
                </span>
              )}
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-600">API Version</span>
              <span className="font-mono text-slate-800">{health?.version || '—'}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-600">Model Artifacts</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-mono">
                {health?.model_status || 'not_loaded'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-600">Database Layer</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-mono">
                {health?.database_status || 'disconnected'}
              </span>
            </div>
          </div>

          <div className="text-[11px] text-slate-500 flex justify-between items-center pt-2 border-t border-slate-100">
            <span>Mode: <strong className="text-amber-800">Synthetic Demo</strong></span>
            {lastChecked && <span>Checked: {lastChecked}</span>}
          </div>

          {healthError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              <p className="font-semibold">Backend Connection Issue</p>
              <p className="mt-0.5">{healthError}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OverviewPage;
