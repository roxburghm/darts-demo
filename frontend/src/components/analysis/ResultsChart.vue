<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkAreaComponent,
  MarkLineComponent,
  ToolboxComponent,
} from 'echarts/components'
import type {
  TimeSeriesResponse,
  DartsAnomalyResult,
  DartsAnomalyPoint,
  AnomalyRegion,
  ForecastPoint,
} from '@/api/types'
import { getSeriesColor, getSeverityBgColor, getSeverityColor } from '@/utils/color'

use([
  CanvasRenderer,
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkAreaComponent,
  MarkLineComponent,
  ToolboxComponent,
])

// Background tint drawn behind stretches of missing (null) data
const NULL_GAP_COLOR = 'rgba(148, 163, 184, 0.18)'

// Find contiguous runs of null values in a series and return [startTs, endTs]
// pairs. The band is widened to the surrounding valid points so it visually
// spans the whole gap left in the broken line.
function nullGapBands(timestamps: string[], values: (number | null)[]): Array<[string, string]> {
  const bands: Array<[string, string]> = []
  const n = values.length
  let j = 0
  while (j < n) {
    if (values[j] == null) {
      const start = j
      while (j < n && values[j] == null) j++
      const end = j - 1
      const startTs = timestamps[start > 0 ? start - 1 : start]
      const endTs = timestamps[end < n - 1 ? end + 1 : end]
      bands.push([startTs, endTs])
    } else {
      j++
    }
  }
  return bands
}

function getChartColors() {
  const isDark = document.documentElement.dataset.theme !== 'light'
  return isDark ? {
    axisLabel: '#64748b',
    axisLine: '#334155',
    splitLine: '#1e293b',
    tooltipBg: 'rgba(15, 23, 42, 0.95)',
    tooltipBorder: 'rgba(99, 102, 241, 0.3)',
    tooltipText: '#e2e8f0',
    legend: '#94a3b8',
    toolboxIcon: '#64748b',
    dataZoomBg: '#0f172a',
    dataZoomBorder: '#334155',
    dataZoomFiller: 'rgba(99, 102, 241, 0.15)',
    dataZoomText: '#64748b',
  } : {
    axisLabel: '#6b7280',
    axisLine: '#d1d5db',
    splitLine: '#e5e7eb',
    tooltipBg: 'rgba(255, 255, 255, 0.95)',
    tooltipBorder: 'rgba(99, 102, 241, 0.2)',
    tooltipText: '#1f2937',
    legend: '#4b5563',
    toolboxIcon: '#6b7280',
    dataZoomBg: '#f9fafb',
    dataZoomBorder: '#d1d5db',
    dataZoomFiller: 'rgba(99, 102, 241, 0.12)',
    dataZoomText: '#6b7280',
  }
}

// Reactive theme trigger — increments when data-theme attribute changes
const themeVersion = ref(0)
let themeObserver: MutationObserver | null = null

onMounted(() => {
  themeObserver = new MutationObserver(() => { themeVersion.value++ })
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  })
})

onUnmounted(() => {
  themeObserver?.disconnect()
})

const props = defineProps<{
  chartData: TimeSeriesResponse | null
  results: DartsAnomalyResult | null
  anomalies?: DartsAnomalyPoint[]
  regions?: AnomalyRegion[]
  thresholdValue?: number | null
  loading: boolean
  showFitLine?: boolean
}>()

const chartRef = ref()

function zoomToRange(start: string, end: string) {
  const chart = chartRef.value?.chart
  if (!chart) return

  // Add some padding around the region
  const startMs = new Date(start).getTime()
  const endMs = new Date(end).getTime()
  const span = endMs - startMs
  const padding = Math.max(span * 2, 3600000) // at least 1 hour padding
  const paddedStart = new Date(startMs - padding).toISOString()
  const paddedEnd = new Date(endMs + padding).toISOString()

  chart.dispatchAction({
    type: 'dataZoom',
    startValue: paddedStart,
    endValue: paddedEnd,
  })
}

function resetZoom() {
  const chart = chartRef.value?.chart
  if (!chart) return
  chart.dispatchAction({ type: 'dataZoom', start: 0, end: 100 })
}

function getZoomRange(): { start: number; end: number } | null {
  const chart = chartRef.value?.chart
  if (!chart) return null
  const opt = chart.getOption()
  const dz = opt?.dataZoom?.[0]
  if (!dz || dz.start == null) return null
  return { start: dz.start, end: dz.end }
}

function restoreZoom(range: { start: number; end: number }) {
  const chart = chartRef.value?.chart
  if (!chart) return
  chart.dispatchAction({ type: 'dataZoom', start: range.start, end: range.end })
}

defineExpose({ zoomToRange, resetZoom, getZoomRange, restoreZoom })

