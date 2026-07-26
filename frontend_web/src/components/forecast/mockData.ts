import type { PriceSeriesRow } from './ChartPanel';
import type { TableRow } from './TablePanel';
import { HUBS } from './tokens';

/**
 * Realistic mock data for the Forecast Assistant demo. Hourly ERCOT DAM prices
 * over ~30 days, per hub, with strong daily cycles and occasional spikes.
 */
function seeded(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

const HUB_BASE: Record<string, number> = {
  HB_HOUSTON: 32,
  HB_NORTH: 28,
  HB_SOUTH: 30,
  HB_WEST: 26,
  HB_BUSAVG: 29,
};

export function buildHubPriceSeries(days = 30): {
  series: PriceSeriesRow[];
  hubs: string[];
} {
  const hubs = ['HB_HOUSTON', 'HB_NORTH', 'HB_SOUTH', 'HB_WEST'];
  const rand = seeded(42);
  const hours = days * 24;
  const start = new Date('2025-09-28T00:00:00Z').getTime();
  const series: PriceSeriesRow[] = [];

  for (let h = 0; h < hours; h += 1) {
    const t = new Date(start + h * 3600_000);
    const hourOfDay = t.getUTCHours();
    // Daily cycle: morning + evening peaks.
    const cycle =
      1 +
      0.5 * Math.sin(((hourOfDay - 7) / 24) * 2 * Math.PI) +
      0.35 * Math.sin(((hourOfDay - 18) / 12) * 2 * Math.PI);
    const row: PriceSeriesRow = { timestamp_utc: t.toISOString() };
    for (const hub of hubs) {
      const spike = rand() > 0.985 ? 40 + rand() * 80 : 0;
      const noise = (rand() - 0.5) * 8;
      row[hub] = Math.max(5, +(HUB_BASE[hub] * cycle + noise + spike).toFixed(2));
    }
    series.push(row);
  }
  return { series, hubs };
}

export function buildPriceTable(days = 30): TableRow[] {
  const { series } = buildHubPriceSeries(days);
  const rows: TableRow[] = [];
  for (const row of series) {
    for (const hub of HUBS.slice(0, 4)) {
      const val = row[hub];
      if (val != null) {
        rows.push({
          timestamp_utc: row.timestamp_utc.replace('Z', '').slice(0, 19),
          hub_name: hub,
          dam_price: Number(val),
        });
      }
    }
  }
  return rows;
}
