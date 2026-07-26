export type ErcotRecord = Record<string, string | number | null>;

export interface PriceResponse {
  hubs: string[];
  records: ErcotRecord[];
}

export interface ErrorSeriesPoint {
  timestamp_utc: string;
  hub_name: string;
  actual: number | null;
  predicted: number | null;
  error: number | null;
  abs_error: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
}

export interface ForecastVsActualResponse {
  hub: string;
  metrics: {
    rmse: number | null;
    mae: number | null;
    max_error: number | null;
  };
  error_series: ErrorSeriesPoint[];
}

export interface ContributingFactor {
  factor: string;
  evidence: string;
  source_url?: string | null;
}

export interface DriverMetric {
  actual_mw?: number | null;
  forecast_mw?: number | null;
  delta_mw?: number | null;
}

export interface DriverSummary {
  wind?: DriverMetric;
  solar?: DriverMetric;
  load?: DriverMetric;
}

export interface RecommendedAction {
  id: string;
  label: string;
  description: string;
}

export interface InvestigateResponse {
  timestamp_utc: string;
  hub_name: string;
  context_features: Record<string, string | number | null>;
  contributing_factors: ContributingFactor[];
  error_mode: string;
  error_mode_label: string;
  narrative: string[];
  recommended_actions: RecommendedAction[];
  driver_summary: DriverSummary;
  action_result?: Record<string, unknown> | null;
}
