<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/dataset'
import { useModelsStore } from '@/stores/models'
import { useAnalysisStore } from '@/stores/analysis'
import ParamPanel from '@/components/analysis/ParamPanel.vue'
import ResultsChart from '@/components/analysis/ResultsChart.vue'
import AnalysisProgress from '@/components/analysis/AnalysisProgress.vue'
import AnomalyTable from '@/components/analysis/AnomalyTable.vue'

const props = defineProps<{ sessionId: string }>()
const router = useRouter()
const dataset = useDatasetStore()
const models = useModelsStore()
const analysis = useAnalysisStore()

const loading = ref(true)
const chartRef = ref<InstanceType<typeof ResultsChart> | null>(null)
const lockZoom = ref(false)
const chartKey = ref(0)
let savedZoom: { start: number; end: number } | null = null
let socket: WebSocket | null = null
let wsRetries = 0
let wsRetryTimer: ReturnType<typeof setTimeout> | null = null
const WS_MAX_RETRIES = 5

function connectWS() {
  const wsBase = import.meta.env.DEV
    ? 'ws://localhost:8001'
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  const url = `${wsBase}/api/ws/${props.sessionId}`
  console.warn('[WS] Connecting to', url)
  socket = new WebSocket(url)

  socket.onopen = () => {
    console.warn('[WS] Connected')
    wsRetries = 0
  }

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'ping') return
      console.warn('[WS] Message:', msg)

      if (msg.type === 'progress' && msg.stage === 'analysis') {
        models.setProgress(msg.detail ?? '', msg.progress ?? 0)
      } else if (msg.type === 'complete' && msg.stage === 'analysis' && msg.run_id) {
        models.setComplete(msg.run_id)
        models.loadResults(props.sessionId, msg.run_id)
      } else if (msg.type === 'error') {
        models.error = msg.detail ?? 'Analysis failed'
        models.isRunning = false
      }
    } catch (e) {
      console.warn('[WS] Parse error:', e, event.data)
    }
  }

  socket.onerror = (event) => {
    console.warn('[WS] Error:', event)
  }

  socket.onclose = (event) => {
    console.warn('[WS] Closed:', event.code, event.reason)
    if (wsRetries < WS_MAX_RETRIES) {
      const delay = Math.min(1000 * Math.pow(2, wsRetries), 10000)
      console.warn(`[WS] Reconnecting in ${delay}ms (attempt ${wsRetries + 1}/${WS_MAX_RETRIES})`)
      wsRetryTimer = setTimeout(() => {
        wsRetries++
        connectWS()
      }, delay)
    } else {
      console.warn('[WS] Max retries reached, giving up')
    }
  }
}

