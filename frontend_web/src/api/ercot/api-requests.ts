import apiClient from '@/api/apiClient';
import type { ForecastVsActualResponse, InvestigateResponse, PriceResponse } from './types';

export async function getHubs({ signal }: { signal?: AbortSignal }) {
  return apiClient.get<string[]>('/v1/ercot/hubs', { signal });
}

export async function getPrices({
  signal,
  hubs,
  startDate,
  endDate,
}: {
  signal?: AbortSignal;
  hubs?: string[];
  startDate?: string;
  endDate?: string;
}) {
  return apiClient.get<PriceResponse>('/v1/ercot/prices', {
    signal,
    params: { hubs, start_date: startDate, end_date: endDate },
  });
}

export async function getForecastVsActual({
  signal,
  hub,
  startDate,
  endDate,
}: {
  signal?: AbortSignal;
  hub: string;
  startDate?: string;
  endDate?: string;
}) {
  return apiClient.get<ForecastVsActualResponse>('/v1/ercot/forecast-vs-actual', {
    signal,
    timeout: 300_000,
    params: { hub, start_date: startDate, end_date: endDate },
  });
}

export async function investigate({
  timestampUtc,
  hubName,
  tavilyApiKey,
  actual,
  predicted,
  action,
}: {
  timestampUtc: string;
  hubName: string;
  tavilyApiKey?: string;
  actual?: number | null;
  predicted?: number | null;
  action?: string;
}) {
  return apiClient.post<InvestigateResponse>('/v1/ercot/investigate', {
    timestamp_utc: timestampUtc,
    hub_name: hubName,
    tavily_api_key: tavilyApiKey || null,
    actual: actual ?? null,
    predicted: predicted ?? null,
    action: action ?? null,
  });
}
