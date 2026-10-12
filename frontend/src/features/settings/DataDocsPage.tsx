import React, { useState } from 'react';
import {
  BookOpen,
  FileText,
  Database,
  Shield,
  Scale,
} from 'lucide-react';

export const DataDocsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'data_dict' | 'model_card' | 'policy_math' | 'architecture'>('data_dict');

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-200">
              <BookOpen className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Governance &amp; Data Documentation</h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-100/70 text-emerald-800 border border-emerald-200">
              Technical Specifications
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Mathematical formulations, model cards, data dictionaries, and responsible AI governance principles governing the SurgeGuard intelligence platform.
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 bg-white border border-slate-200 p-1.5 rounded-xl shadow-sm overflow-x-auto">
        <button
          onClick={() => setActiveTab('data_dict')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
            activeTab === 'data_dict'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Data Dictionary
        </button>

        <button
          onClick={() => setActiveTab('model_card')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
            activeTab === 'model_card'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          Model Card
        </button>

        <button
          onClick={() => setActiveTab('policy_math')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
            activeTab === 'policy_math'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          Policy Simulation Math
        </button>

        <button
          onClick={() => setActiveTab('architecture')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
            activeTab === 'architecture'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          Architecture &amp; Persistence
        </button>
      </div>

      {/* Tab 1: Data Dictionary */}
      {activeTab === 'data_dict' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">Synthetic Marketplace Data Dictionary</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Definitions, physical units, bounds, and interpretation rules for simulation features.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Field Name</th>
                  <th className="py-2.5 px-3">Data Type</th>
                  <th className="py-2.5 px-3">Unit / Range</th>
                  <th className="py-2.5 px-3">Description &amp; Operational Semantics</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">ride_requests</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">float / int</td>
                  <td className="py-2.5 px-3 font-mono">[5.0, ∞) trips</td>
                  <td className="py-2.5 px-3">Passenger booking intent during a 5-minute sampling interval.</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">available_drivers</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">float / int</td>
                  <td className="py-2.5 px-3 font-mono">[4.0, ∞) vehicles</td>
                  <td className="py-2.5 px-3">Online active drivers located within dispatch range of the zone.</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">completed_rides</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">int</td>
                  <td className="py-2.5 px-3 font-mono">[0, requests]</td>
                  <td className="py-2.5 px-3">Rides dispatched and completed: min(requests, available_drivers * 0.94).</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">unfulfilled_requests</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">int</td>
                  <td className="py-2.5 px-3 font-mono">[0, requests]</td>
                  <td className="py-2.5 px-3">Passenger ride requests that could not be served due to vehicle constraints.</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">supply_demand_ratio</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">float</td>
                  <td className="py-2.5 px-3 font-mono">[0.0, ∞) (safe div)</td>
                  <td className="py-2.5 px-3">available_drivers / max(requests, 1.0). Ratios &lt; 0.85 indicate shortage.</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">estimated_wait_time_minutes</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">float</td>
                  <td className="py-2.5 px-3 font-mono">[2.0, 22.0] mins</td>
                  <td className="py-2.5 px-3">Estimated passenger wait from booking to pickup, scaling non-linearly with deficits.</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">fare_pressure_index</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">float</td>
                  <td className="py-2.5 px-3 font-mono">[88.0, 320.0]</td>
                  <td className="py-2.5 px-3">Algorithmic surge multiplier index benchmarked to 100.0 baseline at equilibrium.</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">anomaly_score</td>
                  <td className="py-2.5 px-3 font-mono text-slate-500">float</td>
                  <td className="py-2.5 px-3 font-mono">[0.0, 100.0]</td>
                  <td className="py-2.5 px-3">Ensemble anomaly score prioritizing unusual supply contractions from organic surges.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Model Card */}
      {activeTab === 'model_card' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">SurgeGuard Model Card</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Ensemble anomaly detection architecture combining rule-based heuristics and Isolation Forest ML.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            <div className="space-y-3">
              <h3 className="font-bold text-slate-900 text-sm">Model Architecture</h3>
              <p className="text-slate-600 leading-relaxed">
                The detector integrates two independent layers:
              </p>
              <ul className="list-disc list-inside space-y-1.5 text-slate-600">
                <li>
                  <strong className="text-slate-900">Rule-Based Diagnostic Layer:</strong> Evaluates supply drop magnitude, sustained duration steps, demand stability, and historical zone variance bounds.
                </li>
                <li>
                  <strong className="text-slate-900">Unsupervised Isolation Forest:</strong> 100 estimators trained on engineered rolling features (supply trend, rolling volatility, forecast deviation).
                </li>
                <li>
                  <strong className="text-slate-900">Weighted Risk Ensemble:</strong> Final score S = 0.65 * S_rule + 0.35 * S_ml, calibrated to prioritize unusual supply drops over natural weather shortages.
                </li>
              </ul>
            </div>

            <div className="space-y-3">
              <h3 className="font-bold text-slate-900 text-sm">Evaluation Performance (Measured)</h3>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-500 font-sans">Precision:</span>
                  <span className="font-bold text-emerald-700">0.963</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-sans">Recall:</span>
                  <span className="font-bold text-emerald-700">0.970</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-sans">F1 Score:</span>
                  <span className="font-bold text-emerald-700">0.967</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-sans">PR-AUC:</span>
                  <span className="font-bold text-slate-900">0.976</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-sans">Natural Shortage FPR:</span>
                  <span className="font-bold text-emerald-700">0.038 (Low)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Policy Simulation Math */}
      {activeTab === 'policy_math' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">What-If Policy Simulation Formulations</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Empirical microeconomic equations and clearing assumptions implemented in the Policy Lab.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900 text-sm block">1. Targeted Driver Incentive</span>
              <p className="text-slate-600 leading-relaxed">
                Driver supply responds to per-ride incentive bonus alpha (5% to 100%) with empirical supply elasticity E_s = 0.50:
              </p>
              <div className="bg-white p-2.5 rounded border border-slate-200 font-mono text-[11px] text-emerald-800">
                S_t = S_base * (1 + min(0.55, 0.50 * (alpha / 100)))
              </div>
              <p className="text-slate-500 text-[11px]">
                Cost: sum(C_t * $18.50 * (alpha / 100)) where C_t is completed rides.
              </p>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900 text-sm block">2. Rider Fare Discount</span>
              <p className="text-slate-600 leading-relaxed">
                Passenger demand responds to fare discount beta (5% to 50%) with price elasticity E_d = 0.60:
              </p>
              <div className="bg-white p-2.5 rounded border border-slate-200 font-mono text-[11px] text-rose-800">
                D_t = D_base * (1 + min(0.40, 0.60 * (beta / 100)))
              </div>
              <p className="text-rose-600 text-[11px] font-medium">
                Warning: In supply-depressed scenarios, stimulating demand without expanding drivers inflates wait times and unfulfilled requests.
              </p>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900 text-sm block">3. Supply Recovery Support</span>
              <p className="text-slate-600 leading-relaxed">
                Conditionally activates when supply-demand ratio drops below 0.85, providing minimum earnings floor gamma (10% to 60%):
              </p>
              <div className="bg-white p-2.5 rounded border border-slate-200 font-mono text-[11px] text-sky-800">
                S_t = S_base + max(0, (S_norm - S_base) * min(0.55, 0.70 * (gamma / 100)))
              </div>
              <p className="text-slate-500 text-[11px]">
                Targeted cost: only incurred during shortage intervals ($4.50/step per active driver).
              </p>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900 text-sm block">4. Market Clearing Physics</span>
              <p className="text-slate-600 leading-relaxed">
                Dispatch clearing and fare pressure index are calculated identically across all regimes:
              </p>
              <div className="bg-white p-2.5 rounded border border-slate-200 font-mono text-[11px] text-slate-800">
                C_t = min(D_t, S_t * 0.94); U_t = max(0, D_t - C_t)
              </div>
              <p className="text-slate-500 text-[11px]">
                Guarantees deterministic comparability with identical seeds.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Architecture & Persistence */}
      {activeTab === 'architecture' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">System Architecture &amp; Persistence</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Dual-mode storage architecture supporting standalone local execution and production PostgreSQL.
            </p>
          </div>

          <div className="space-y-4 text-xs text-slate-600 leading-relaxed">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900 block text-sm">In-Memory Local Demo Mode (Active)</span>
              <p>
                When <code className="bg-slate-200 px-1 py-0.5 rounded font-mono text-[11px]">DATABASE_URL</code> is omitted, SurgeGuard runs in completely self-contained in-memory demo mode. All simulation runs, time-series steps, policy comparisons, and anomaly assessments persist in memory during the active session.
              </p>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900 block text-sm">PostgreSQL / Supabase Ready</span>
              <p>
                The persistence layer provides seamless plug-and-play transition to PostgreSQL / Supabase when configured via environment variables. Sensitive credentials remain exclusively on the backend server.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataDocsPage;
