import { Activity, Database, Cpu } from 'lucide-react';
import type { HealthResponse } from '../lib/types';

interface HealthStatusBadgeProps {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
}

/**
 * Maps the backend model_status literal to a human-readable label.
 *
 * Backend semantics (health.py):
 *   loaded      — forecaster.pkl + isolation_forest.pkl both present on disk.
 *                 Anomaly detection (Isolation Forest) + Baseline Forecaster are operational.
 *   not_loaded  — One or both artifact files missing; assessment endpoints are unavailable.
 *   fallback    — Artifacts found but a non-critical load warning occurred; running in degraded mode.
 *   ready       — Full production-ready state (not currently used in demo builds).
 */
function modelStatusLabel(status: HealthResponse['model_status']): string {
  switch (status) {
    case 'loaded':
      return 'Anomaly + Forecasting';
    case 'ready':
      return 'All Models Ready';
    case 'fallback':
      return 'Fallback Mode';
    case 'not_loaded':
      return 'Artifacts Missing';
    default:
      return status;
  }
}

function modelStatusColor(status: HealthResponse['model_status']): string {
  switch (status) {
    case 'loaded':
    case 'ready':
      return 'bg-mint-100/60 text-brand-900 border-mint-200';
    case 'fallback':
      return 'bg-amber-50 text-amber-800 border-amber-200';
    case 'not_loaded':
      return 'bg-rose-50 text-rose-700 border-rose-200';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

export const HealthStatusBadge: React.FC<HealthStatusBadgeProps> = ({ health, loading, error }) => {
  if (loading) {
    return (
      <div className="flex items-center space-x-2 text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
        <span className="w-2 h-2 rounded-full bg-slate-400 animate-pulse" />
        <span>Connecting to backend...</span>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="flex items-center space-x-2 text-xs text-rose-700 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200">
        <span className="w-2 h-2 rounded-full bg-rose-500" />
        <span>Backend Offline ({error || 'Unknown'})</span>
      </div>
    );
  }

  const isHealthy = health.status === 'healthy';
  const isDemoDb = health.database_status === 'local_demo_mode';

  return (
    <div className="flex items-center space-x-3 text-xs">
      <div className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md border ${
        isHealthy ? 'bg-mint-100/60 text-brand-900 border-mint-200' : 'bg-amber-50 text-amber-800 border-amber-200'
      }`}>
        <Activity className="w-3.5 h-3.5 text-brand-700" />
        <span className="font-medium">API: {health.status}</span>
        <span className="text-slate-400">|</span>
        <span className="text-slate-600 font-mono text-[11px]">v{health.version}</span>
      </div>

      <div className={`hidden sm:flex items-center space-x-1.5 px-2 py-1 rounded-md border ${modelStatusColor(health.model_status)}`}>
        <Cpu className="w-3 h-3" />
        <span className="text-[11px]">
          Models: {modelStatusLabel(health.model_status)}
        </span>
      </div>

      <div className="hidden sm:flex items-center space-x-1.5 px-2 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
        <Database className="w-3 h-3 text-slate-500" />
        <span className="text-[11px]">
          {isDemoDb ? 'Demo DB (in-memory)' : `DB: ${health.database_status}`}
        </span>
      </div>
    </div>
  );
};
