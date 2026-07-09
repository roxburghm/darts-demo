<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/dataset'
import { useAnalysisStore } from '@/stores/analysis'
import ColumnSelector from '@/components/dataset/ColumnSelector.vue'
import DimensionFilter from '@/components/dataset/DimensionFilter.vue'
import AggregationControl from '@/components/dataset/AggregationControl.vue'
import KPIEditor from '@/components/dataset/KPIEditor.vue'
import ResultsChart from '@/components/analysis/ResultsChart.vue'

const props = defineProps<{ sessionId: string }>()
const router = useRouter()
const dataset = useDatasetStore()
const analysis = useAnalysisStore()

const loading = ref(true)
const previewLoading = ref(false)
const kpiError = ref('')
const canProceed = computed(() => dataset.selectedMetrics.length > 0)
const availableMetricNames = computed(() => dataset.metricColumns.map((c) => c.name))

onMounted(async () => {
  loading.value = true
  try {
    if (!dataset.metadata || dataset.metadata.session_id !== props.sessionId) {
      await dataset.loadMetadata(props.sessionId)
    }
    dataset.restoreSelections(props.sessionId)
    // Load preview if metrics already selected (restored session)
    if (dataset.selectedMetrics.length > 0) {
      loadPreview()
    }
  } finally {
    loading.value = false
  }
})

async function loadPreview() {
  if (dataset.selectedMetrics.length === 0) {
    analysis.chartData = null
    return
  }
  previewLoading.value = true
  analysis.error = null
  try {
    const dims = dataset.selectedDimensions.length > 0 ? dataset.selectedDimensions : null
    const filters = Object.keys(dataset.dimensionFilters).length > 0 ? dataset.dimensionFilters : null
    await analysis.loadChartData(
      props.sessionId,
      dataset.selectedMetrics,
      dims,
      filters,
      dataset.aggregation,
    )
  } finally {
    previewLoading.value = false
  }
}

// Debounced watch on selection changes
let previewTimer: ReturnType<typeof setTimeout> | null = null
watch(
  [
    () => dataset.selectedMetrics,
    () => dataset.selectedDimensions,
    () => dataset.dimensionFilters,
    () => dataset.aggregation,
  ],
  () => {
    if (previewTimer) clearTimeout(previewTimer)
    previewTimer = setTimeout(loadPreview, 500)
  },
  { deep: true },
)

async function handleSaveKPIs() {
  kpiError.value = ''
  const err = await dataset.saveKPIs(props.sessionId)
  if (err) kpiError.value = err
}

function proceed() {
  dataset.persistSelections(props.sessionId)
  router.push({ name: 'models', params: { sessionId: props.sessionId } })
}

function goBack() {
  router.push({ name: 'preview', params: { sessionId: props.sessionId } })
}
</script>

<template>
  <div class="configure-view">
    <div v-if="loading" class="loading-state">
      <div class="spinner" />
      <p>Loading...</p>
    </div>

    <template v-else-if="dataset.metadata">
      <div class="configure-layout">
        <div class="configure-left">
          <div class="configure-header">
            <div class="configure-header-row">
              <button class="btn btn-ghost" @click="goBack">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
                </svg>
                Back to Preview
              </button>
              <button class="btn btn-primary" :disabled="!canProceed" @click="proceed">
                Select Model
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                </svg>
              </button>
            </div>
            <h2>Configure Columns &amp; KPIs</h2>
            <p class="text-secondary">
              Select the metrics and dimensions to analyze. Optionally define derived KPIs.
            </p>
          </div>

          <div class="configure-grid">
            <div class="configure-card">
              <AggregationControl
                :value="dataset.aggregation"
                @update="(v: any) => dataset.aggregation = v"
              />
            </div>

            <div class="configure-card">
              <ColumnSelector
                title="Metrics"
                :columns="dataset.metricColumns"
                :selected="dataset.selectedMetrics"
                @toggle="dataset.toggleMetric"
              />
            </div>

            <div class="configure-card">
              <ColumnSelector
                title="Dimensions"
                :columns="dataset.dimensionColumns"
                :selected="dataset.selectedDimensions"
                @toggle="dataset.toggleDimension"
              />
            </div>

            <div v-if="dataset.selectedDimensions.length > 0" class="configure-card">
              <DimensionFilter
                :dimension-values="dataset.dimensionValues"
                :selected-dimensions="dataset.selectedDimensions"
                :filters="dataset.dimensionFilters"
                @update-filter="dataset.setDimensionFilter"
              />
            </div>

            <div class="configure-card configure-card--wide">
              <KPIEditor
                :kpis="dataset.kpiDefinitions"
                :selected-metrics="dataset.selectedMetrics"
                :available-columns="availableMetricNames"
                :session-id="props.sessionId"
                @add="dataset.addKPI"
                @remove="dataset.removeKPI"
                @toggle="dataset.toggleMetric"
                @save="handleSaveKPIs"
              />
              <p v-if="kpiError" class="kpi-error">{{ kpiError }}</p>
            </div>
          </div>

          <div class="configure-footer">
            <div class="selection-summary">
              <span v-if="dataset.selectedMetrics.length > 0">
                {{ dataset.selectedMetrics.length }} metric{{ dataset.selectedMetrics.length !== 1 ? 's' : '' }} selected
              </span>
              <span v-else class="text-muted">No metrics selected</span>
              <span v-if="dataset.selectedDimensions.length > 0" class="text-muted">
                &middot; {{ dataset.selectedDimensions.length }} dimension{{ dataset.selectedDimensions.length !== 1 ? 's' : '' }}
              </span>
            </div>
          </div>
        </div>

        <div class="configure-right">
          <div class="preview-panel">
            <h3 class="preview-title">Data Preview</h3>
            <div v-if="dataset.selectedMetrics.length === 0" class="preview-empty">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              <p>Select metrics to preview</p>
            </div>
            <div v-else-if="analysis.error" class="preview-error">
              {{ analysis.error }}
            </div>
            <div v-else class="preview-chart-wrap">
              <ResultsChart
                :chart-data="analysis.chartData"
                :results="null"
                :loading="previewLoading"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.configure-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: calc(100vh - var(--header-height));
  max-height: calc(100vh - var(--header-height));
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  color: var(--text-secondary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-primary);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.configure-layout {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.configure-left {
  flex: 0 0 50%;
  max-width: 600px;
  overflow-y: auto;
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.configure-right {
  flex: 1;
  border-left: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--space-md);
  overflow: hidden;
}

.preview-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-sm);
  flex-shrink: 0;
}

.preview-chart-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.preview-chart-wrap :deep(.results-chart) {
  min-height: 0;
}

.preview-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  color: var(--text-muted);
  font-size: 0.85rem;
}

.configure-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.configure-header h2 {
  font-size: 1.3rem;
  font-weight: 700;
  margin: var(--space-md) 0 var(--space-xs);
}

.configure-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.configure-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
}

.configure-card--wide {
  /* no special sizing needed in single-column layout */
}

.configure-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) 0;
  border-top: 1px solid var(--border-primary);
}

.selection-summary {
  font-size: 0.9rem;
  color: var(--text-primary);
  display: flex;
  gap: var(--space-sm);
}

.kpi-error {
  font-size: 0.8rem;
  color: var(--color-error);
  margin-top: var(--space-sm);
}

.preview-error {
  padding: var(--space-lg);
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--radius-lg);
  font-size: 0.85rem;
}
</style>
