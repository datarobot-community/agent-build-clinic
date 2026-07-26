import { useEffect, useMemo, useRef, useState } from 'react';
import { AppShell } from '@/components/forecast/AppShell';
import {
  ForecastVsActualChart,
  type ForecastPoint,
} from '@/components/forecast/ForecastVsActualChart';
import { COLORS, HUBS } from '@/components/forecast/tokens';
import { useForecastVsActual, useHubs, useInvestigate } from '@/api/ercot/hooks';
import type { DriverMetric, DriverSummary, ErrorSeriesPoint, InvestigateResponse } from '@/api/ercot/types';

function BoltIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path d="M9 1L3 9h4l-1 6 6-8H8l1-6z" fill={COLORS.accentActiveTab} />
    </svg>
  );
}
function BulbIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M8 1.5a4 4 0 0 0-2.5 7.1c.4.3.6.8.6 1.3V11h3.8v-1.1c0-.5.2-1 .6-1.3A4 4 0 0 0 8 1.5zM6 13h4M6.5 14.5h3"
        stroke={COLORS.lime}
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path d="M3 8.5l3 3 7-7" stroke={COLORS.mint} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function RefreshIcon({ color }: { color: string }) {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M13 8a5 5 0 1 1-1.5-3.5M13 8V5m0 3h-3"
        stroke={color}
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MetricBadge({
  label,
  value,
  variant,
}: {
  label: string;
  value: string;
  variant: 'mint' | 'neutral' | 'coral';
}) {
  const color =
    variant === 'mint' ? COLORS.mint : variant === 'coral' ? COLORS.coral : COLORS.textMuted;
  return (
    <span
      className="rounded-md border px-2.5 py-1 text-xs font-medium"
      style={{ borderColor: color, color }}
    >
      {label}: {value}
    </span>
  );
}

// Chart uses live API data only (no mock fallback).

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}
function longDate(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleString(undefined, { month: 'long' })} ${ordinal(
    d.getUTCDate()
  )}, ${d.getUTCFullYear()}`;
}
function shortStamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' });
}

function formatDriver(metric: DriverMetric | undefined): string {
  if (!metric) return '—';
  const { actual_mw, forecast_mw } = metric;
  if (actual_mw == null && forecast_mw == null) return '—';
  if (actual_mw != null && forecast_mw != null) {
    const delta = metric.delta_mw ?? actual_mw - forecast_mw;
    return `${actual_mw.toFixed(0)} MW (forecast: ${forecast_mw.toFixed(0)} MW, ${delta >= 0 ? '+' : ''}${delta.toFixed(0)})`;
  }
  if (actual_mw != null) return `${actual_mw.toFixed(0)} MW`;
  return `forecast: ${forecast_mw!.toFixed(0)} MW`;
}

function PlatformLink({
  href,
  label,
  primary,
}: {
  href: string;
  label: string;
  primary?: boolean;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="rounded-md border px-3 py-1.5 text-xs font-medium"
      style={
        primary
          ? { backgroundColor: COLORS.accentActiveTab, color: '#1B1E33', borderColor: COLORS.accentActiveTab }
          : { borderColor: COLORS.periwinkle, color: COLORS.periwinkle }
      }
    >
      {label} ↗
    </a>
  );
}

function ActionResultView({ result }: { result: Record<string, unknown> }) {
  const type = result.type as string;
  if (type === 'compare_hubs') {
    const hubs = (result.hubs as Array<Record<string, unknown>>) ?? [];
    return (
      <div className="space-y-1">
        <div className="text-xs font-semibold" style={{ color: COLORS.textMuted }}>
          Hub comparison at this hour
        </div>
        {hubs.map(h => (
          <div key={String(h.hub_name)} className="flex justify-between gap-2 text-xs">
            <span style={{ color: h.is_primary ? COLORS.accentActiveTab : COLORS.textPrimary }}>
              {String(h.hub_name)}
              {h.is_primary ? ' (selected)' : ''}
            </span>
            <span>
              {h.dam_price_usd_mwh != null
                ? `$${Number(h.dam_price_usd_mwh).toFixed(2)}/MWh`
                : '—'}
            </span>
          </div>
        ))}
      </div>
    );
  }
  if (type === 'driver_window') {
    const series = (result.series as Array<Record<string, unknown>>) ?? [];
    return (
      <div className="space-y-1">
        <div className="text-xs font-semibold" style={{ color: COLORS.textMuted }}>
          ±6h driver window
        </div>
        {series.slice(0, 8).map((row, i) => (
          <div key={i} className="text-[11px]" style={{ color: COLORS.textMuted }}>
            {String(row.timestamp_utc ?? '').slice(0, 16)} — price $
            {row.dam_price_usd_mwh != null ? Number(row.dam_price_usd_mwh).toFixed(0) : '—'}
            {row.wind ? ` · wind ${formatDriver(row.wind as DriverMetric)}` : ''}
          </div>
        ))}
        {series.length > 8 && (
          <div className="text-[11px]" style={{ color: COLORS.textMuted }}>
            …and {series.length - 8} more hours
          </div>
        )}
      </div>
    );
  }
  if (type === 'recommend_retrain') {
    const recs = (result.recommendations as string[]) ?? [];
    return (
      <ul className="list-inside list-disc space-y-1 text-xs" style={{ color: COLORS.textPrimary }}>
        {recs.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
    );
  }
  if (type === 'start_retrain') {
    const links = (result.links as Record<string, string>) ?? {};
    const status = String(result.status ?? 'unknown');
    return (
      <div className="space-y-2 text-xs" style={{ color: COLORS.textPrimary }}>
        <p className="font-medium">{String(result.message ?? 'Retrain action completed.')}</p>
        {result.project_name ? (
          <p style={{ color: COLORS.textMuted }}>Project: {String(result.project_name)}</p>
        ) : null}
        <div className="flex flex-wrap gap-2 pt-1">
          {links.project ? (
            <PlatformLink href={links.project} label="Open retraining project" primary />
          ) : null}
          {links.deployment_retraining ? (
            <PlatformLink href={links.deployment_retraining} label="Deployment retraining" />
          ) : null}
          {links.deployment ? (
            <PlatformLink href={links.deployment} label="View deployment" />
          ) : null}
          {links.champion_project ? (
            <PlatformLink href={links.champion_project} label="Champion project" />
          ) : null}
          {links.dataset ? <PlatformLink href={links.dataset} label="Open dataset" /> : null}
        </div>
        {status === 'links_only' ? (
          <p style={{ color: COLORS.textMuted }}>
            Automatic retrain could not be started — use the platform links above.
          </p>
        ) : null}
        {status === 'project_created' ? (
          <p style={{ color: COLORS.mint }}>
            Project created — open it to launch Autopilot with the same ERCOT dataset.
          </p>
        ) : null}
      </div>
    );
  }
  if (type === 'focus_wind') {
    const lines = (result.narrative as string[]) ?? [];
    const wind = result.wind as DriverMetric | undefined;
    return (
      <div className="space-y-1 text-xs" style={{ color: COLORS.textPrimary }}>
        {lines.map((line, i) => (
          <p key={i}>{line}</p>
        ))}
        {wind && <p>Current hour: {formatDriver(wind)}</p>}
      </div>
    );
  }
  return null;
}

export function AnalystPage() {
  const { data: apiHubs } = useHubs();
  const hubs = apiHubs && apiHubs.length ? apiHubs : HUBS;

  const [hub, setHub] = useState('HB_HOUSTON');
  const [startDate, setStartDate] = useState('2025-10-21');
  const [endDate, setEndDate] = useState('2025-10-23');
  const [tavilyKey, setTavilyKey] = useState('');
  const [applied, setApplied] = useState({
    hub: 'HB_HOUSTON',
    startDate: '2025-10-21',
    endDate: '2025-10-23',
  });
  const [selected, setSelected] = useState<ForecastPoint | null>(null);
  const [narrative, setNarrative] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [investigation, setInvestigation] = useState<InvestigateResponse | null>(null);
  const streamTimer = useRef<number | null>(null);

  const { data, isPending, isFetching, isError, error } = useForecastVsActual(
    applied.hub,
    applied.startDate,
    applied.endDate
  );
  const investigate = useInvestigate();

  const points: ForecastPoint[] = useMemo(() => {
    if (!data?.error_series?.length) return [];
    return data.error_series.map((p: ErrorSeriesPoint) => ({
      timestamp_utc: p.timestamp_utc,
      actual: p.actual,
      predicted: p.predicted,
      ci_lower: p.ci_lower,
      ci_upper: p.ci_upper,
      abs_error: p.abs_error,
    }));
  }, [data]);

  const isLoadingForecast = isPending || isFetching;

  const loadError =
    isError && error
      ? error instanceof Error
        ? error.message
        : 'Forecast request failed. The server may still be running a batch job — try Update again.'
      : null;

  const metrics = data?.metrics ?? { rmse: null, mae: null, max_error: null };

  const onUpdate = () => {
    setApplied({ hub, startDate, endDate });
    setSelected(null);
    setNarrative([]);
    setInvestigation(null);
  };

  const streamNarrative = (lines: string[]) => {
    if (streamTimer.current) window.clearInterval(streamTimer.current);
    setNarrative([]);
    setStreaming(true);
    let i = 0;
    streamTimer.current = window.setInterval(() => {
      setNarrative(prev => [...prev, lines[i]]);
      i += 1;
      if (i >= lines.length) {
        if (streamTimer.current) window.clearInterval(streamTimer.current);
        setStreaming(false);
      }
    }, 500);
  };

  const runInvestigation = (p: ForecastPoint, action?: string) => {
    investigate.mutate(
      {
        timestampUtc: p.timestamp_utc,
        hubName: applied.hub,
        tavilyApiKey: tavilyKey || undefined,
        actual: p.actual,
        predicted: p.predicted,
        action,
      },
      {
        onSuccess: data => {
          setInvestigation(data);
          if (!action) {
            streamNarrative(data.narrative);
          }
        },
      }
    );
  };

  const startAnalysis = (p: ForecastPoint) => runInvestigation(p);

  const runAction = (actionId: string) => {
    if (!selected) return;
    investigate.mutate(
      {
        timestampUtc: selected.timestamp_utc,
        hubName: applied.hub,
        tavilyApiKey: tavilyKey || undefined,
        actual: selected.actual,
        predicted: selected.predicted,
        action: actionId,
      },
      {
        onSuccess: data => {
          setInvestigation(prev =>
            prev
              ? { ...prev, action_result: data.action_result, recommended_actions: data.recommended_actions }
              : data
          );
        },
      }
    );
  };

  useEffect(() => {
    return () => {
      if (streamTimer.current) window.clearInterval(streamTimer.current);
    };
  }, []);

  const errPct =
    selected && selected.actual
      ? (((selected.predicted ?? 0) - selected.actual) / selected.actual) * 100
      : 0;

  const calloutDrivers: DriverSummary = investigation?.driver_summary ?? {};

  const field = 'flex flex-col gap-1';
  const fieldLabel = 'text-[11px]';
  const inputStyle = {
    backgroundColor: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    color: COLORS.textPrimary,
  };

  const rightSlot = (
    <span
      className="flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs"
      style={{ borderColor: COLORS.border, color: COLORS.textPrimary }}
    >
      {points.length > 0 ? (
        <>
          <CheckIcon />
          Loaded {points.length} forecast points
        </>
      ) : isLoadingForecast ? (
        'Running batch forecast (1–2 min)…'
      ) : loadError ? (
        'Forecast request failed'
      ) : (
        'No forecast data for this range'
      )}
    </span>
  );

  return (
    <AppShell rightSlot={rightSlot}>
      <div className="h-full space-y-4 overflow-auto px-4 pb-6">
        {/* Section header */}
        <div className="flex items-center gap-2">
          <BoltIcon />
          <h1 className="text-base font-semibold" style={{ color: COLORS.textPrimary }}>
            AI Analyst
          </h1>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-end gap-4">
          <div className={field}>
            <label className={fieldLabel} style={{ color: COLORS.textMuted }}>
              Trading Hub
            </label>
            <select
              value={hub}
              onChange={e => setHub(e.target.value)}
              className="rounded-md px-3 py-2 text-sm outline-none"
              style={inputStyle}
            >
              {hubs.map(h => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          </div>
          <div className={field}>
            <label className={fieldLabel} style={{ color: COLORS.textMuted }}>
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
              className="rounded-md px-3 py-2 text-sm outline-none"
              style={inputStyle}
            />
          </div>
          <div className={field}>
            <label className={fieldLabel} style={{ color: COLORS.textMuted }}>
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
              className="rounded-md px-3 py-2 text-sm outline-none"
              style={inputStyle}
            />
          </div>
          <div className={field}>
            <label className={fieldLabel} style={{ color: COLORS.textMuted }}>
              Tavily API Key (Optional)
            </label>
            <input
              type="password"
              value={tavilyKey}
              onChange={e => setTavilyKey(e.target.value)}
              placeholder="Optional"
              className="rounded-md px-3 py-2 text-sm outline-none"
              style={inputStyle}
            />
          </div>
          <button
            onClick={onUpdate}
            className="flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-semibold"
            style={{ backgroundColor: '#FFFFFF', color: COLORS.surface }}
          >
            <RefreshIcon color={COLORS.surface} />
            Update
          </button>
        </div>

        {/* Chart card */}
        <div
          className="relative rounded-xl border p-4"
          style={{ backgroundColor: COLORS.surface, borderColor: COLORS.border }}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold" style={{ color: COLORS.textPrimary }}>
              Forecast vs Actual Prices
            </h2>
            <div className="flex items-center gap-2">
              <MetricBadge
                label="RMSE"
                value={metrics.rmse != null ? metrics.rmse.toFixed(2) : '—'}
                variant="mint"
              />
              <MetricBadge
                label="MAE"
                value={metrics.mae != null ? `$${metrics.mae.toFixed(2)}` : '—'}
                variant="neutral"
              />
              <MetricBadge
                label="Max Error"
                value={metrics.max_error != null ? `$${metrics.max_error.toFixed(2)}` : '—'}
                variant="coral"
              />
            </div>
          </div>

          {isLoadingForecast && (
            <p className="mb-2 text-xs" style={{ color: COLORS.textMuted }}>
              Running batch forecast for {applied.hub} — this usually takes 1–2 minutes. Please wait…
            </p>
          )}

          {loadError && !isLoadingForecast && (
            <p className="mb-2 text-xs" style={{ color: COLORS.coral }}>
              {loadError}
            </p>
          )}

          {!isLoadingForecast && !loadError && points.length === 0 && (
            <p className="mb-2 text-xs" style={{ color: COLORS.textMuted }}>
              No forecast vs actual data for {applied.hub} between {applied.startDate} and{' '}
              {applied.endDate}. Try a date range within your ERCOT dataset (e.g. before the last
              available timestamp).
            </p>
          )}

          {points.length > 0 && (
            <ForecastVsActualChart
              data={points}
              selectedTs={selected?.timestamp_utc ?? null}
              onSelect={setSelected}
              rangeStart={applied.startDate}
              rangeEnd={applied.endDate}
            />
          )}

          {/* Interactive analysis callout */}
          {selected && (
            <div
              className="absolute right-6 top-20 w-64 rounded-lg border p-3 text-xs shadow-lg"
              style={{
                backgroundColor: COLORS.appBg,
                borderColor: COLORS.borderStrong,
                color: COLORS.textPrimary,
              }}
            >
              <div className="mb-2 text-sm font-semibold">{shortStamp(selected.timestamp_utc)}</div>
              <dl className="space-y-1">
                <Row
                  k="Actual"
                  v={selected.actual != null ? `$${selected.actual.toFixed(2)}/MWh` : '—'}
                />
                <Row
                  k="Predicted"
                  v={selected.predicted != null ? `$${selected.predicted.toFixed(2)}/MWh` : '—'}
                />
                <Row
                  k="Error"
                  v={
                    selected.actual != null && selected.predicted != null
                      ? `$${(selected.predicted - selected.actual).toFixed(2)} (${errPct.toFixed(1)}%)`
                      : '—'
                  }
                />
                <Row k="RMSE Context" v={(selected.abs_error ?? 0) >= 20 ? 'High' : 'Low'} />
                {investigation?.timestamp_utc === selected.timestamp_utc && (
                  <Row
                    k="Classification"
                    v={investigation.error_mode_label}
                  />
                )}
                <Row
                  k="Wind"
                  v={
                    investigation?.timestamp_utc === selected.timestamp_utc
                      ? formatDriver(calloutDrivers.wind)
                      : '—'
                  }
                />
                <Row
                  k="Solar"
                  v={
                    investigation?.timestamp_utc === selected.timestamp_utc
                      ? formatDriver(calloutDrivers.solar)
                      : '—'
                  }
                />
              </dl>
              <button
                onClick={() => startAnalysis(selected)}
                disabled={investigate.isPending}
                className="mt-3 text-left text-xs font-medium disabled:opacity-50"
                style={{ color: COLORS.accentActiveTab }}
              >
                {investigate.isPending
                  ? 'Analyzing…'
                  : investigation?.timestamp_utc === selected.timestamp_utc
                    ? 'Re-run analysis →'
                    : 'Click to analyze this forecast error →'}
              </button>
            </div>
          )}

          {/* Legend row */}
          <div
            className="mt-3 flex flex-wrap items-center gap-4 text-[11px]"
            style={{ color: COLORS.textMuted }}
          >
            <LegendItem color={COLORS.textMuted} dashed label="90% Confidence High" />
            <LegendItem color={COLORS.textMuted} dashed label="90% Confidence Low" />
            <LegendItem color={COLORS.orange} label="Actual Price" />
            <LegendItem color={COLORS.periwinkle} dashed label="Predicted Price" />
          </div>

          {/* Streamed root-cause narrative */}
          {narrative.length > 0 && (
            <div
              className="mt-4 rounded-lg border p-3 text-sm"
              style={{ backgroundColor: COLORS.appBg, borderColor: COLORS.border }}
            >
              <div
                className="mb-1 text-xs font-semibold uppercase tracking-wider"
                style={{ color: COLORS.textMuted }}
              >
                Root-cause analysis {streaming ? '…' : ''}
                {investigation?.error_mode_label && !streaming ? (
                  <span className="ml-2 normal-case">— {investigation.error_mode_label}</span>
                ) : null}
              </div>
              <div className="space-y-1.5">
                {narrative.map((line, i) => (
                  <p key={i} style={{ color: COLORS.textPrimary }}>
                    {line}
                  </p>
                ))}
              </div>

              {!streaming && investigation?.recommended_actions?.length ? (
                <div className="mt-4 border-t pt-3" style={{ borderColor: COLORS.border }}>
                  <div
                    className="mb-2 text-xs font-semibold uppercase tracking-wider"
                    style={{ color: COLORS.textMuted }}
                  >
                    Recommended next steps
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {investigation.recommended_actions.map(action => (
                      <button
                        key={action.id}
                        type="button"
                        onClick={() => runAction(action.id)}
                        disabled={investigate.isPending}
                        title={action.description}
                        className="rounded-md border px-3 py-1.5 text-left text-xs disabled:opacity-50"
                        style={{
                          borderColor: COLORS.periwinkle,
                          color: COLORS.textPrimary,
                          backgroundColor: COLORS.surface,
                        }}
                      >
                        <span className="font-medium" style={{ color: COLORS.periwinkle }}>
                          {action.label}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {investigation?.action_result ? (
                <div
                  className="mt-4 rounded-md border p-3"
                  style={{ borderColor: COLORS.borderStrong, backgroundColor: COLORS.surface }}
                >
                  <ActionResultView result={investigation.action_result} />
                </div>
              ) : null}

              {investigation?.contributing_factors?.length ? (
                <div className="mt-4 border-t pt-3" style={{ borderColor: COLORS.border }}>
                  <div
                    className="mb-2 text-xs font-semibold uppercase tracking-wider"
                    style={{ color: COLORS.textMuted }}
                  >
                    External context
                  </div>
                  {investigation.contributing_factors.slice(0, 3).map((f, i) => (
                    <p key={i} className="text-xs" style={{ color: COLORS.textMuted }}>
                      <span className="font-medium" style={{ color: COLORS.textPrimary }}>
                        {f.factor}
                      </span>
                      {f.evidence ? ` — ${f.evidence.slice(0, 160)}…` : ''}
                    </p>
                  ))}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Instructional bar */}
        <div
          className="flex items-start gap-2 rounded-lg border p-3 text-xs"
          style={{ borderColor: COLORS.border, color: COLORS.textMuted }}
        >
          <span className="mt-0.5">
            <BulbIcon />
          </span>
          <p>
            Click any forecast point to run a structured miss investigation. The analyst classifies
            the error, explains wind/load/solar drivers from your dataset, and offers one-click
            follow-ups — compare hubs, review a ±6h driver window, or get model next-step
            recommendations.
          </p>
        </div>
      </div>
    </AppShell>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt style={{ color: COLORS.textMuted }}>{k}</dt>
      <dd className="text-right">{v}</dd>
    </div>
  );
}

function LegendItem({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className="inline-block h-0 w-4"
        style={{
          borderTop: `2px ${dashed ? 'dashed' : 'solid'} ${color}`,
        }}
      />
      {label}
    </span>
  );
}
