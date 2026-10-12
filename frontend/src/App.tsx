import { useState } from 'react';
import { DisclaimerBanner } from './components/DisclaimerBanner';
import { Header } from './components/Header';
import { Sidebar, type ActiveTab } from './components/Sidebar';
import { OverviewPage } from './pages/Overview';
import { DigitalTwinPage } from './features/digital-twin/DigitalTwinPage';
import { AlertsPage } from './features/alerts';
import { CityMapPage } from './features/map';
import { PolicyLabPage } from './features/policy-lab';
import { ModelEvaluationPage } from './features/model-evaluation/ModelEvaluationPage';
import { DataDocsPage } from './features/settings/DataDocsPage';
import type { HealthResponse } from './lib/types';

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const handleHealthLoaded = (data: HealthResponse | null, err: string | null) => {
    setHealth(data);
    setError(err);
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900 font-sans">
      {/* Mandatory PRD Disclaimer Banner */}
      <DisclaimerBanner />

      {/* Operations Header */}
      <Header health={health} loading={loading} error={error} />

      {/* Main Workspace Layout with Sidebar */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} health={health} />

        <main className="flex-1 p-6 overflow-y-auto">
          {activeTab === 'overview' && (
            <OverviewPage onHealthLoaded={handleHealthLoaded} onNavigate={setActiveTab} />
          )}

          {activeTab === 'digital-twin' && (
            <DigitalTwinPage />
          )}

          {activeTab === 'map' && (
            <CityMapPage onNavigateTab={setActiveTab} />
          )}

          {activeTab === 'alerts' && (
            <AlertsPage />
          )}

          {activeTab === 'policy-lab' && (
            <PolicyLabPage />
          )}

          {activeTab === 'model-evaluation' && (
            <ModelEvaluationPage />
          )}

          {activeTab === 'settings' && (
            <DataDocsPage />
          )}
        </main>
      </div>

      {/* Operations Footer */}
      <footer className="bg-white border-t border-slate-200 py-3 px-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>SurgeGuard Platform • Marketplace Integrity Intelligence</span>
          <span>Operational Analytics • Digital Twin &amp; Explainable Anomaly Detection</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
