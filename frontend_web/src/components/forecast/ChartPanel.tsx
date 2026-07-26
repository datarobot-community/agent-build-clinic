import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { COLORS, HUB_SERIES_COLOR } from './tokens';

export interface PriceSeriesRow {
  timestamp_utc: string;
  [hub: string]: string | number;
}

function tickDate(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return ts;
  }
}

/**
 * Chart panel: multi-line hourly DAM price chart with an overlaid 2-column
 * legend in the upper-left of the plot area.
 */
export function ChartPanel({
  title,
  data,
  hubs,
}: {
  title: string;
  data: PriceSeriesRow[];
  hubs: string[];
}) {
  return (
    <div className="relative">
      <p className="mb-2 text-center text-sm font-medium" style={{ color: COLORS.textPrimary }}>
        {title}
      </p>
      <div className="relative">
        {/* Overlaid legend, upper-left, 2-column grid */}
        <div
          className="absolute left-12 top-1 z-10 grid grid-cols-2 gap-x-3 gap-y-1 rounded-md border px-2 py-1.5"
          style={{ backgroundColor: COLORS.surface, borderColor: COLORS.border }}
        >
          {hubs.map(hub => (
            <div key={hub} className="flex items-center gap-1.5">
              <span
                className="inline-block h-0.5 w-3"
                style={{ backgroundColor: HUB_SERIES_COLOR[hub] ?? COLORS.textMuted }}
              />
              <span className="text-[10px]" style={{ color: COLORS.textMuted }}>
                {hub}
              </span>
            </div>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
            <XAxis
              dataKey="timestamp_utc"
              tickFormatter={tickDate}
              tick={{ fill: COLORS.textMuted, fontSize: 10 }}
              stroke={COLORS.borderStrong}
              label={{
                value: 'Timestamp (UTC)',
                position: 'insideBottom',
                offset: -12,
                fill: COLORS.textMuted,
                fontSize: 11,
              }}
            />
            <YAxis
              tick={{ fill: COLORS.textMuted, fontSize: 10 }}
              stroke={COLORS.borderStrong}
              width={56}
              label={{
                value: 'DAM Price (USD/MWh)',
                angle: -90,
                position: 'insideLeft',
                fill: COLORS.textMuted,
                fontSize: 11,
                style: { textAnchor: 'middle' },
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: COLORS.surface,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 8,
                color: COLORS.textPrimary,
                fontSize: 12,
              }}
              labelFormatter={ts => new Date(String(ts)).toLocaleString()}
              formatter={(v: number) => [`$${Number(v).toFixed(2)}`, '']}
            />
            <Legend wrapperStyle={{ display: 'none' }} />
            {hubs.map(hub => (
              <Line
                key={hub}
                type="linear"
                dataKey={hub}
                name={hub}
                stroke={HUB_SERIES_COLOR[hub] ?? COLORS.textMuted}
                dot={false}
                strokeWidth={1.25}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
