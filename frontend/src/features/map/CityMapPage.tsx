import React, { useState, useEffect } from 'react';
import {
  MapPin,
  Activity,
  Compass,
  Filter,
  Scale,
  RefreshCw,
} from 'lucide-react';
import { apiClient } from '../../lib/api-client';
import type {
  ScenarioType,
  ZoneIntelligenceResponse,
  ZoneIntelligenceItem,
} from '../../lib/types';

interface CityMapPageProps {
  onNavigateTab?: (tab: any, params?: any) => void;
}

const SCENARIOS: { id: ScenarioType; name: string }[] = [
  { id: 'unusual_supply_drop', name: 'Unusual Supply Drop (Driver Deficit)' },
  { id: 'natural_shortage', name: 'Natural Shortage (Severe Weather)' },
  { id: 'demand_led_surge', name: 'Demand-Led Surge (Major Event)' },
  { id: 'normal_marketplace', name: 'Normal Marketplace (Equilibrium)' },
];

export const CityMapPage: React.FC<CityMapPageProps> = ({ onNavigateTab }) => {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('unusual_supply_drop');
  const [riskFilter, setRiskFilter] = useState<'all' | 'normal' | 'watch' | 'investigate'>('all');
  const [overlayMetric, setOverlayMetric] = useState<'risk' | 'ratio' | 'wait_time' | 'fare_pressure'>('risk');
  const [selectedZoneId, setSelectedZoneId] = useState<string>('zone_midtown_core');

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [zoneData, setZoneData] = useState<ZoneIntelligenceResponse | null>(null);

  const fetchZoneIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await apiClient.getZoneIntelligence(selectedScenario);
      setZoneData(resp);
    } catch (err) {
      console.error('Failed to load zone intelligence:', err);
      setError(err instanceof Error ? err.message : 'Could not retrieve spatial zone intelligence.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchZoneIntelligence();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedScenario]);

  const selectedZone = zoneData?.zones.find((z) => z.zone_id === selectedZoneId) || zoneData?.zones[0];

  // Helper to color zone polygons based on active overlay
  const getZoneFillColor = (zone: ZoneIntelligenceItem): string => {
    if (overlayMetric === 'risk') {
      if (zone.risk_category === 'investigate') return '#f43f5e'; // Rose
      if (zone.risk_category === 'watch') return '#f59e0b'; // Amber
      return '#10b981'; // Emerald
    }
    if (overlayMetric === 'ratio') {
      if (zone.supply_demand_ratio < 0.6) return '#ef4444';
      if (zone.supply_demand_ratio < 0.85) return '#f59e0b';
      if (zone.supply_demand_ratio < 1.0) return '#38bdf8';
      return '#10b981';
    }
    if (overlayMetric === 'wait_time') {
      if (zone.estimated_wait_time_minutes > 7.0) return '#e11d48';
      if (zone.estimated_wait_time_minutes > 4.5) return '#f59e0b';
      return '#10b981';
    }
    // fare_pressure
    if (zone.fare_pressure_index > 140) return '#be123c';
    if (zone.fare_pressure_index > 115) return '#ea580c';
    return '#059669';
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-200">
              <Compass className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">City Map &amp; Spatial Intelligence</h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-100/70 text-emerald-800 border border-emerald-200">
              NYC TLC Synthetic Centroids
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Spatial monitoring of supply-demand equilibrium, passenger waiting queues, and contextual risk anomalies across TLC test zones.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchZoneIntelligence}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-emerald-600 ${loading ? 'animate-spin' : ''}`} />
            Refresh Signals
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs">
          {error}
        </div>
      )}

      {/* System Health Summary Bar */}
      {zoneData && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Monitored Zones</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">{zoneData.summary.total_zones} Zones</div>
            <span className="text-[11px] text-slate-400">NYC TLC Demo Corridors</span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Investigate Triggered</span>
            <div className="text-lg font-bold text-rose-600 mt-0.5">{zoneData.summary.investigate_zones} Zones</div>
            <span className="text-[11px] text-rose-500 font-medium">Priority Anomaly Leads</span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Under Watch</span>
            <div className="text-lg font-bold text-amber-600 mt-0.5">{zoneData.summary.watch_zones} Zones</div>
            <span className="text-[11px] text-amber-500 font-medium">Elevated Shortage</span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">System Avg Wait</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">{zoneData.summary.system_avg_wait_time.toFixed(1)}m</div>
            <span className="text-[11px] text-slate-400">Estimated Passenger Queue</span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">System Avg Surge</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">{zoneData.summary.system_avg_fare_pressure.toFixed(1)}</div>
            <span className="text-[11px] text-slate-400">Baseline 100.0</span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[11px] text-slate-500 font-medium">Overall Fulfillment</span>
            <div className="text-lg font-bold text-emerald-600 mt-0.5">{zoneData.summary.overall_fulfillment_rate.toFixed(1)}%</div>
            <span className="text-[11px] text-emerald-600 font-medium">Dispatch Clearing Rate</span>
          </div>
        </div>
      )}

      {/* Map Control Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Scenario Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">Scenario:</span>
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value as ScenarioType)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
          >
            {SCENARIOS.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.name}
              </option>
            ))}
          </select>
        </div>

        {/* Overlay Metric Toggles */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
          <span className="text-[11px] text-slate-500 px-2 font-medium">Layer:</span>
          <button
            onClick={() => setOverlayMetric('risk')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all ${
              overlayMetric === 'risk'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Anomaly Risk
          </button>
          <button
            onClick={() => setOverlayMetric('ratio')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all ${
              overlayMetric === 'ratio'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Supply/Demand Ratio
          </button>
          <button
            onClick={() => setOverlayMetric('wait_time')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all ${
              overlayMetric === 'wait_time'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Wait Times
          </button>
          <button
            onClick={() => setOverlayMetric('fare_pressure')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all ${
              overlayMetric === 'fare_pressure'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Fare Pressure
          </button>
        </div>

        {/* Risk Filter */}
        <div className="flex items-center gap-1 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-500 text-[11px] font-medium mr-1">Filter:</span>
          {(['all', 'normal', 'watch', 'investigate'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setRiskFilter(r)}
              className={`px-2 py-0.5 rounded text-[11px] font-medium capitalize transition-colors ${
                riskFilter === r
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Main Interactive Map & Zone Telemetry Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Interactive Schematic City Map Canvas */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                New York City TLC Schematic Corridors
              </span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              Click any zone to inspect telemetry
            </span>
          </div>

          {/* SVG Map Container */}
          <div className="relative w-full h-[450px] bg-slate-900 rounded-lg overflow-hidden border border-slate-800 p-4">
            {/* Background Grid & Waterways */}
            <svg
              className="w-full h-full"
              viewBox="0 0 600 500"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Grid lines */}
              <defs>
                <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                  <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1e293b" strokeWidth="0.75" />
                </pattern>
                {/* Glow Filter */}
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              <rect width="600" height="500" fill="#0f172a" />
              <rect width="600" height="500" fill="url(#grid)" opacity="0.6" />

              {/* Schematic River Outlines (Hudson & East River) */}
              <path
                d="M 120 0 C 140 150, 160 300, 150 500"
                fill="none"
                stroke="#1e3a5f"
                strokeWidth="18"
                opacity="0.7"
              />
              <path
                d="M 270 0 C 260 120, 240 240, 290 380 C 320 440, 360 500, 380 500"
                fill="none"
                stroke="#1e3a5f"
                strokeWidth="14"
                opacity="0.7"
              />

              {/* Waterway Labels */}
              <text x="70" y="240" fill="#334155" fontSize="10" fontFamily="sans-serif" transform="rotate(-75 70 240)">
                HUDSON RIVER
              </text>
              <text x="240" y="210" fill="#334155" fontSize="10" fontFamily="sans-serif" transform="rotate(-65 240 210)">
                EAST RIVER
              </text>
              <text x="440" y="470" fill="#334155" fontSize="10" fontFamily="sans-serif">
                JFK APPROACH CORRIDOR
              </text>

              {/* 4 TLC Demo Zones Coordinates in SVG Canvas */}
              {/* Zone 1: Midtown Core (x: 200, y: 200) */}
              <g
                onClick={() => setSelectedZoneId('zone_midtown_core')}
                className="cursor-pointer transition-all duration-200"
                opacity={riskFilter === 'all' || zoneData?.zones.find(z => z.zone_id === 'zone_midtown_core')?.risk_category === riskFilter ? 1 : 0.25}
              >
                <polygon
                  points="175,170 235,185 220,245 160,230"
                  fill={zoneData?.zones[0] ? getZoneFillColor(zoneData.zones[0]) : '#059669'}
                  fillOpacity={selectedZoneId === 'zone_midtown_core' ? 0.85 : 0.65}
                  stroke={selectedZoneId === 'zone_midtown_core' ? '#ffffff' : '#e2e8f0'}
                  strokeWidth={selectedZoneId === 'zone_midtown_core' ? 3 : 1.5}
                  filter={selectedZoneId === 'zone_midtown_core' ? 'url(#glow)' : undefined}
                />
                <circle cx="198" cy="208" r="4" fill="#ffffff" />
                <text x="198" y="160" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">
                  Midtown Core
                </text>
                <text x="198" y="222" fill="#e2e8f0" fontSize="9" fontFamily="monospace" textAnchor="middle">
                  {zoneData?.zones[0]?.current_demand} req / {zoneData?.zones[0]?.current_supply} drv
                </text>
              </g>

              {/* Zone 2: Downtown Financial (x: 185, y: 340) */}
              <g
                onClick={() => setSelectedZoneId('zone_downtown_financial')}
                className="cursor-pointer transition-all duration-200"
                opacity={riskFilter === 'all' || zoneData?.zones.find(z => z.zone_id === 'zone_downtown_financial')?.risk_category === riskFilter ? 1 : 0.25}
              >
                <polygon
                  points="165,310 220,320 205,385 150,370"
                  fill={zoneData?.zones[1] ? getZoneFillColor(zoneData.zones[1]) : '#059669'}
                  fillOpacity={selectedZoneId === 'zone_downtown_financial' ? 0.85 : 0.65}
                  stroke={selectedZoneId === 'zone_downtown_financial' ? '#ffffff' : '#e2e8f0'}
                  strokeWidth={selectedZoneId === 'zone_downtown_financial' ? 3 : 1.5}
                  filter={selectedZoneId === 'zone_downtown_financial' ? 'url(#glow)' : undefined}
                />
                <circle cx="185" cy="347" r="4" fill="#ffffff" />
                <text x="185" y="302" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">
                  Downtown Financial
                </text>
                <text x="185" y="360" fill="#e2e8f0" fontSize="9" fontFamily="monospace" textAnchor="middle">
                  {zoneData?.zones[1]?.current_demand} req / {zoneData?.zones[1]?.current_supply} drv
                </text>
              </g>

              {/* Zone 3: Uptown Residential (x: 215, y: 80) */}
              <g
                onClick={() => setSelectedZoneId('zone_uptown_residential')}
                className="cursor-pointer transition-all duration-200"
                opacity={riskFilter === 'all' || zoneData?.zones.find(z => z.zone_id === 'zone_uptown_residential')?.risk_category === riskFilter ? 1 : 0.25}
              >
                <polygon
                  points="190,55 250,70 235,130 175,115"
                  fill={zoneData?.zones[3] ? getZoneFillColor(zoneData.zones[3]) : '#059669'}
                  fillOpacity={selectedZoneId === 'zone_uptown_residential' ? 0.85 : 0.65}
                  stroke={selectedZoneId === 'zone_uptown_residential' ? '#ffffff' : '#e2e8f0'}
                  strokeWidth={selectedZoneId === 'zone_uptown_residential' ? 3 : 1.5}
                  filter={selectedZoneId === 'zone_uptown_residential' ? 'url(#glow)' : undefined}
                />
                <circle cx="212" cy="92" r="4" fill="#ffffff" />
                <text x="212" y="47" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">
                  Uptown Residential
                </text>
                <text x="212" y="106" fill="#e2e8f0" fontSize="9" fontFamily="monospace" textAnchor="middle">
                  {zoneData?.zones[3]?.current_demand} req / {zoneData?.zones[3]?.current_supply} drv
                </text>
              </g>

              {/* Zone 4: Airport Terminal (JFK Corridor) (x: 460, y: 350) */}
              <g
                onClick={() => setSelectedZoneId('zone_airport_terminal')}
                className="cursor-pointer transition-all duration-200"
                opacity={riskFilter === 'all' || zoneData?.zones.find(z => z.zone_id === 'zone_airport_terminal')?.risk_category === riskFilter ? 1 : 0.25}
              >
                <polygon
                  points="410,310 510,320 490,410 390,400"
                  fill={zoneData?.zones[2] ? getZoneFillColor(zoneData.zones[2]) : '#059669'}
                  fillOpacity={selectedZoneId === 'zone_airport_terminal' ? 0.85 : 0.65}
                  stroke={selectedZoneId === 'zone_airport_terminal' ? '#ffffff' : '#e2e8f0'}
                  strokeWidth={selectedZoneId === 'zone_airport_terminal' ? 3 : 1.5}
                  filter={selectedZoneId === 'zone_airport_terminal' ? 'url(#glow)' : undefined}
                />
                <circle cx="450" cy="360" r="4" fill="#ffffff" />
                <text x="450" y="300" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">
                  Airport Terminal
                </text>
                <text x="450" y="375" fill="#e2e8f0" fontSize="9" fontFamily="monospace" textAnchor="middle">
                  {zoneData?.zones[2]?.current_demand} req / {zoneData?.zones[2]?.current_supply} drv
                </text>
              </g>
            </svg>

            {/* Map Legend Overlay in bottom-left */}
            <div className="absolute bottom-3 left-3 bg-slate-900/90 border border-slate-700/80 rounded-lg p-2.5 text-[11px] text-slate-300 backdrop-blur-sm space-y-1">
              <span className="font-semibold text-white block">Active Layer: {overlayMetric.replace('_', ' ').toUpperCase()}</span>
              {overlayMetric === 'risk' && (
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Normal</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Watch</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Investigate</span>
                </div>
              )}
              {overlayMetric === 'ratio' && (
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-emerald-500" /> &gt;1.0 Surplus</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-amber-500" /> 0.7-0.9</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-rose-500" /> &lt;0.6 Deficit</span>
                </div>
              )}
              {overlayMetric === 'wait_time' && (
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-emerald-500" /> &lt;4m</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-amber-500" /> 4-7m</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-rose-500" /> &gt;7m</span>
                </div>
              )}
            </div>
          </div>

          <p className="text-[11px] text-slate-400 italic">
            Notice: TLC centroids and bounding coordinates represent synthetic demo boundaries mapped for market visualization.
          </p>
        </div>

        {/* Selected Zone Intelligence Detail Panel */}
        <div className="lg:col-span-5 space-y-4">
          {selectedZone ? (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900">{selectedZone.zone_name}</h3>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        selectedZone.risk_category === 'investigate'
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : selectedZone.risk_category === 'watch'
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      }`}
                    >
                      {selectedZone.risk_category}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 font-medium">{selectedZone.zone_type}</span>
                </div>

                <div className="text-right">
                  <span className="text-[11px] text-slate-400 block font-mono">Risk Score</span>
                  <span className="text-lg font-bold font-mono text-slate-900">{selectedZone.anomaly_score.toFixed(1)}/100</span>
                </div>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                {selectedZone.description}
              </p>

              {/* Core Telemetry Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[11px]">Demand vs Supply</span>
                  <span className="font-bold text-slate-900 font-mono text-sm">
                    {selectedZone.current_demand} / {selectedZone.current_supply}
                  </span>
                  <span className="text-[11px] text-slate-500 block mt-0.5">
                    Ratio: <span className="font-mono font-semibold">{selectedZone.supply_demand_ratio.toFixed(2)}</span>
                  </span>
                </div>

                <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[11px]">Passenger Wait Time</span>
                  <span className="font-bold text-slate-900 font-mono text-sm">
                    {selectedZone.estimated_wait_time_minutes.toFixed(1)} mins
                  </span>
                  <span className="text-[11px] text-slate-500 block mt-0.5">
                    Surge Index: <span className="font-mono font-semibold">{selectedZone.fare_pressure_index.toFixed(1)}</span>
                  </span>
                </div>

                <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[11px]">Baseline Benchmark</span>
                  <span className="font-bold text-slate-900 font-mono text-sm">
                    {selectedZone.baseline_demand} / {selectedZone.baseline_supply}
                  </span>
                  <span className="text-[11px] text-slate-500 block mt-0.5">
                    Equilibrium expectation
                  </span>
                </div>

                <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[11px]">Fulfillment Rate</span>
                  <span className="font-bold text-emerald-700 font-mono text-sm">
                    {selectedZone.fulfillment_rate_pct.toFixed(1)}%
                  </span>
                  <span className="text-[11px] text-slate-500 block mt-0.5">
                    Trip clearing efficacy
                  </span>
                </div>
              </div>

              {/* Dominant Signal & Anomaly Interpretation */}
              <div className="space-y-1.5 pt-2 border-t border-slate-100">
                <span className="text-xs font-semibold text-slate-800">Dominant Interpretation Signal</span>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 font-medium">
                  {selectedZone.dominant_signal}
                </div>
              </div>

              {/* Active Contextual Alerts */}
              <div className="space-y-1.5 pt-2 border-t border-slate-100">
                <span className="text-xs font-semibold text-slate-800">
                  Recent Anomaly Leads ({selectedZone.recent_alert_summaries.length})
                </span>
                {selectedZone.recent_alert_summaries.length > 0 ? (
                  <ul className="space-y-1 text-[11px] text-slate-600">
                    {selectedZone.recent_alert_summaries.map((alert, idx) => (
                      <li key={idx} className="p-1.5 bg-rose-50/60 border border-rose-200 rounded text-rose-900 font-mono">
                        {alert}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-400 italic">No elevated anomaly signals triggered for this zone.</p>
                )}
              </div>

              {/* Workflow Navigation Quick Actions */}
              <div className="pt-3 border-t border-slate-100 flex flex-col gap-2">
                <button
                  onClick={() => onNavigateTab && onNavigateTab('policy-lab')}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm"
                >
                  <Scale className="w-3.5 h-3.5" />
                  Test Interventions in Policy Lab
                </button>
                <button
                  onClick={() => onNavigateTab && onNavigateTab('digital-twin')}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-medium transition-colors"
                >
                  <Activity className="w-3.5 h-3.5 text-slate-600" />
                  Replay Time Series in Digital Twin
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 bg-white rounded-xl border border-slate-200 text-center text-xs text-slate-400">
              Select a zone from the map to inspect operational signals.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CityMapPage;
