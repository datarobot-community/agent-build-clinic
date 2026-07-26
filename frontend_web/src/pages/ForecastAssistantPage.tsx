import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AppShell } from '@/components/forecast/AppShell';
import { ChartPanel } from '@/components/forecast/ChartPanel';
import { TablePanel } from '@/components/forecast/TablePanel';
import { COLORS } from '@/components/forecast/tokens';
import { useForecastChat, type ChatTurn } from '@/components/forecast/useForecastChat';
import { ForecastMarkdown } from '@/components/forecast/ForecastMarkdown';

function RefreshIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M13 8a5 5 0 1 1-1.5-3.5M13 8V5m0 3h-3"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M6 4L2.5 8 6 12M10 4l3.5 4L10 12"
        stroke={COLORS.textMuted}
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M8 2v8m0 0L5 7m3 3l3-3M3 13h10"
        stroke={COLORS.textMuted}
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden
      style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 120ms' }}
    >
      <path d="M4 6l4 4 4-4" stroke={COLORS.textMuted} strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function Label({ children }: { children: ReactNode }) {
  return (
    <div
      className="mb-1 text-[10px] font-semibold uppercase tracking-wider"
      style={{ color: COLORS.textMuted }}
    >
      {children}
    </div>
  );
}

function ToolCallRow({ label, name, body }: { label: string; name: string; body: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(o => !o)}
      className="flex w-full flex-col rounded-md border px-3 py-2 text-left"
      style={{ backgroundColor: COLORS.appBg, borderColor: COLORS.border }}
    >
      <div className="flex items-center gap-2">
        <span
          className="rounded px-1.5 py-0.5 font-mono text-[11px]"
          style={{ backgroundColor: COLORS.surface, color: COLORS.periwinkle }}
        >
          {label}: {name}
        </span>
        <span className="ml-auto">
          <ChevronIcon open={open} />
        </span>
      </div>
      {open && body && (
        <pre
          className="mt-2 overflow-x-auto rounded p-2 font-mono text-[11px]"
          style={{ backgroundColor: COLORS.surface, color: COLORS.textMuted }}
        >
          {body}
        </pre>
      )}
    </button>
  );
}

function PanelCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      className="rounded-xl border p-3"
      style={{ backgroundColor: COLORS.surface, borderColor: COLORS.border }}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium" style={{ color: COLORS.textPrimary }}>
          {title}
        </span>
        <div className="flex items-center gap-2">
          <button aria-label="View source">
            <CodeIcon />
          </button>
          <button aria-label="Download">
            <DownloadIcon />
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}

function TurnView({ turn }: { turn: ChatTurn }) {
  if (turn.kind === 'user') {
    return (
      <div>
        <Label>You</Label>
        <div
          className="inline-block rounded-md border px-3 py-2 text-sm"
          style={{ borderColor: COLORS.borderStrong, color: COLORS.textPrimary }}
        >
          {turn.text}
        </div>
      </div>
    );
  }
  if (turn.kind === 'agent-text') {
    return (
      <div>
        <Label>Agent</Label>
        <div className="text-sm leading-relaxed" style={{ color: COLORS.textPrimary }}>
          <ForecastMarkdown>{turn.text}</ForecastMarkdown>
        </div>
      </div>
    );
  }
  // tool-call
  return (
    <div className="space-y-2">
      <Label>{turn.result === null ? 'Agent' : 'Tool'}</Label>
      <ToolCallRow
        label={turn.result === null ? 'Tool Call' : 'Tool Call Result'}
        name={turn.name}
        body={turn.result ?? turn.args}
      />
    </div>
  );
}

const GREETING =
  'Hello! I can help you analyze ERCOT day-ahead prices and forecasts. Try asking about a hub ' +
  '(HB_HOUSTON, HB_NORTH, HB_SOUTH, HB_WEST, HB_BUSAVG), a date range, or what drove a specific ' +
  'forecast error.';