onMounted(async () => {
  loading.value = true
  // Clear stale results from any previous run
  models.results = null
  models.error = null
  models.currentRunId = null
  models.isRunning = false

  try {
    if (!dataset.metadata || dataset.metadata.session_id !== props.sessionId) {
      await dataset.loadMetadata(props.sessionId)
    }
    dataset.restoreSelections(props.sessionId)

    if (models.models.length === 0) {
      await models.loadModels()
    }
    models.restoreSelection(props.sessionId)

    // Load chart data with current transforms
    await reloadChartData()

    connectWS()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  wsRetries = WS_MAX_RETRIES // prevent reconnection
  if (wsRetryTimer) {
    clearTimeout(wsRetryTimer)
    wsRetryTimer = null
  }
  if (socket) {
    socket.onclose = null
    socket.close()
    socket = null
  }
})

async function reloadChartData() {
  const dims = dataset.selectedDimensions.length > 0 ? dataset.selectedDimensions : null
  const filters = Object.keys(dataset.dimensionFilters).length > 0 ? dataset.dimensionFilters : null
  await analysis.loadChartData(
    props.sessionId,
    dataset.selectedMetrics,
    dims,
    filters,
    dataset.aggregation,
    undefined,
    undefined,
    models.smoothingWindow,
    models.transforms.length > 0 ? [...models.transforms] : undefined,
    models.infill !== 'none' ? models.infill : undefined,
  )
}

// Reload chart when transforms, smoothing, or infill change
let reloadTimer: ReturnType<typeof setTimeout> | null = null
watch(
  [() => models.transforms, () => models.smoothingWindow, () => models.infill],
  () => {
    if (reloadTimer) clearTimeout(reloadTimer)
    reloadTimer = setTimeout(async () => {
      await reloadChartData()
      if (!lockZoom.value) {
        // Increment key to force full chart re-mount so y-axis recalculates
        chartKey.value++
      }
    }, 300)
  },
  { deep: true },
)

function handleRun() {
  // Preserve current zoom before re-running
  savedZoom = chartRef.value?.getZoomRange() ?? null
  models.runDetection(props.sessionId)
}

// Restore zoom after new results arrive and chart re-renders
watch(() => models.results, (newVal) => {
  if (newVal && savedZoom) {
    const zoom = savedZoom
    savedZoom = null
    // Wait a tick for the chart to update with new data
    requestAnimationFrame(() => {
      chartRef.value?.restoreZoom(zoom)
    })
  }
})

function handleRegionClick(start: string, end: string) {
  chartRef.value?.zoomToRange(start, end)
}

function handleDetectorTypeChange(type: 'quantile' | 'threshold' | 'iqr') {
  models.detectorType = type
  // Set sensible defaults when switching detector type
  if (type === 'quantile') models.detectorThreshold = 0.95
  else if (type === 'threshold') models.detectorThreshold = models.thresholdScore ?? 1.0
  else if (type === 'iqr') models.detectorThreshold = 1.5
}

function handleResetZoom() {
  chartRef.value?.resetZoom()
}

function goBack() {
  router.push({ name: 'models', params: { sessionId: props.sessionId } })
}
</script>

<template>
  <div class="analysis-view">
    <div class="analysis-main">
      <div class="analysis-toolbar">
        <button class="btn btn-ghost btn-sm" @click="goBack">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
          </svg>
          Models
        </button>
        <h2 v-if="models.selectedModel">{{ models.selectedModel.name }}</h2>
        <div v-if="models.effectiveSummary" class="results-summary">
          <span class="summary-badge summary-badge--total">
            {{ models.effectiveSummary.total_anomalies }} anomalies
          </span>
          <span class="summary-badge summary-badge--high">
            {{ models.effectiveSummary.by_severity.high ?? 0 }} high
          </span>
          <span class="summary-badge summary-badge--medium">
            {{ models.effectiveSummary.by_severity.medium ?? 0 }} med
          </span>
          <span class="summary-badge summary-badge--low">
            {{ models.effectiveSummary.by_severity.low ?? 0 }} low
          </span>
        </div>
        <label class="toolbar-toggle" :title="models.showFitLine ? 'Showing forecast/fit overlay' : 'Forecast/fit overlay hidden'">
          <input type="checkbox" v-model="models.showFitLine" />
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="4 3">
            <line x1="2" y1="12" x2="22" y2="12"/>
          </svg>
          Show Fit
        </label>
        <label class="toolbar-toggle" :title="lockZoom ? 'Zoom preserved when transforms change' : 'Zoom resets when transforms change'">
          <input type="checkbox" v-model="lockZoom" />
          <svg v-if="lockZoom" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>
          </svg>
          Lock Zoom
        </label>
        <button class="btn btn-ghost btn-xs toolbar-reset-zoom" @click="handleResetZoom">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
          Reset Zoom
        </button>
      </div>

      <div class="chart-section">
        <ResultsChart
          :key="chartKey"
          ref="chartRef"
          :chart-data="analysis.chartData"
          :results="models.results"
          :anomalies="models.effectiveAnomalies"
          :regions="models.effectiveRegions"
          :threshold-value="models.thresholdScore"
          :loading="loading"
          :show-fit-line="models.showFitLine"
        />
      </div>

      <div class="bottom-panel">
        <AnalysisProgress
          v-if="models.isRunning"
          :progress="models.progress"
          :stage="models.progressStage"
        />

        <div v-else-if="models.results" class="results-table-wrap">
          <AnomalyTable
            :regions="models.effectiveRegions"
            :explanations="models.regionExplanations"
            @region-click="handleRegionClick"
          />
        </div>

        <div v-else-if="models.error" class="error-banner">
          {{ models.error }}
        </div>

        <div v-else class="empty-state">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <p>Configure parameters and click <strong>Run Detection</strong> to find anomalies.</p>
        </div>
      </div>
    </div>

    <aside class="analysis-sidebar">
      <ParamPanel
        v-if="models.selectedModel"
        :model="models.selectedModel"
        :params="models.params"
        :detector-type="models.detectorType"
        :detector-threshold="models.detectorThreshold"
        :smoothing-window="models.smoothingWindow"
        :transforms="models.transforms"
        :infill="models.infill"
        :scorer-id="models.scorerId"
        :results="models.results"
        :is-running="models.isRunning"
        :persistence-damping="models.persistenceDamping"
        :min-anomaly-points="models.minAnomalyPoints"
        :volume-gate-metric="models.volumeGateMetric"
        :volume-gate-threshold="models.volumeGateThreshold"
        :available-metrics="dataset.metadata?.metric_columns.map(c => c.name) ?? []"
        @update:params="(p) => models.params = p"
        @update:detector-type="handleDetectorTypeChange"
        @update:detector-threshold="(t) => models.detectorThreshold = t"
        @update:smoothing-window="(v) => models.smoothingWindow = v"
        @update:transforms="(v) => models.transforms = v"
        @update:infill="(v) => models.infill = v"
        @update:scorer-id="(v) => models.scorerId = v"
        @update:persistence-damping="(v) => models.persistenceDamping = v"
        @update:min-anomaly-points="(v) => models.minAnomalyPoints = v"
        @update:volume-gate-metric="(v) => models.volumeGateMetric = v"
        @update:volume-gate-threshold="(v) => models.volumeGateThreshold = v"
        @run="handleRun"
      />
    </aside>
  </div>
</template>

<style scoped>
.analysis-view {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.analysis-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.analysis-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-lg);
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.analysis-toolbar h2 {
  font-size: 1rem;
  font-weight: 700;
}

.results-summary {
  display: flex;
  gap: var(--space-xs);
  margin-left: auto;
}

.summary-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 9999px;
}

