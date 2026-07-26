import { PATHS } from '@/constants/path.ts';
import { lazy } from 'react';
import { Navigate } from 'react-router-dom';
import { ForecastAssistantPage } from './pages/ForecastAssistantPage';
import { AnalystPage } from './pages/AnalystPage';

const OAuthCallback = lazy(() => import('./pages/OAuthCallback'));

export const appRoutes = [
  { path: PATHS.OAUTH_CB, element: <OAuthCallback /> },
  { path: PATHS.CHAT_EMPTY, element: <ForecastAssistantPage /> },
  { path: PATHS.ANALYST, element: <AnalystPage /> },
  { path: '*', element: <Navigate to={PATHS.CHAT_EMPTY} replace /> },
];
