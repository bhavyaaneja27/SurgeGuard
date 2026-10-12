import { ShieldCheck } from 'lucide-react';
import { HealthStatusBadge } from './HealthStatusBadge';
import type { HealthResponse } from '../lib/types';

interface HeaderProps {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
}

export const Header: React.FC<HeaderProps> = ({ health, loading, error }) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-brand-900 flex items-center justify-center text-mint-100 shadow-sm">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-tight text-slate-900">
                SurgeGuard
              </h1>
            </div>
            <p className="text-xs text-slate-500">
              Marketplace Integrity Intelligence • Digital Twin &amp; Explainable Anomaly Detection
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <HealthStatusBadge health={health} loading={loading} error={error} />
        </div>
      </div>
    </header>
  );
};