export function ForecastAssistantPage() {
  const [input, setInput] = useState('');
  const chat = useForecastChat();
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const isEmpty = input.trim().length === 0;

  const submit = () => {
    if (isEmpty || chat.isRunning) return;
    const text = input;
    setInput('');
    void chat.sendMessage(text);
  };

  // Autoscroll to the newest content as the stream progresses.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [chat.turns, chat.liveAgentText, chat.isThinking]);

  const rightSlot = (
    <>
      <button
        onClick={chat.clear}
        className="flex items-center gap-1.5 text-sm"
        style={{ color: COLORS.textMuted }}
      >
        <RefreshIcon />
        Clear
      </button>
      <span className="text-sm" style={{ color: COLORS.textMuted }}>
        {chat.isRunning ? 'Agent working…' : 'Agent ready'}
      </span>
    </>
  );

  return (
    <AppShell rightSlot={rightSlot}>
      <div className="flex h-full min-h-0 gap-4 px-4 pb-4">
        {/* Conversation panel */}
        <section className="flex min-h-0 flex-[0_0_63%] flex-col">
          <div ref={scrollRef} className="min-h-0 flex-1 space-y-5 overflow-auto pr-2">
            <div>
              <Label>Agent</Label>
              <p className="text-sm leading-relaxed" style={{ color: COLORS.textPrimary }}>
                {GREETING}
              </p>
            </div>

            {chat.turns.map(turn => (
              <TurnView key={turn.id} turn={turn} />
            ))}

            {chat.liveAgentText !== null && (
              <div>
                <Label>Agent</Label>
                <div className="text-sm leading-relaxed" style={{ color: COLORS.textPrimary }}>
                  <ForecastMarkdown>{chat.liveAgentText || '…'}</ForecastMarkdown>
                </div>
              </div>
            )}

            {chat.isThinking && (
              <div>
                <Label>Agent</Label>
                <p className="text-sm" style={{ color: COLORS.textMuted }}>
                  Thinking…
                </p>
              </div>
            )}

            {chat.error && (
              <div
                className="rounded-md border px-3 py-2 text-sm"
                style={{ borderColor: COLORS.coral, color: COLORS.coral }}
              >
                {chat.error}
              </div>
            )}
          </div>

          {/* Input bar */}
          <div className="mt-3 flex items-center gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              placeholder="Ask about ERCOT prices, hubs, or forecasts..."
              className="flex-1 rounded-lg border px-3 py-2.5 text-sm outline-none"
              style={{
                backgroundColor: COLORS.surface,
                borderColor: COLORS.border,
                color: COLORS.textPrimary,
              }}
            />
            <button
              onClick={submit}
              disabled={isEmpty || chat.isRunning}
              className="rounded-lg px-4 py-2.5 text-sm font-medium"
              style={
                isEmpty || chat.isRunning
                  ? { backgroundColor: COLORS.idleBtnBg, color: COLORS.idleBtnText }
                  : { backgroundColor: '#FFFFFF', color: COLORS.surface }
              }
            >
              Send
            </button>
          </div>
        </section>

        {/* Panels workspace */}
        <section className="flex min-h-0 flex-1 flex-col">
          <div className="mb-2">
            <h2 className="text-sm font-semibold" style={{ color: COLORS.textPrimary }}>
              Panels
            </h2>
            <p className="text-xs" style={{ color: COLORS.textMuted }}>
              Showing panels created during this conversation
            </p>
          </div>
          <div className="min-h-0 flex-1 space-y-3 overflow-auto pr-1">
            {chat.panels.length === 0 ? (
              <div
                className="rounded-xl border p-6 text-center text-xs"
                style={{ borderColor: COLORS.border, color: COLORS.textMuted }}
              >
                Panels created by the assistant will appear here after it calls{' '}
                <code className="text-[10px]">get_dam_prices</code>.
              </div>
            ) : (
              chat.panels.map(panel => (
                <div key={panel.id} className="space-y-3">
                  <PanelCard title={panel.title}>
                    <ChartPanel title={panel.chartTitle} data={panel.series} hubs={panel.hubs} />
                  </PanelCard>
                  <PanelCard title={`${panel.title} — data table`}>
                    <TablePanel rows={panel.tableRows} />
                  </PanelCard>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
