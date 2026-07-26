import { useMemo, useState } from 'react';
import { COLORS } from './tokens';

export interface TableRow {
  timestamp_utc: string;
  hub_name: string;
  dam_price: number | string;
}

const PER_PAGE = 20;

function FilterIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M2 3h12l-4.5 5.5V13L6.5 11V8.5L2 3z"
        stroke={COLORS.textMuted}
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ResetIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M3 8a5 5 0 1 1 1.5 3.5M3 8V5m0 3h3"
        stroke={COLORS.textMuted}
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Data table panel: filterable columns (funnel icons), a Clear filters reset,
 * and a paginated footer matching the DataRobot design.
 */
export function TablePanel({ rows }: { rows: TableRow[] }) {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    return rows.filter(r =>
      Object.entries(filters).every(([k, v]) =>
        v
          ? String(r[k as keyof TableRow] ?? '')
              .toLowerCase()
              .includes(v.toLowerCase())
          : true
      )
    );
  }, [rows, filters]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const clampedPage = Math.min(page, totalPages);
  const pageRows = filtered.slice((clampedPage - 1) * PER_PAGE, clampedPage * PER_PAGE);

  const columns: { key: keyof TableRow; label: string }[] = [
    { key: 'timestamp_utc', label: 'timestamp_utc' },
    { key: 'hub_name', label: 'hub_name' },
    { key: 'dam_price', label: 'dam_price' },
  ];

  const clearFilters = () => {
    setFilters({});
    setActiveFilter(null);
    setPage(1);
  };

  const pagerBtn = 'flex h-6 w-6 items-center justify-center rounded hover:opacity-80';

  return (
    <div className="space-y-2 text-xs" style={{ color: COLORS.textPrimary }}>
      <button
        onClick={clearFilters}
        className="flex items-center gap-1"
        style={{ color: COLORS.textMuted }}
      >
        <ResetIcon />
        Clear filters
      </button>

      <div className="overflow-hidden rounded-md border" style={{ borderColor: COLORS.border }}>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {columns.map(col => (
                <th
                  key={col.key}
                  className="px-3 py-2 text-left font-medium"
                  style={{ borderBottom: `1px solid ${COLORS.border}`, color: COLORS.textMuted }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate">{col.label}</span>
                    <button
                      onClick={() => setActiveFilter(activeFilter === col.key ? null : col.key)}
                      className="shrink-0"
                      aria-label={`Filter ${col.label}`}
                    >
                      <FilterIcon />
                    </button>
                  </div>
                  {activeFilter === col.key && (
                    <input
                      autoFocus
                      value={filters[col.key] ?? ''}
                      onChange={e => {
                        setFilters(f => ({ ...f, [col.key]: e.target.value }));
                        setPage(1);
                      }}
                      placeholder="Filter…"
                      className="mt-1 w-full rounded px-2 py-1 text-[11px] outline-none"
                      style={{
                        backgroundColor: COLORS.appBg,
                        border: `1px solid ${COLORS.border}`,
                        color: COLORS.textPrimary,
                      }}
                    />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r, i) => (
              <tr key={i}>
                <td className="px-3 py-1.5" style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                  {r.timestamp_utc}
                </td>
                <td className="px-3 py-1.5" style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                  {r.hub_name}
                </td>
                <td className="px-3 py-1.5" style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                  {typeof r.dam_price === 'number' ? r.dam_price.toFixed(2) : r.dam_price}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between" style={{ color: COLORS.textMuted }}>
        <div className="flex items-center gap-1">
          <button className={pagerBtn} onClick={() => setPage(1)} aria-label="First page">
            {'|<'}
          </button>
          <button
            className={pagerBtn}
            onClick={() => setPage(p => Math.max(1, p - 1))}
            aria-label="Previous page"
          >
            {'<'}
          </button>
          <button
            className={pagerBtn}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            aria-label="Next page"
          >
            {'>'}
          </button>
          <button className={pagerBtn} onClick={() => setPage(totalPages)} aria-label="Last page">
            {'>|'}
          </button>
          <span className="ml-2">
            Page {clampedPage} of {totalPages}
          </span>
        </div>
        <span>{PER_PAGE} per page</span>
      </div>
    </div>
  );
}
