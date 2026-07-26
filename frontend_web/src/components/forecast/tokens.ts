/**
 * Exact design tokens for the DataRobot "Forecast Agent App", sampled from the
 * source screenshots. Use these constants so colors stay consistent and exact.
 */
export const COLORS = {
  appBg: '#191D21',
  surface: '#23272B',
  border: '#2B3036',
  borderStrong: '#40454C',
  textPrimary: '#F5F5F5',
  textMuted: '#9AA0A6',
  accentActiveTab: '#A9B0F2',
  periwinkle: '#929BEF',
  mint: '#7EDC92',
  mintBright: '#A0F8AD',
  sky: '#69BDF7',
  lime: '#CCFB8E',
  orange: '#D5772F',
  coral: '#C17B75',
  idleBtnBg: '#40454C',
  idleBtnText: '#9197A0',
} as const;

export const HUB_SERIES_COLOR: Record<string, string> = {
  HB_HOUSTON: COLORS.mint,
  HB_NORTH: COLORS.sky,
  HB_SOUTH: COLORS.periwinkle,
  HB_WEST: COLORS.lime,
  HB_BUSAVG: COLORS.coral,
};

export const HUBS = ['HB_HOUSTON', 'HB_NORTH', 'HB_SOUTH', 'HB_WEST', 'HB_BUSAVG'];
