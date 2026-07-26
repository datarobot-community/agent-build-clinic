import { useMutation, useQuery } from '@tanstack/react-query';
import { getForecastVsActual, getHubs, getPrices, investigate } from './api-requests';
import { ercotKeys } from './keys';

export function useHubs() {
  return useQuery({
    queryKey: ercotKeys.hubs,
    queryFn: ({ signal }) => getHubs({ signal }).then(r => r.data),
    staleTime: 5 * 60_000,
  });
}

export function usePrices(hubs: string[], startDate?: string, endDate?: string, enabled = true) {
  return useQuery({
    queryKey: ercotKeys.prices(hubs, startDate, endDate),
    queryFn: ({ signal }) => getPrices({ signal, hubs, startDate, endDate }).then(r => r.data),
    enabled,
    staleTime: 60_000,
  });
}

export function useForecastVsActual(
  hub: string,
  startDate?: string,
  endDate?: string,
  enabled = true
) {
  return useQuery({
    queryKey: ercotKeys.forecastVsActual(hub, startDate, endDate),
    queryFn: ({ signal }) =>
      getForecastVsActual({ signal, hub, startDate, endDate }).then(r => r.data),
    enabled: enabled && Boolean(hub),
    staleTime: 60_000,
    retry: false,
    refetchOnWindowFocus: false,
    gcTime: 5 * 60_000,
  });
}

export function useInvestigate() {
  return useMutation({
    mutationFn: (vars: {
      timestampUtc: string;
      hubName: string;
      tavilyApiKey?: string;
      actual?: number | null;
      predicted?: number | null;
      action?: string;
    }) => investigate(vars).then(r => r.data),
  });
}