.summary-badge--total {
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-primary);
}

.summary-badge--high {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.summary-badge--medium {
  background: rgba(249, 115, 22, 0.15);
  color: #f97316;
}

.summary-badge--low {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

.chart-section {
  flex: 1;
  min-height: 300px;
  padding: var(--space-sm);
}

.bottom-panel {
  height: 200px;
  min-height: 150px;
  border-top: 1px solid var(--border-primary);
  overflow: auto;
}

.results-table-wrap {
  height: 100%;
  overflow: auto;
}

.toolbar-toggle {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.7rem;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
}

.toolbar-toggle input {
  display: none;
}

.toolbar-toggle:has(input:checked) {
  color: var(--accent-primary);
}

.toolbar-reset-zoom {
  font-size: 0.7rem;
  padding: 2px 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Don't let toggle push summary badges — summary already has margin-left:auto */
.results-summary ~ .toolbar-toggle {
  margin-left: var(--space-sm);
}

.results-summary ~ .toolbar-reset-zoom {
  margin-left: 0;
}

.error-banner {
  padding: var(--space-lg);
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.08);
  font-size: 0.85rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-sm);
  color: var(--text-muted);
  font-size: 0.85rem;
}

.analysis-sidebar {
  width: 300px;
  min-width: 300px;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-primary);
  padding: var(--space-lg);
  overflow-y: auto;
}

.btn-sm {
  font-size: 0.75rem;
  padding: 4px 8px;
}
</style>
