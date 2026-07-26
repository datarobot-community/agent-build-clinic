import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { PATHS } from '@/constants/path';
import { COLORS } from './tokens';

function LogoMark() {
  // Small stacked-bars DataRobot-style logo mark.
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
      <rect x="2" y="11" width="3.4" height="7" rx="1" fill={COLORS.accentActiveTab} />
      <rect x="8.3" y="6" width="3.4" height="12" rx="1" fill={COLORS.sky} />
      <rect x="14.6" y="2" width="3.4" height="16" rx="1" fill={COLORS.mint} />
    </svg>
  );
}

const TABS = [
  { to: PATHS.CHAT_EMPTY, label: 'Forecast Assistant' },
  { to: PATHS.ANALYST, label: 'AI Analyst' },
];

/**
 * Shared app chrome: full-width top navbar with the DataRobot logo/wordmark,
 * two pill tabs, and a per-tab right-side slot.
 */
export function AppShell({ children, rightSlot }: { children: ReactNode; rightSlot?: ReactNode }) {
  return (
    <div
      className="flex h-svh w-full flex-col"
      style={{ backgroundColor: COLORS.appBg, color: COLORS.textPrimary }}
    >
      <header className="flex items-center gap-6 px-4 py-3">
        <div className="flex items-center gap-2">
          <LogoMark />
          <span className="text-sm font-semibold tracking-tight">DataRobot</span>
        </div>
        <nav className="flex items-center gap-2">
          {TABS.map(tab => (
            <NavLink key={tab.to} to={tab.to} end={tab.to === PATHS.CHAT_EMPTY}>
              {({ isActive }) => (
                <span
                  className="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
                  style={
                    isActive
                      ? { backgroundColor: COLORS.accentActiveTab, color: '#1B1E33' }
                      : { color: COLORS.textMuted }
                  }
                >
                  {tab.label}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">{rightSlot}</div>
      </header>
      <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
