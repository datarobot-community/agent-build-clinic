import type { CSSProperties } from 'react';
import { Markdown } from '@/components/block/markdown';
import { cn } from '@/lib/utils';
import { COLORS } from './tokens';

const FORECAST_MARKDOWN_CLASS = cn(
  '[&_.body]:!text-[var(--forecast-markdown-text)]',
  '[&_.heading-02]:!text-[var(--forecast-markdown-text)]',
  '[&_.heading-03]:!text-[var(--forecast-markdown-text)]',
  '[&_.heading-04]:!text-[var(--forecast-markdown-text)]',
  '[&_.heading-05]:!text-[var(--forecast-markdown-text)]',
  '[&_.heading-06]:!text-[var(--forecast-markdown-text)]',
  '[&_li]:!text-[var(--forecast-markdown-text)]',
  '[&_strong]:!text-[var(--forecast-markdown-text)]',
  '[&_em]:!text-[var(--forecast-markdown-text)]'
);

/** Markdown tuned for the dark Forecast Assistant / AI Analyst surfaces. */
export function ForecastMarkdown({ children }: { children: string }) {
  return (
    <div
      className="text-sm leading-relaxed"
      style={
        {
          color: COLORS.textPrimary,
          '--forecast-markdown-text': COLORS.textPrimary,
        } as CSSProperties
      }
    >
      <Markdown className={FORECAST_MARKDOWN_CLASS}>{children}</Markdown>
    </div>
  );
}
