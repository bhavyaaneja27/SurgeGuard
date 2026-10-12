import React from 'react';
import {
  LayoutDashboard,
  Cpu,
  MapPin,
  AlertOctagon,
  Scale,
  LineChart,
  Settings,
} from 'lucide-react';
import type { HealthResponse } from '../lib/types';

export type ActiveTab =
  | 'overview'
  | 'digital-twin'
  | 'map'
  | 'alerts'
  | 'policy-lab'
  | 'model-evaluation'
  | 'settings';

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  health: HealthResponse | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange, health }) => {
  const navItems = [
    {
      id: 'overview' as ActiveTab,
      label: 'Overview',
      icon: LayoutDashboard,
    },
    {
      id: 'digital-twin' as ActiveTab,
      label: 'Digital Twin',
      icon: Cpu,
    },
    {
      id: 'map' as ActiveTab,
      label: 'City Map',
      icon: MapPin,
    },
    {
      id: 'alerts' as ActiveTab,
      label: 'Integrity Alerts',
      icon: AlertOctagon,
    },
    {
      id: 'policy-lab' as ActiveTab,
      label: 'What-If Policy Lab',
      icon: Scale,
    },
    {
      id: 'model-evaluation' as ActiveTab,
      label: 'Model Evaluation',
      icon: LineChart,
    },
    {
      id: 'settings' as ActiveTab,
      label: 'Settings / Data Docs',
      icon: Settings,
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between h-[calc(100vh-4rem)] sticky top-16 select-none flex-shrink-0">
      <div className="p-4 space-y-6">
        <div>
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-3 mb-2">
            Operations Workspace
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-brand-900 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-mint-300' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-slate-500 text-[11px]">Mode</span>
          <span className="inline-flex items-center space-x-1 font-semibold text-[10px] px-2 py-0.5 rounded bg-amber-100 text-amber-900 uppercase tracking-wider">
            Synthetic Demo
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500 text-[11px]">API Engine</span>
          <span className="font-mono text-[11px] text-slate-700">
            {health?.status === 'healthy' ? 'FastAPI Online' : 'Offline / Connecting'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500 text-[11px]">Seed Contract</span>
          <span className="font-mono text-[11px] text-slate-700">Deterministic</span>
        </div>
      </div>
    </aside>
  );
};
