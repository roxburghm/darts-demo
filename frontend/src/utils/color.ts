const CHART_PALETTE = [
  '#6366f1', // indigo
  '#22d3ee', // cyan
  '#f97316', // orange
  '#10b981', // emerald
  '#f43f5e', // rose
  '#a78bfa', // violet
  '#fb923c', // amber
  '#34d399', // teal
  '#e879f9', // fuchsia
  '#38bdf8', // sky
]

export function getSeriesColor(index: number): string {
  return CHART_PALETTE[index % CHART_PALETTE.length]
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'high':
      return '#ef4444'
    case 'medium':
      return '#f97316'
    case 'low':
      return '#fbbf24'
    default:
      return '#6b7280'
  }
}

export function getSeverityBgColor(severity: string): string {
  switch (severity) {
    case 'high':
      return 'rgba(239, 68, 68, 0.25)'
    case 'medium':
      return 'rgba(249, 115, 22, 0.20)'
    case 'low':
      return 'rgba(251, 191, 36, 0.15)'
    default:
      return 'rgba(107, 114, 128, 0.10)'
  }
}
