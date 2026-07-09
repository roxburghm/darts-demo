import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TimeSeriesResponse, AggregationLevel, TransformId, InfillMethod } from '@/api/types'
import { getTimeSeries } from '@/api/analysis'

export const useAnalysisStore = defineStore('analysis', () => {
  const chartData = ref<TimeSeriesResponse | null>(null)
  const error = ref<string | null>(null)

  async function loadChartData(
    sessionId: string,
    metrics: string[],
    dimensions: string[] | null,
    dimensionFilters: Record<string, string[]> | null,
    aggregation: AggregationLevel,
    timeStart?: string,
    timeEnd?: string,
    smoothingWindow?: number,
    transforms?: TransformId[],
    infill?: InfillMethod,
  ) {
    try {
      chartData.value = await getTimeSeries(sessionId, {
        metrics,
        dimensions,
        dimension_filters: dimensionFilters,
        aggregation,
        time_start: timeStart,
        time_end: timeEnd,
        max_points: 3000,
        smoothing_window: smoothingWindow ?? 1,
        transforms: transforms ?? [],
        infill: infill ?? 'none',
      })
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      error.value = detail || err?.message || 'Failed to load chart data'
    }
  }

  function reset() {
    chartData.value = null
    error.value = null
  }

  return {
    chartData,
    error,
    loadChartData,
    reset,
  }
})
