import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  SkipBack,
  SkipForward,
  Download,
  AlertTriangle,
  Info,
  Car,
  Users,
  DollarSign,
  Clock,
  CheckCircle,
  Activity,
  Layers,
  Sparkles,
  ChevronDown,
  ChevronUp,
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
import { apiClient, SurgeGuardApiError } from '../../lib/api-client';
import type {
  ScenarioDefinition,
  ScenarioType,
  SimulationCreateRequest,
  SimulationRunResponse,
  SimulationStep,
} from '../../lib/types';

const ZONE_OPTIONS = [
  { id: 'zone_midtown_core', name: 'Midtown Core (High Volume)' },
  { id: 'zone_downtown_financial', name: 'Downtown Financial (Commuter Hub)' },
  { id: 'zone_airport_terminal', name: 'Airport Terminal (Steady Queue)' },
  { id: 'zone_uptown_residential', name: 'Uptown Residential (Dispersed)' },
];

export const DigitalTwinPage: React.FC = () => {
  // Scenario Config States
  const [scenarios, setScenarios] = useState<ScenarioDefinition[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('unusual_supply_drop');
  const [selectedZone, setSelectedZone] = useState<string>('zone_midtown_core');
  const [durationMinutes, setDurationMinutes] = useState<number>(120);
  const [eventIntensity, setEventIntensity] = useState<number>(0.75);
  const [seed, setSeed] = useState<number>(42);

  // Simulation Execution States
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentRun, setCurrentRun] = useState<SimulationRunResponse | null>(null);
  const [steps, setSteps] = useState<SimulationStep[]>([]);

  // Replay & Scrubber States
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1); // 1x, 2x, 5x
  const [showDataTable, setShowDataTable] = useState<boolean>(false);

  const animationTimerRef = useRef<number | null>(null);

  // Load available scenarios on mount
  useEffect(() => {
    async function loadScenarios() {
      try {
        const scList = await apiClient.getScenarios();
        setScenarios(scList);
      } catch (err) {
        console.warn('Could not load scenarios list from backend:', err);
      }
    }
    loadScenarios();
  }, []);

  // Run initial default simulation on load so the user immediately sees charts
  useEffect(() => {
    handleRunSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Scrubber playback timer
  useEffect(() => {
    if (isPlaying && steps.length > 0) {
      const intervalMs = Math.max(80, 600 / playbackSpeed);
      animationTimerRef.current = window.setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev >= steps.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    } else {
      if (animationTimerRef.current) {
        clearInterval(animationTimerRef.current);
        animationTimerRef.current = null;
      }
    }

    return () => {
      if (animationTimerRef.current) {
        clearInterval(animationTimerRef.current);
      }
    };
  }, [isPlaying, steps, playbackSpeed]);

  const handleRunSimulation = async () => {
    setLoading(true);
    setError(null);
    setIsPlaying(false);

    try {
      const payload: SimulationCreateRequest = {
        scenario_type: selectedScenario,
        zone_id: selectedZone,
        duration_minutes: durationMinutes,
        event_intensity: eventIntensity,
        seed: seed,
      };

      const runRes = await apiClient.createSimulation(payload);
      const stepRecords = await apiClient.getSimulationSteps(runRes.run_id);
      try {
        localStorage.setItem('surgeguard_last_run_id', runRes.run_id);
      } catch {
        // ignore storage errors
      }

      setCurrentRun(runRes);
      setSteps(stepRecords);
      setCurrentStepIndex(0);
    } catch (err) {
      const msg =
        err instanceof SurgeGuardApiError
          ? `${err.error_code}: ${err.message}`
          : err instanceof Error
          ? err.message
          : 'Failed to run simulation';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleResetScrubber = () => {
    setIsPlaying(false);
    setCurrentStepIndex(0);
  };

  const handleStepBack = () => {
    setIsPlaying(false);
    setCurrentStepIndex((prev) => Math.max(0, prev - 1));
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    setCurrentStepIndex((prev) => Math.min(steps.length - 1, prev + 1));
  };

  const activeStep: SimulationStep | null =
    steps.length > 0 && currentStepIndex < steps.length
      ? steps[currentStepIndex]
      : null;

  const currentAnnotation = activeStep?.annotation;

  return (
    <div className="space-y-6">
      {/* Page Title & Synthetic Disclaimer */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-800 text-xs font-semibold mb-2 border border-brand-200">
              <span className="w-2 h-2 rounded-full bg-brand-600 animate-pulse"></span>
              <span>Digital Twin Simulation Engine</span>
              <span className="text-slate-400">|</span>
              <span className="font-mono text-[11px] text-brand-900 uppercase">Deterministic Sandbox</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Marketplace Digital Twin
            </h1>
            <p className="text-sm text-slate-600 mt-1 max-w-3xl">
              Model changes in passenger ride requests, driver availability, dispatch wait times, and surge fare pressure in a controlled stochastic environment.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-100 text-amber-900 border border-amber-300">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
              <span>SYNTHETIC DEMO DATA</span>
            </span>
            {currentRun && (
              <div className="flex space-x-2">
                <a
                  href={apiClient.getExportUrl(currentRun.run_id, 'csv')}
                  download
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium border border-slate-300 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>CSV</span>
                </a>
                <a
                  href={apiClient.getExportUrl(currentRun.run_id, 'json')}
                  download
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium border border-slate-300 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>JSON</span>
                </a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Simulator Control Panel */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-brand-700" />
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
              Simulation Parameters
            </h2>
          </div>
          <span className="text-xs text-slate-400">
            Ground-Truth Label: <strong className="text-slate-700 font-mono">{selectedScenario}</strong>
          </span>
        </div>

        {/* Scenario Archetype Selector Cards */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-2">
            1. Select Scenario Archetype ({scenarios.length || 4} Available from API)
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              {
                id: 'normal_marketplace' as ScenarioType,
                title: 'Normal Marketplace',
                desc: 'Ordinary fluctuations in demand and driver supply near equilibrium.',
                tag: 'Normal Control',
                color: 'border-slate-200',
              },
              {
                id: 'demand_led_surge' as ScenarioType,
                title: 'Demand-Led Surge',
                desc: 'Sharp passenger request spike; delayed organic driver repositioning.',
                tag: 'Event Surge',
                color: 'border-blue-200',
              },
              {
                id: 'natural_shortage' as ScenarioType,
                title: 'Natural Shortage',
                desc: 'Severe rainstorm: simultaneous demand rise (+35%) and supply drop (-45%).',
                tag: 'Weather Shock',
                color: 'border-cyan-200',
              },
              {
                id: 'unusual_supply_drop' as ScenarioType,
                title: 'Unusual Supply Drop',
                desc: 'Precipitous driver drop (-60%) with flat demand; controlled anomaly.',
                tag: 'Injected Anomaly',
                color: 'border-rose-200',
              },
            ].map((sc) => {
              const isSelected = selectedScenario === sc.id;
              return (
                <div
                  key={sc.id}
                  onClick={() => setSelectedScenario(sc.id)}
                  className={`p-3.5 rounded-lg border-2 cursor-pointer transition-all ${
                    isSelected
                      ? 'border-brand-900 bg-brand-50/40 shadow-sm'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-semibold text-xs text-slate-900">{sc.title}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                        isSelected
                          ? 'bg-brand-900 text-white'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {sc.tag}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                    {sc.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Controls Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          {/* Zone Selector */}
          <div>
            <label className="block font-semibold text-slate-700 mb-1.5">
              2. Zone Location
            </label>
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-brand-700"
            >
              {ZONE_OPTIONS.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            </select>
          </div>

          {/* Duration Selector */}
          <div>
            <label className="block font-semibold text-slate-700 mb-1.5">
              3. Duration (Steps / Minutes)
            </label>
            <select
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-brand-700"
            >
              <option value={60}>60 Minutes (1 Hour)</option>
              <option value={120}>120 Minutes (2 Hours - Standard)</option>
              <option value={180}>180 Minutes (3 Hours)</option>
              <option value={240}>240 Minutes (4 Hours)</option>
            </select>
          </div>

          {/* Intensity Slider */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="font-semibold text-slate-700">
                4. Shock Intensity
              </label>
              <span className="font-mono text-[11px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded">
                {Math.round(eventIntensity * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.2"
              max="1.0"
              step="0.05"
              value={eventIntensity}
              onChange={(e) => setEventIntensity(Number(e.target.value))}
              className="w-full accent-brand-900 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>Mild (20%)</span>
              <span>Extreme (100%)</span>
            </div>
          </div>

          {/* Random Seed Control */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="font-semibold text-slate-700">
                5. Random Seed
              </label>
              <span className="text-[10px] text-slate-400">Reproducible</span>
            </div>
            <div className="flex space-x-1.5">
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-brand-700"
              />
              <button
                type="button"
                onClick={() => setSeed(Math.floor(Math.random() * 9000) + 1000)}
                title="Generate Random Seed"
                className="px-2.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium border border-slate-300"
              >
                <Sparkles className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setSeed(42)}
                title="Reset to default seed 42"
                className="px-2.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-mono border border-slate-300"
              >
                42
              </button>
            </div>
          </div>
        </div>

        {/* Run Button & Error Banner */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <div className="text-xs text-slate-500 flex items-center space-x-2">
            <Info className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <span>
              Deterministic seed generates identical traces across backend runs. Data stored in-memory for session.
            </span>
          </div>

          <button
            onClick={handleRunSimulation}
            disabled={loading}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-2.5 bg-brand-900 hover:bg-brand-950 text-white rounded-lg text-sm font-semibold transition-all shadow-sm disabled:opacity-50"
          >
            <Activity className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Running Simulation...' : 'Run Simulation'}</span>
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Summary Metrics Cards */}
      {currentRun && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-medium uppercase">Avg Demand</span>
              <Users className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-xl font-bold text-slate-900">
              {currentRun.summary_metrics.average_demand}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Peak: <strong>{currentRun.summary_metrics.peak_demand}</strong> req/m
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-medium uppercase">Avg Supply</span>
              <Car className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-xl font-bold text-slate-900">
              {currentRun.summary_metrics.average_supply}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Min: <strong>{currentRun.summary_metrics.min_supply}</strong> drivers
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-medium uppercase">Peak Fare Surge</span>
              <DollarSign className="w-4 h-4 text-brand-700" />
            </div>
            <div
              className={`text-xl font-bold ${
                currentRun.summary_metrics.peak_fare_pressure > 140
                  ? 'text-rose-700'
                  : 'text-slate-900'
              }`}
            >
              {currentRun.summary_metrics.peak_fare_pressure}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Avg: <strong>{currentRun.summary_metrics.average_fare_pressure}</strong> (base 100)
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-medium uppercase">Avg Wait Time</span>
              <Clock className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-xl font-bold text-slate-900">
              {currentRun.summary_metrics.average_wait_time_minutes}m
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Max: <strong>{currentRun.summary_metrics.max_wait_time_minutes}m</strong> latency
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-medium uppercase">Fulfillment</span>
              <CheckCircle className="w-4 h-4 text-brand-700" />
            </div>
            <div className="text-xl font-bold text-slate-900">
              {currentRun.summary_metrics.fulfillment_rate_pct}%
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {currentRun.summary_metrics.total_completed_rides.toLocaleString()} rides completed
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-medium uppercase">Deficit Steps</span>
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            </div>
            <div
              className={`text-xl font-bold ${
                currentRun.summary_metrics.critical_steps_count > 0
                  ? 'text-amber-700'
                  : 'text-slate-900'
              }`}
            >
              {currentRun.summary_metrics.critical_steps_count}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              of {currentRun.total_steps} minutes duration
            </div>
          </div>
        </div>
      )}

      {/* Interactive Timeline Scrubber & Replay Bar */}
      {steps.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-1">
                <button
                  onClick={handleResetScrubber}
                  title="Reset to Step 0"
                  className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 border border-slate-200"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button
                  onClick={handleStepBack}
                  title="Step Backward"
                  className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 border border-slate-200"
                >
                  <SkipBack className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  title={isPlaying ? 'Pause' : 'Play Replay'}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-brand-900 hover:bg-brand-950 text-white text-xs font-semibold"
                >
                  {isPlaying ? (
                    <>
                      <Pause className="w-3.5 h-3.5" />
                      <span>Pause</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Play Replay</span>
                    </>
                  )}
                </button>
                <button
                  onClick={handleStepForward}
                  title="Step Forward"
                  className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 border border-slate-200"
                >
                  <SkipForward className="w-4 h-4" />
                </button>
              </div>

              {/* Speed Toggles */}
              <div className="flex items-center rounded-lg border border-slate-200 p-0.5 text-[11px] font-mono">
                {[1, 2, 5].map((speed) => (
                  <button
                    key={speed}
                    onClick={() => setPlaybackSpeed(speed)}
                    className={`px-2 py-0.5 rounded ${
                      playbackSpeed === speed
                        ? 'bg-slate-900 text-white font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>

            {/* Current Step Telemetry Badge */}
            {activeStep && (
              <div className="flex items-center space-x-4 text-xs">
                <div className="font-mono bg-slate-100 text-slate-800 px-2.5 py-1 rounded-md border border-slate-200">
                  Step <strong>{activeStep.step_number}</strong> / {steps.length - 1} min
                </div>
                <div className="hidden sm:block text-slate-500 font-mono text-[11px]">
                  {new Date(activeStep.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-slate-500">Ratio:</span>
                  <span
                    className={`font-mono font-bold px-1.5 py-0.5 rounded ${
                      activeStep.supply_demand_ratio < 0.8
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-mint-100 text-brand-900'
                    }`}
                  >
                    {activeStep.supply_demand_ratio}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Timeline Range Slider */}
          <div className="space-y-1">
            <input
              type="range"
              min={0}
              max={steps.length - 1}
              value={currentStepIndex}
              onChange={(e) => {
                setIsPlaying(false);
                setCurrentStepIndex(Number(e.target.value));
              }}
              className="w-full accent-brand-900 cursor-pointer h-2 bg-slate-200 rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>0m (Onset)</span>
              <span>{Math.floor(steps.length / 2)}m (Midpoint)</span>
              <span>{steps.length - 1}m (End)</span>
            </div>
          </div>

          {/* Dynamic Annotation Banner */}
          {currentAnnotation && (
            <div className="p-3 bg-mint-50 border border-mint-200 rounded-lg flex items-center space-x-2 text-xs text-brand-900 animate-fadeIn">
              <Info className="w-4 h-4 text-brand-700 flex-shrink-0" />
              <span>
                <strong>Event Annotation (Minute {activeStep?.step_number}):</strong>{' '}
                {currentAnnotation}
              </span>
            </div>
          )}

          {/* Live Step Gauge Cards */}
          {activeStep && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[10px]">Requests</span>
                <span className="font-bold text-slate-900 text-sm font-mono">
                  {activeStep.ride_requests}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[10px]">Available Supply</span>
                <span className="font-bold text-slate-900 text-sm font-mono">
                  {activeStep.available_drivers}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[10px]">Wait Time</span>
                <span className="font-bold text-slate-900 text-sm font-mono">
                  {activeStep.estimated_wait_time_minutes} min
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[10px]">Fare Pressure</span>
                <span
                  className={`font-bold text-sm font-mono ${
                    activeStep.fare_pressure_index > 130 ? 'text-rose-700' : 'text-slate-900'
                  }`}
                >
                  {activeStep.fare_pressure_index}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 col-span-2 sm:col-span-1">
                <span className="text-slate-400 block text-[10px]">Earnings Index</span>
                <span className="font-bold text-slate-900 text-sm font-mono">
                  {activeStep.driver_earnings_index}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Synchronized Analytical Charts */}
      {steps.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Passenger Demand vs Available Drivers */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900 text-sm">
                  Passenger Requests vs. Available Drivers
                </h3>
                <p className="text-xs text-slate-500">
                  Demand volume (requests/min) against active online driver supply
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">Time Series</span>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={steps} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorDemand" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0f4c3a" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#0f4c3a" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="colorSupply" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="step_number"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={(val) => `${val}m`}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderColor: '#e2e8f0',
                      borderRadius: '0.5rem',
                      fontSize: '12px',
                    }}
                    labelFormatter={(label) => `Minute ${label}`}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
                    iconType="circle"
                  />
                  {activeStep && (
                    <ReferenceLine
                      x={activeStep.step_number}
                      stroke="#dc2626"
                      strokeDasharray="3 3"
                      label={{ value: 'Scrubber', fill: '#dc2626', fontSize: 10 }}
                    />
                  )}
                  <Area
                    type="monotone"
                    dataKey="ride_requests"
                    name="Ride Requests (Demand)"
                    stroke="#0f4c3a"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorDemand)"
                  />
                  <Area
                    type="monotone"
                    dataKey="available_drivers"
                    name="Available Drivers (Supply)"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorSupply)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Fare Pressure Index & Wait Time */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900 text-sm">
                  Fare Pressure Index &amp; Dispatch Wait Time
                </h3>
                <p className="text-xs text-slate-500">
                  Surge pressure multiplier (baseline 100) and passenger wait latency
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">Market Outcomes</span>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={steps} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="step_number"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={(val) => `${val}m`}
                  />
                  {/* Left Y Axis: Fare Pressure */}
                  <YAxis
                    yAxisId="left"
                    domain={[80, 'auto']}
                    tick={{ fontSize: 11, fill: '#b45309' }}
                  />
                  {/* Right Y Axis: Wait Time */}
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[0, 'auto']}
                    tick={{ fontSize: 11, fill: '#64748b' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderColor: '#e2e8f0',
                      borderRadius: '0.5rem',
                      fontSize: '12px',
                    }}
                    labelFormatter={(label) => `Minute ${label}`}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
                    iconType="circle"
                  />
                  <ReferenceLine
                    yAxisId="left"
                    y={100}
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                    label={{ value: 'Base 100', fill: '#94a3b8', fontSize: 10 }}
                  />
                  {activeStep && (
                    <ReferenceLine
                      yAxisId="left"
                      x={activeStep.step_number}
                      stroke="#dc2626"
                      strokeDasharray="3 3"
                    />
                  )}
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="fare_pressure_index"
                    name="Fare Pressure Index"
                    stroke="#d97706"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="estimated_wait_time_minutes"
                    name="Wait Time (min)"
                    stroke="#64748b"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Telemetry Data Table Drawer */}
      {steps.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div
            onClick={() => setShowDataTable(!showDataTable)}
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-sm text-slate-900">
                Raw Simulation Telemetry Records ({steps.length} rows)
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {currentRun?.storage_type === 'in_memory_demo' ? 'In-Memory Store' : 'Database'}
              </span>
            </div>
            <button className="text-slate-500 hover:text-slate-800">
              {showDataTable ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {showDataTable && (
            <div className="border-t border-slate-100 overflow-x-auto max-h-96">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-[11px] font-semibold text-slate-700 uppercase tracking-wider sticky top-0 border-b border-slate-200">
                  <tr>
                    <th className="px-3 py-2">Step</th>
                    <th className="px-3 py-2">Time</th>
                    <th className="px-3 py-2">Requests</th>
                    <th className="px-3 py-2">Drivers</th>
                    <th className="px-3 py-2">Ratio</th>
                    <th className="px-3 py-2">Completed</th>
                    <th className="px-3 py-2">Fare Index</th>
                    <th className="px-3 py-2">Wait (m)</th>
                    <th className="px-3 py-2">Earnings</th>
                    <th className="px-3 py-2">Context</th>
                    <th className="px-3 py-2">Ground Truth</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                  {steps.map((st) => {
                    const isSelected = st.step_number === currentStepIndex;
                    return (
                      <tr
                        key={st.step_number}
                        onClick={() => setCurrentStepIndex(st.step_number)}
                        className={`hover:bg-slate-50 cursor-pointer ${
                          isSelected ? 'bg-mint-50/70 font-semibold text-brand-950' : ''
                        }`}
                      >
                        <td className="px-3 py-1.5">{st.step_number}</td>
                        <td className="px-3 py-1.5">
                          {new Date(st.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="px-3 py-1.5">{st.ride_requests}</td>
                        <td className="px-3 py-1.5">{st.available_drivers}</td>
                        <td className="px-3 py-1.5">{st.supply_demand_ratio}</td>
                        <td className="px-3 py-1.5">{st.completed_rides}</td>
                        <td className="px-3 py-1.5">{st.fare_pressure_index}</td>
                        <td className="px-3 py-1.5">{st.estimated_wait_time_minutes}</td>
                        <td className="px-3 py-1.5">{st.driver_earnings_index}</td>
                        <td className="px-3 py-1.5 font-sans text-slate-500">{st.context_type}</td>
                        <td className="px-3 py-1.5">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] ${
                              st.ground_truth_label === 'unusual_supply_drop'
                                ? 'bg-rose-100 text-rose-800'
                                : st.ground_truth_label === 'natural_shortage'
                                ? 'bg-cyan-100 text-cyan-800'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {st.ground_truth_label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
