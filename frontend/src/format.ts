import type { DatasetRole, ImpactMetric, RunStatus, VariantKey, Verdict } from './api/types'

export const palette = {
  primary: '#38bdf8',
  pass: '#22c55e',
  fail: '#f43f5e',
  warning: '#f59e0b',
  muted: '#64748b',
  series: ['#38bdf8', '#a78bfa', '#f59e0b', '#34d399', '#f472b6', '#facc15'],
  variants: { clean: '#60a5fa', poisoned: '#f87171', cleaned: '#34d399' } as Record<VariantKey, string>,
}

export const metricLabels: Record<ImpactMetric, string> = {
  clean_accuracy: 'Clean accuracy',
  attack_success_rate: 'Attack success rate',
}

export const roleLabels: Record<DatasetRole, string> = {
  clean: 'Clean training',
  test: 'Clean test',
  suspect: 'Poisoned demo',
  exam: 'Benchmark exam',
}

export function f1(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toFixed(2)
}

export function percent(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? '—' : `${(value * 100).toFixed(digits)}%`
}

export function verdictType(verdict: Verdict): 'success' | 'error' | 'info' | 'default' {
  if (verdict === 'pass') return 'success'
  if (verdict === 'fail') return 'error'
  if (verdict === 'running') return 'info'
  return 'default'
}

export function statusType(status: RunStatus): 'success' | 'error' | 'info' | 'warning' | 'default' {
  if (status === 'pr_opened' || status === 'approved' || status === 'done') return 'success'
  if (['failed', 'blocked', 'error', 'rejected', 'publish_failed'].includes(status)) return 'error'
  if (status === 'awaiting_approval' || status === 'interrupted') return 'warning'
  if (status === 'running') return 'info'
  return 'default'
}

export function statusLabel(status: RunStatus): string {
  return status.replace(/_/g, ' ')
}

export function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(`${iso}Z`).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`
  return `${Math.floor(seconds / 86400)} d ago`
}
