import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient, SurgeGuardApiError } from '../lib/api-client';

describe('apiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('should return default or configured base URL', () => {
    const url = apiClient.getBaseUrl();
    expect(url).toBeDefined();
    expect(typeof url).toBe('string');
  });

  it('should fetch health status successfully', async () => {
    const mockHealthResponse = {
      status: 'healthy',
      version: '0.1.0',
      model_status: 'not_loaded',
      database_status: 'disconnected',
      timestamp: '2026-10-12T21:40:00Z',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealthResponse,
    });

    const response = await apiClient.getHealth();
    expect(response).toEqual(mockHealthResponse);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    );
  });

  it('should list available scenarios', async () => {
    const mockScenarios = [
      {
        id: 'scenario_normal_marketplace',
        name: 'Normal Marketplace',
        description: 'Normal equilibrium',
        scenario_type: 'normal_marketplace',
        default_seed: 42,
        default_duration_minutes: 120,
        default_intensity: 0.7,
        supported_zones: ['zone_midtown_core'],
        ground_truth_label: 'normal',
      },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockScenarios,
    });

    const result = await apiClient.getScenarios();
    expect(result).toHaveLength(1);
    expect(result[0].scenario_type).toBe('normal_marketplace');
  });

  it('should execute simulation and return run summary', async () => {
    const mockRunResponse = {
      run_id: 'test-run-123',
      scenario_id: 'scenario_unusual_supply_drop',
      scenario_name: 'Unusual Supply Drop',
      scenario_type: 'unusual_supply_drop',
      zone_id: 'zone_midtown_core',
      duration_minutes: 60,
      event_intensity: 0.8,
      seed: 42,
      status: 'completed',
      started_at: '2026-10-12T18:00:00Z',
      completed_at: '2026-10-12T18:00:02Z',
      model_version: 'v0.1-synthetic',
      data_mode: 'SYNTHETIC_SIMULATION',
      storage_type: 'in_memory_demo',
      total_steps: 60,
      summary_metrics: {
        average_demand: 120.0,
        average_supply: 80.0,
        peak_demand: 130.0,
        min_supply: 45.0,
        total_requests: 7200,
        total_completed_rides: 4800,
        fulfillment_rate_pct: 66.7,
        average_wait_time_minutes: 5.5,
        max_wait_time_minutes: 12.0,
        peak_fare_pressure: 195.0,
        average_fare_pressure: 135.0,
        average_supply_demand_ratio: 0.67,
        critical_steps_count: 24,
      },
      disclaimer: 'SYNTHETIC SIMULATION',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockRunResponse,
    });

    const res = await apiClient.createSimulation({
      scenario_type: 'unusual_supply_drop',
      zone_id: 'zone_midtown_core',
      duration_minutes: 60,
      event_intensity: 0.8,
      seed: 42,
    });

    expect(res.run_id).toBe('test-run-123');
    expect(res.total_steps).toBe(60);
    expect(res.summary_metrics.peak_fare_pressure).toBe(195.0);
  });

  it('should construct correct export URLs', () => {
    const csvUrl = apiClient.getExportUrl('test-uuid-456', 'csv');
    expect(csvUrl).toContain('/api/v1/export/test-uuid-456?format=csv');

    const jsonUrl = apiClient.getExportUrl('test-uuid-456', 'json');
    expect(jsonUrl).toContain('/api/v1/export/test-uuid-456?format=json');
  });

  it('should handle API errors and throw SurgeGuardApiError with structured data', async () => {
    const mockErrorResponse = {
      error_code: 'SERVICE_UNAVAILABLE',
      message: 'Database connection failed',
      details: { retry_after: 30 },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => mockErrorResponse,
    });

    try {
      await apiClient.getHealth();
      expect.unreachable('Should have thrown an error');
    } catch (err) {
      expect(err).toBeInstanceOf(SurgeGuardApiError);
      if (err instanceof SurgeGuardApiError) {
        expect(err.error_code).toBe('SERVICE_UNAVAILABLE');
        expect(err.status).toBe(503);
        expect(err.message).toBe('Database connection failed');
      }
    }
  });

  it('should call comparePolicies and return policy comparisons', async () => {
    const mockPolicyResponse = {
      run_id: 'test-run-policy-1',
      scenario_type: 'unusual_supply_drop',
      zone_id: 'zone_midtown_core',
      seed: 42,
      baseline_policy: 'no_intervention',
      comparisons: [
        {
          policy_type: 'no_intervention',
          policy_name: 'No Intervention',
          description: 'Baseline',
          parameters_json: {},
          metrics: {
            ride_requests: 7200,
            available_drivers: 80.0,
            completed_rides: 4800,
            unfulfilled_requests: 2400,
            fulfillment_rate_pct: 66.7,
            average_wait_time_minutes: 5.5,
            max_wait_time_minutes: 12.0,
            fare_pressure_index: 135.0,
            peak_fare_pressure: 195.0,
            driver_earnings_index: 110.0,
            simulated_driver_incentive_cost: 0,
            simulated_rider_discount_cost: 0,
            estimated_intervention_cost: 0,
          },
          deltas_versus_baseline: {
            ride_requests_delta: 0,
            available_drivers_delta: 0,
            rides_delta: 0,
            unfulfilled_delta: 0,
            fulfillment_rate_delta: 0,
            wait_time_delta: 0,
            fare_pressure_delta: 0,
            earnings_delta: 0,
            cost_delta: 0,
          },
          timeline: [],
          assumptions: [],
          trade_offs_and_limitations: [],
        },
      ],
      disclaimer: 'Simulated counterfactual estimates',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockPolicyResponse,
    });

    const res = await apiClient.comparePolicies({
      scenario_type: 'unusual_supply_drop',
      zone_id: 'zone_midtown_core',
    });

    expect(res.comparisons).toHaveLength(1);
    expect(res.baseline_policy).toBe('no_intervention');
  });

  it('should fetch zone intelligence across demo zones', async () => {
    const mockZoneResp = {
      scenario_type: 'unusual_supply_drop',
      timestamp: '2026-10-12T19:00:00Z',
      zones: [
        {
          zone_id: 'zone_midtown_core',
          zone_name: 'Midtown Core',
          zone_type: 'Commercial',
          description: 'High volume',
          centroid: { lat: 40.7549, lng: -73.9840 },
          boundary: [],
          baseline_demand: 120,
          baseline_supply: 135,
          current_demand: 120,
          current_supply: 80,
          supply_demand_ratio: 0.67,
          estimated_wait_time_minutes: 5.5,
          fare_pressure_index: 135.0,
          fulfillment_rate_pct: 66.7,
          risk_category: 'investigate',
          anomaly_score: 84.5,
          active_alerts_count: 3,
          dominant_signal: 'Unusual shortage',
          recent_alert_summaries: [],
        },
      ],
      summary: {
        total_zones: 1,
        investigate_zones: 1,
        watch_zones: 0,
        normal_zones: 0,
        system_avg_wait_time: 5.5,
        system_avg_fare_pressure: 135.0,
        overall_fulfillment_rate: 66.7,
      },
      disclaimer: 'Synthetic Demo Zones',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockZoneResp,
    });

    const res = await apiClient.getZoneIntelligence('unusual_supply_drop');
    expect(res.zones).toHaveLength(1);
    expect(res.zones[0].risk_category).toBe('investigate');
  });
});
