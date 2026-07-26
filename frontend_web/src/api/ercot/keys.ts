const all = ['ercot'] as const;

export const ercotKeys = {
  all,
  hubs: [...all, 'hubs'] as const,
  prices: (hubs: string[], start?: string, end?: string) =>
    [...all, 'prices', hubs.join(','), start ?? '', end ?? ''] as const,
  forecastVsActual: (hub: string, start?: string, end?: string) =>
    [...all, 'forecast-vs-actual', hub, start ?? '', end ?? ''] as const,
};
