import type { AnomalyRegion, SeriesData } from '@/api/types'
import { formatNumber, formatTimestamp } from '@/utils/formatters'

type PatternType =
  | 'single_outlier'
  | 'spike_up'
  | 'spike_down'
  | 'volatility_increase'
  | 'gradual_drift_up'
  | 'gradual_drift_down'
  | 'level_shift_up'
  | 'level_shift_down'
  | 'sustained_deviation'

// --- Helpers ---

function mean(arr: number[]): number {
  return arr.reduce((a, b) => a + b, 0) / arr.length
}

function std(arr: number[]): number {
  if (arr.length < 2) return 0
  const m = mean(arr)
  return Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / (arr.length - 1))
}

/** Spearman rank correlation with index (detects monotonic trend). */
function rankCorrelation(values: number[]): number {
  const n = values.length
  if (n < 4) return 0
  // Rank the values
  const indexed = values.map((v, i) => ({ v, i }))
  indexed.sort((a, b) => a.v - b.v)
  const ranks = new Array<number>(n)
  for (let k = 0; k < n; k++) ranks[indexed[k].i] = k + 1
  // Spearman: 1 - 6 * sum(d^2) / (n*(n^2-1))
  let sumD2 = 0
  for (let i = 0; i < n; i++) {
    const d = ranks[i] - (i + 1)
    sumD2 += d * d
  }
  return 1 - (6 * sumD2) / (n * (n * n - 1))
}

function formatDuration(startMs: number, endMs: number): string {
  const diffMs = Math.abs(endMs - startMs)
  const minutes = diffMs / 60_000
  if (minutes < 2) return '1 minute'
  if (minutes < 120) return `${Math.round(minutes)} minutes`
  const hours = minutes / 60
  if (hours < 48) return `${Math.round(hours)} hours`
  const days = hours / 24
  return `${Math.round(days)} days`
}

function changePctPhrase(changePct: number): string {
  const abs = Math.abs(changePct)
  const dir = changePct >= 0 ? 'above' : 'below'
  return `${abs.toFixed(0)}% ${dir}`
}

/** Find the SeriesData entry matching a region's metric, accounting for dimension prefixes. */
function findSeries(region: AnomalyRegion, seriesData: SeriesData[]): SeriesData | null {
  // Exact match first
  let match = seriesData.find((s) => s.name === region.metric)
  if (match) return match
  // Match by suffix: series name like "MOID=x | MetricName"
  match = seriesData.find((s) => {
    const parts = s.name.split(' | ')
    return parts[parts.length - 1] === region.metric
  })
  if (match) return match
  // If region has dimension_values, try matching with dimension prefix
  if (region.dimension_values) {
    const dimParts = Object.entries(region.dimension_values).map(([k, v]) => `${k}=${v}`)
    const prefix = dimParts.join(' | ')
    match = seriesData.find(
      (s) => s.name === `${prefix} | ${region.metric}`,
    )
  }
  return match ?? null
}

/** Extract non-null numeric values from a slice of a series. */
function sliceValues(
  series: SeriesData,
  startIdx: number,
  endIdx: number,
): number[] {
  const vals: number[] = []
  for (let i = Math.max(0, startIdx); i <= Math.min(endIdx, series.values.length - 1); i++) {
    const v = series.values[i]
    if (v != null && isFinite(v)) vals.push(v)
  }
  return vals
}

/** Find the index of the closest timestamp >= target. */
function findTimestampIndex(timestamps: string[], target: string): number {
  const targetMs = new Date(target).getTime()
  // Binary search for efficiency
  let lo = 0
  let hi = timestamps.length - 1
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (new Date(timestamps[mid]).getTime() < targetMs) lo = mid + 1
    else hi = mid
  }
  return lo
}

// --- Main ---