const chartOption = computed(() => {
  if (!props.chartData || props.chartData.series.length === 0) {
    return {}
  }

  const seriesList: any[] = []
  const legendData: string[] = []

  // --- Main time series ---
  props.chartData.series.forEach((s, i) => {
    legendData.push(s.name)
    const data = s.timestamps.map((t, j) => [t, s.values[j]])

    const markAreaData: any[] = []
    const activeRegions = props.regions ?? props.results?.regions ?? []
    if (activeRegions.length > 0) {
      for (const region of activeRegions) {
        if (s.name.includes(region.metric) || props.chartData!.series.length === 1) {
          markAreaData.push([
            {
              xAxis: region.start,
              itemStyle: { color: getSeverityBgColor(region.severity) },
            },
            {
              xAxis: region.end,
            },
          ])
        }
      }
    }

    // Shade the background behind gaps of missing (null) data
    for (const [startTs, endTs] of nullGapBands(s.timestamps, s.values)) {
      markAreaData.push([
        { xAxis: startTs, itemStyle: { color: NULL_GAP_COLOR } },
        { xAxis: endTs },
      ])
    }

    seriesList.push({
      name: s.name,
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data,
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: 1.5, color: getSeriesColor(i) },
      itemStyle: { color: getSeriesColor(i) },
      markArea: markAreaData.length > 0 ? {
        silent: true,
        data: markAreaData,
      } : undefined,
    })
  })

  // --- Original (pre-transform) series overlay ---
  if (props.chartData.original_series && props.chartData.original_series.length > 0) {
    props.chartData.original_series.forEach((s, i) => {
      legendData.push(s.name)
      const data = s.timestamps.map((t, j) => [t, s.values[j]])

      seriesList.push({
        name: s.name,
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data,
        symbol: 'none',
        lineStyle: {
          width: 1,
          type: 'dashed',
          color: getSeriesColor(i),
          opacity: 0.35,
        },
        itemStyle: {
          color: getSeriesColor(i),
          opacity: 0.35,
        },
      })
    })
  }

  // --- Model fit overlay (dashed line) ---
  // For forecast models: predicted values. For scorers: fitted baseline.
  // For peer divergence: consensus line.
  if (props.showFitLine !== false && props.results?.forecast && props.results.forecast.length > 0) {
    const forecastByMetric = new Map<string, ForecastPoint[]>()
    for (const fp of props.results.forecast) {
      if (!forecastByMetric.has(fp.metric)) {
        forecastByMetric.set(fp.metric, [])
      }
      forecastByMetric.get(fp.metric)!.push(fp)
    }

    // Choose label based on model type
    const SCORER_IDS = new Set(['kmeans', 'isolation_forest', 'lof', 'ecod', 'wasserstein'])
    const modelId = props.results.config.model_id
    let fitLabel = 'Forecast'
    if (modelId === 'peer_divergence') fitLabel = 'Consensus'
    else if (SCORER_IDS.has(modelId)) fitLabel = 'Fitted'

    let fcIdx = 0
    for (const [metric, points] of forecastByMetric) {
      const name = `${fitLabel}: ${metric}`
      legendData.push(name)
      seriesList.push({
        name,
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: points.map((p) => [p.timestamp, p.predicted]),
        symbol: 'none',
        lineStyle: {
          width: 1.5,
          type: 'dashed',
          color: getSeriesColor(props.chartData!.series.length + fcIdx),
        },
        itemStyle: {
          color: getSeriesColor(props.chartData!.series.length + fcIdx),
        },
      })
      fcIdx++
    }
  }

  // --- Anomaly scatter points ---
  // Build lookup from chart data so scatter points sit on the visible line
  // (important when transforms change the y-scale after detection)
  const activeAnomalies = props.anomalies ?? props.results?.anomalies ?? []
  if (activeAnomalies.length > 0) {
    const valueLookup = new Map<string, number>()
    for (const s of props.chartData.series) {
      for (let j = 0; j < s.timestamps.length; j++) {
        if (s.values[j] != null) {
          // Key by metric|timestamp — series name may contain dimension prefix
          const metric = s.name.split(' | ').pop() ?? s.name
          valueLookup.set(`${metric}|${s.timestamps[j]}`, s.values[j]!)
        }
      }
    }

    const scatterData = activeAnomalies
      .map((a) => {
        // Try to find the chart y-value at this timestamp; fall back to stored value
        const chartVal =
          valueLookup.get(`${a.metric}|${a.timestamp}`) ??
          (props.chartData!.series.length === 1
            ? valueLookup.get(`${props.chartData!.series[0].name}|${a.timestamp}`)
            : undefined)
        const yVal = chartVal ?? a.value ?? undefined
        return {
          value: [a.timestamp, yVal],
          itemStyle: { color: getSeverityColor(a.severity) },
        }
      })
      .filter((d) => d.value[1] != null)

    legendData.push('Anomalies')
    seriesList.push({
      name: 'Anomalies',
      type: 'scatter',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: scatterData,
      symbolSize: 6,
      z: 10,
      animation: false,
    })
  }

  // --- Score track (per-metric) ---
  const SCORE_PALETTE = ['#f97316', '#ef4444', '#eab308', '#f472b6', '#fb923c']
  const hasScores = props.results && props.results.scores.length > 0
  if (hasScores) {
    // Group scores by metric
    const scoresByMetric = new Map<string, Array<[string, number]>>()
    for (const s of props.results!.scores) {
      const key = s.metric ?? 'score'
      if (!scoresByMetric.has(key)) scoresByMetric.set(key, [])
      scoresByMetric.get(key)!.push([s.timestamp, s.score])
    }

    let scoreIdx = 0
    const isMultiMetric = scoresByMetric.size > 1
    for (const [metric, data] of scoresByMetric) {
      const color = SCORE_PALETTE[scoreIdx % SCORE_PALETTE.length]
      const name = isMultiMetric ? `Score: ${metric}` : 'Anomaly Score'
      legendData.push(name)
      const scoreSeriesConfig: any = {
        name,
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data,
        symbol: 'none',
        lineStyle: { width: 1, color },
        itemStyle: { color },
        areaStyle: { color: color + '14' },
      }
      // Threshold markLine on first score series only
      if (scoreIdx === 0 && props.thresholdValue != null) {
        scoreSeriesConfig.markLine = {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#ef4444', type: 'dashed', width: 1 },
          data: [{ yAxis: props.thresholdValue }],
          label: {
            formatter: `threshold: {c}`,
            fontSize: 9,
            color: '#ef4444',
            position: 'insideEndTop',
          },
        }
      }
      seriesList.push(scoreSeriesConfig)
      scoreIdx++
    }
  }

  // Compute overall time range from main chart data so both axes align
  let timeMin: string | undefined
  let timeMax: string | undefined
  if (props.chartData && props.chartData.series.length > 0) {
    for (const s of props.chartData.series) {
      if (s.timestamps.length > 0) {
        const first = s.timestamps[0]
        const last = s.timestamps[s.timestamps.length - 1]
        if (!timeMin || first < timeMin) timeMin = first
        if (!timeMax || last > timeMax) timeMax = last
      }
    }
  }

  // Read theme colors (themeVersion dependency makes this reactive)
  void themeVersion.value
  const tc = getChartColors()

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: tc.tooltipBg,
      borderColor: tc.tooltipBorder,
      textStyle: { color: tc.tooltipText, fontSize: 12 },
    },
    toolbox: {
      feature: {
        dataZoom: {
          yAxisIndex: 'none',
          title: { zoom: 'Drag to zoom', back: 'Undo zoom' },
        },
      },
      right: 24,
      top: 2,
      iconStyle: { borderColor: tc.toolboxIcon },
      emphasis: { iconStyle: { borderColor: '#6366f1' } },
    },
    legend: {
      data: legendData,
      textStyle: { color: tc.legend, fontSize: 11 },
      top: 4,
      right: 80,
      type: 'scroll',
    },
    grid: [
      { left: 60, right: 20, top: 40, bottom: hasScores ? '42%' : 60 },
      ...(hasScores ? [{ left: 60, right: 20, top: '65%', bottom: 40 }] : []),
    ],
    xAxis: [
      {
        type: 'time',
        gridIndex: 0,
        min: timeMin,
        max: timeMax,
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        axisLine: { lineStyle: { color: tc.axisLine } },
        splitLine: { show: false },
      },
      ...(hasScores ? [{
        type: 'time',
        gridIndex: 1,
        min: timeMin,
        max: timeMax,
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        axisLine: { lineStyle: { color: tc.axisLine } },
        splitLine: { show: false },
      }] : []),
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        splitLine: { lineStyle: { color: tc.splitLine } },
      },
      ...(hasScores ? [{
        type: 'value',
        gridIndex: 1,
        name: 'Score',
        nameTextStyle: { color: tc.axisLabel, fontSize: 10 },
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        splitLine: { lineStyle: { color: tc.splitLine } },
      }] : []),
    ],
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: hasScores ? [0, 1] : [0],
        bottom: 8,
        height: 24,
        borderColor: tc.dataZoomBorder,
        backgroundColor: tc.dataZoomBg,
        fillerColor: tc.dataZoomFiller,
        handleStyle: { color: '#6366f1' },
        textStyle: { color: tc.dataZoomText },
      },
      {
        type: 'inside',
        xAxisIndex: hasScores ? [0, 1] : [0],
        zoomOnMouseWheel: true,
        moveOnMouseMove: false,
        moveOnMouseWheel: false,
      },
    ],
    series: seriesList.map((s: any) => ({
      ...s,
      emphasis: { focus: 'series' },
      blur: { lineStyle: { opacity: 0.15 }, itemStyle: { opacity: 0.15 }, areaStyle: { opacity: 0.05 } },
    })),
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 300,
  }
})
</script>

<template>
  <div class="results-chart">
    <div v-if="loading" class="chart-loading">
      <div class="spinner" />
      <p>Loading chart data...</p>
    </div>

    <div v-else-if="!chartData || chartData.series.length === 0" class="chart-empty">
      <p>No data to display</p>
    </div>

    <VChart
      v-else
      ref="chartRef"
      :option="chartOption"
      :update-options="{ notMerge: false }"
      autoresize
      class="chart-instance"
    />
  </div>
</template>

<style scoped>
.results-chart {
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.chart-instance {
  width: 100%;
  height: 100%;
}

.chart-loading,
.chart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-md);
  color: var(--text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-primary);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
