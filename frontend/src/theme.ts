import type { GlobalThemeOverrides } from 'naive-ui'

import { palette } from './format'

export const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: palette.primary,
    primaryColorHover: '#7dd3fc',
    primaryColorPressed: '#0ea5e9',
    primaryColorSuppl: palette.primary,
    successColor: palette.pass,
    errorColor: palette.fail,
    warningColor: palette.warning,
    bodyColor: '#0b0f14',
    cardColor: '#11161d',
    modalColor: '#11161d',
    popoverColor: '#151b23',
    tableColor: '#11161d',
    borderColor: 'rgba(148, 163, 184, 0.14)',
    dividerColor: 'rgba(148, 163, 184, 0.12)',
    fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
    fontFamilyMono: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
    borderRadius: '6px',
  },
  Card: {
    borderRadius: '10px',
    titleFontSizeMedium: '15px',
  },
  DataTable: {
    thColor: '#0f141a',
    tdColor: '#11161d',
    tdColorHover: '#151c25',
    thFontWeight: '600',
  },
}