export function explainRegion(
  region: AnomalyRegion,
  seriesData: SeriesData[],
): string {
  const series = findSeries(region, seriesData)
  if (!series || series.timestamps.length === 0) {
    return `${region.metric} anomaly detected from ${formatTimestamp(region.start)} to ${formatTimestamp(region.end)}.`
  }

  const startIdx = findTimestampIndex(series.timestamps, region.start)
  const endIdx = findTimestampIndex(series.timestamps, region.end)

  const inside = sliceValues(series, startIdx, endIdx)
  if (inside.length === 0) {
    return `${region.metric} anomaly detected from ${formatTimestamp(region.start)} to ${formatTimestamp(region.end)}.`
  }

  // Context window: same length as inside, or at least 5 points, before the region
  const contextLen = Math.max(inside.length, 5)
  const before = sliceValues(series, startIdx - contextLen, startIdx - 1)

  const insideMean = mean(inside)
  const insideMax = Math.max(...inside)
  const insideMin = Math.min(...inside)
  const insideStd = std(inside)

  const hasBaseline = before.length >= 3
  const beforeMean = hasBaseline ? mean(before) : null
  const beforeStd = hasBaseline ? std(before) : null

  // Percentage change vs baseline
  let changePct = 0
  if (beforeMean != null && Math.abs(beforeMean) > 1e-10) {
    changePct = ((insideMean - beforeMean) / Math.abs(beforeMean)) * 100
  }

  const startMs = new Date(region.start).getTime()
  const endMs = new Date(region.end).getTime()
  const metric = region.metric
  const start = formatTimestamp(region.start)

  // --- Pattern classification ---
  let pattern: PatternType

  if (region.point_count === 1) {
    pattern = 'single_outlier'
  } else if (region.point_count <= 3 && hasBaseline) {
    pattern = insideMean > (beforeMean ?? 0) ? 'spike_up' : 'spike_down'
  } else if (
    hasBaseline &&
    beforeStd != null &&
    beforeStd > 1e-10 &&
    insideStd / beforeStd > 2.0
  ) {
    pattern = 'volatility_increase'
  } else if (region.point_count >= 4) {
    const corr = rankCorrelation(inside)
    if (corr > 0.7) {
      pattern = 'gradual_drift_up'
    } else if (corr < -0.7) {
      pattern = 'gradual_drift_down'
    } else if (hasBaseline && insideMean > (beforeMean ?? 0)) {
      pattern = 'level_shift_up'
    } else if (hasBaseline && insideMean < (beforeMean ?? 0)) {
      pattern = 'level_shift_down'
    } else {
      pattern = 'sustained_deviation'
    }
  } else {
    pattern = 'sustained_deviation'
  }

  // --- Template rendering ---
  const dur = region.point_count === 1 ? '1 point' : formatDuration(startMs, endMs)
  const fmtBaseline = beforeMean != null ? formatNumber(beforeMean) : '?'
  const pctPhrase = changePctPhrase(changePct)

  switch (pattern) {
    case 'single_outlier': {
      const val = formatNumber(inside[0])
      if (!hasBaseline) {
        return `${metric} had a single anomalous reading of ${val} at ${start}.`
      }
      return `${metric} had a single anomalous reading of ${val} at ${start}, ${pctPhrase} the baseline of ${fmtBaseline}.`
    }
    case 'spike_up':
      return `${metric} spiked to ${formatNumber(insideMax)} around ${start}, ${pctPhrase} the preceding baseline of ${fmtBaseline}.`
    case 'spike_down':
      return `${metric} dropped sharply to ${formatNumber(insideMin)} around ${start}, ${pctPhrase} the preceding baseline of ${fmtBaseline}.`
    case 'volatility_increase': {
      const ratio = (insideStd / (beforeStd ?? 1)).toFixed(1)
      return `${metric} became unusually volatile over ${dur} starting ${start}, with ${ratio}x the normal variation.`
    }
    case 'gradual_drift_up':
      return `${metric} gradually increased over ${dur} starting ${start}, rising from ${formatNumber(inside[0])} to ${formatNumber(inside[inside.length - 1])}.`
    case 'gradual_drift_down':
      return `${metric} gradually decreased over ${dur} starting ${start}, falling from ${formatNumber(inside[0])} to ${formatNumber(inside[inside.length - 1])}.`
    case 'level_shift_up':
      return `${metric} shifted to a higher level averaging ${formatNumber(insideMean)} over ${dur} starting ${start}, up ${Math.abs(changePct).toFixed(0)}% from the prior baseline of ${fmtBaseline}.`
    case 'level_shift_down':
      return `${metric} shifted to a lower level averaging ${formatNumber(insideMean)} over ${dur} starting ${start}, down ${Math.abs(changePct).toFixed(0)}% from the prior baseline of ${fmtBaseline}.`
    case 'sustained_deviation':
    default:
      if (hasBaseline) {
        return `${metric} deviated from normal over ${dur} starting ${start}, averaging ${formatNumber(insideMean)} vs a baseline of ${fmtBaseline} (${pctPhrase}).`
      }
      return `${metric} deviated from normal over ${dur} starting ${start}, averaging ${formatNumber(insideMean)}.`
  }
}
