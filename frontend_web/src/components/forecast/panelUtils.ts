import type { PriceSeriesRow } from './ChartPanel';
import type { TableRow } from './TablePanel';
import type { Panel } from '@/api/ercot/types';
import { v4 as uuid } from 'uuid';

export interface DamPriceRecord {
  timestamp_utc: string;
  hub_name: string;
  dam_price_usd_mwh?: number | string | null;
  predicted_dam_price_usd_mwh?: number | string | null;
}

export interface PredictionToolResult {
  hub_name?: string;
  predictions?: DamPriceRecord[];
}

export interface ForecastPanel {
  id: string;
  title: string;
  chartTitle: string;
  series: PriceSeriesRow[];
  hubs: string[];
  tableRows: TableRow[];
  toolName?: string;
}

function parseDamRecords(raw: unknown): DamPriceRecord[] {
  if (Array.isArray(raw)) {
    return raw as DamPriceRecord[];
  }
  if (raw && typeof raw === 'object') {
    const obj = raw as Record<string, unknown>;
    if (Array.isArray(obj.records)) {
      return obj.records as DamPriceRecord[];
    }
  }
  return [];
}

/** Build chart + table panel payloads from a `get_dam_prices` tool result. */
export function panelFromDamPricesResult(raw: unknown, panelId: string): ForecastPanel | null {
  const records = parseDamRecords(raw);
  if (records.length === 0) return null;

  const hubs = [...new Set(records.map(r => r.hub_name).filter(Boolean))].sort();
  const byTs = new Map<string, PriceSeriesRow>();
  const tableRows: TableRow[] = [];

  for (const rec of records) {
    const ts = rec.timestamp_utc;
    const hub = rec.hub_name;
    const price = rec.dam_price_usd_mwh;
    if (!ts || !hub || price == null || price === '') continue;
    const numeric = Number(price);
    if (Number.isNaN(numeric)) continue;

    if (!byTs.has(ts)) {
      byTs.set(ts, { timestamp_utc: ts });
    }
    byTs.get(ts)![hub] = numeric;
    tableRows.push({
      timestamp_utc: ts.replace('Z', '').slice(0, 19),
      hub_name: hub,
      dam_price: numeric,
    });
  }

  if (tableRows.length === 0) return null;

  const series = [...byTs.values()].sort(
    (a, b) => new Date(a.timestamp_utc).getTime() - new Date(b.timestamp_utc).getTime()
  );

  const hubLabel = hubs.length === 1 ? hubs[0] : 'all hubs';
  return {
    id: panelId,
    title: `ERCOT DAM prices – ${hubLabel}`,
    chartTitle: `ERCOT Day-Ahead Hub Prices – ${hubLabel}`,
    series,
    hubs,
    tableRows,
  };
}

/** Build chart + table panel payloads from a `predict_dam_prices` tool result. */
export function panelFromPredictionsResult(raw: unknown, panelId: string): ForecastPanel | null {
  if (!raw || typeof raw !== 'object') return null;
  const payload = raw as PredictionToolResult;
  const records = payload.predictions ?? [];
  if (records.length === 0) return null;

  const hub = payload.hub_name ?? records[0]?.hub_name ?? 'hub';
  const byTs = new Map<string, PriceSeriesRow>();
  const tableRows: TableRow[] = [];

  for (const rec of records) {
    const ts = rec.timestamp_utc;
    const price = rec.predicted_dam_price_usd_mwh;
    if (!ts || price == null || price === '') continue;
    const numeric = Number(price);
    if (Number.isNaN(numeric)) continue;

    if (!byTs.has(ts)) {
      byTs.set(ts, { timestamp_utc: ts });
    }
    byTs.get(ts)![hub] = numeric;
    tableRows.push({
      timestamp_utc: ts.replace('Z', '').slice(0, 19),
      hub_name: hub,
      dam_price: numeric,
    });
  }

  if (tableRows.length === 0) return null;

  const series = [...byTs.values()].sort(
    (a, b) => new Date(a.timestamp_utc).getTime() - new Date(b.timestamp_utc).getTime()
  );

  return {
    id: panelId,
    title: `ERCOT DAM forecast – ${hub}`,
    chartTitle: `24h DAM Price Forecast – ${hub}`,
    series,
    hubs: [hub],
    tableRows,
  };
}

export function parseToolResultContent(content: string): unknown {
  try {
    return JSON.parse(content) as unknown;
  } catch {
    return content;
  }
}

/** Convert an in-session forecast panel into a persisted workspace panel payload. */
export function forecastPanelToStoredPanel(
  panel: ForecastPanel,
  opts: { sourceDatasetId: string; toolName: string; parents?: string[] }
): Panel {
  return {
    id: uuid(),
    title: panel.title,
    panel_type: 'bundle',
    payload: {
      chartTitle: panel.chartTitle,
      series: panel.series,
      hubs: panel.hubs,
      tableRows: panel.tableRows,
    },
    parents: opts.parents ?? [],
    source_dataset_id: opts.sourceDatasetId,
    tool_name: opts.toolName,
  };
}

/** Rehydrate a stored workspace bundle panel for chart/table components. */
export function storedPanelToForecastPanel(panel: Panel): ForecastPanel | null {
  if (panel.panel_type !== 'bundle') return null;
  const payload = panel.payload;
  const series = payload.series as PriceSeriesRow[] | undefined;
  const tableRows = payload.tableRows as TableRow[] | undefined;
  if (!series?.length || !tableRows?.length) return null;
  return {
    id: panel.id,
    title: panel.title,
    chartTitle: String(payload.chartTitle ?? panel.title),
    series,
    hubs: (payload.hubs as string[]) ?? [],
    tableRows,
  };
}
