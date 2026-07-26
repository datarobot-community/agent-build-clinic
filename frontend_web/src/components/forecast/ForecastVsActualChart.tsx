import { useMemo } from 'react';
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { COLORS } from './tokens';

export interface ForecastPoint {
  timestamp_utc: string;
  actual: number | null;
  predicted: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  abs_error: number | null;
}

type ChartRow = ForecastPoint & { ts: number };

function tickLabel(ts: number): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
    });
  } catch {
    return String(ts);
  }
}

function parseUtcDate(dateOnly: string): number {
  return Date.parse(`${dateOnly}T00:00:00Z`);
}

function endOfUtcDay(dateOnly: string): number {
  return Date.parse(`${dateOnly}T23:59:59.999Z`);
}

interface Props {
  data: ForecastPoint[];
  selectedTs: string | null;
  onSelect: (p: ForecastPoint) => void;
  rangeStart?: string;
  rangeEnd?: string;
}

const ERROR_THRESHOLD = 20;

export function ForecastVsActualChart({
  data,
  selectedTs,
  onSelect,
  rangeStart,
  rangeEnd,
}: Props) {
  const chartData = useMemo(() => {
    const seen = new Set<number>();
    return data
      .map(row => ({ ...row, ts: Date.parse(row.timestamp_utc) }))
      .filter((row): row is ChartRow => !Number.isNaN(row.ts))
      .filter(row => {
        if (seen.has(row.ts)) return false;
        seen.add(row.ts);
        return true;
      })
      .sort((a, b) => a.ts - b.ts);
  }, [data]);

  const xDomain = useMemo((): [number, number] => {
    if (rangeStart && rangeEnd) {
      const min = parseUtcDate(rangeStart);
      const max = endOfUtcDay(rangeEnd);
      if (!Number.isNaN(min) && !Number.isNaN(max) && max > min) {
        return [min, max];
      }
    }
    if (chartData.length === 0) {
      return [0, 1];
    }
    return [chartData[0].ts, chartData[chartData.length - 1].ts];
  }, [chartData, rangeStart, rangeEnd]);

  const selected = chartData.find(d => d.timestamp_utc === selectedTs) ?? null;

  const renderDot = (props: { cx?: number; cy?: number; payload?: ChartRow }) => {
    const { cx, cy, payload } = props;
    if (cx == null || cy == null || !payload) return <g />;
    const isSelected = payload.timestamp_utc === selectedTs;
    const isError = (payload.abs_error ?? 0) >= ERROR_THRESHOLD;
    const fill = isSelected ? '#F2D024' : isError ? '#E5484D' : COLORS.periwinkle;
    return (
      <circle
        cx={cx}
        cy={cy}
        r={isSelected ? 5 : 3}
        fill={fill}
        stroke={isSelected ? '#F2D024' : '#00000000'}
        strokeWidth={isSelected ? 2 : 0}
        style={{ cursor: 'pointer' }}
        onClick={() => onSelect(payload)}
      />
    );
  };

  return (
    <ResponsiveContainer width="100%" height={360}>
      <ComposedChart data={chartData} margin={{ top: 12, right: 16, bottom: 36, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
        <XAxis
          type="number"
          dataKey="ts"
          scale="time"
          domain={xDomain}
          tickFormatter={tickLabel}
          tick={{ fill: COLORS.textMuted, fontSize: 10 }}
          stroke={COLORS.borderStrong}
          angle={-35}
          textAnchor="end"
          height={50}
        />
        <YAxis
          domain={[0, 140]}
          ticks={[0, 35, 70, 105, 140]}
          tick={{ fill: COLORS.textMuted, fontSize: 10 }}
          stroke={COLORS.borderStrong}
          width={56}
          label={{
            value: 'Price ($/MWh)',
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
          labelFormatter={ts => new Date(Number(ts)).toLocaleString()}
          formatter={(v: number, name: string) => [
            v == null ? '—' : `$${Number(v).toFixed(2)}`,
            name,
          ]}
        />
        <Line
          type="monotone"
          dataKey="ci_upper"
          name="90% Confidence High"
          stroke={COLORS.textMuted}
          strokeDasharray="2 3"
          strokeWidth={1}
          dot={false}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="ci_lower"
          name="90% Confidence Low"
          stroke={COLORS.textMuted}
          strokeDasharray="2 3"
          strokeWidth={1}
          dot={false}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="actual"
          name="Actual Price"
          stroke={COLORS.orange}
          strokeWidth={2}
          dot={false}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="predicted"
          name="Predicted Price"
          stroke={COLORS.periwinkle}
          strokeDasharray="5 4"
          strokeWidth={2}
          dot={renderDot}
          activeDot={renderDot}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Scatter data={chartData} dataKey="predicted" shape={renderDot} isAnimationActive={false} />
        {selected && (
          <ReferenceLine
            x={selected.ts}
            stroke="#F2D024"
            strokeDasharray="4 3"
            strokeWidth={1}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
