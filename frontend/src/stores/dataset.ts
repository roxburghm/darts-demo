import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { DatasetMetadata, DimensionValues, AggregationLevel, KPIDefinition } from '@/api/types'
import { getDatasetMetadata, getDimensionValues, saveKPIs as apiSaveKPIs } from '@/api/datasets'

export const useDatasetStore = defineStore('dataset', () => {
  const metadata = ref<DatasetMetadata | null>(null)
  const dimensionValues = ref<DimensionValues[]>([])
  const selectedMetrics = ref<string[]>([])
  const selectedDimensions = ref<string[]>([])
  const dimensionFilters = ref<Record<string, string[]>>({})
  const aggregation = ref<AggregationLevel>('1h')
  const loading = ref(false)
  const kpiDefinitions = ref<KPIDefinition[]>([])

  const metricColumns = computed(() => metadata.value?.metric_columns ?? [])
  const dimensionColumns = computed(() => metadata.value?.dimension_columns ?? [])
  const timestampColumn = computed(() => metadata.value?.timestamp_column ?? '')
  const timeRange = computed(() => metadata.value?.time_range ?? null)

  async function loadMetadata(sessionId: string) {
    loading.value = true
    try {
      metadata.value = await getDatasetMetadata(sessionId)
      dimensionValues.value = await getDimensionValues(sessionId)
      kpiDefinitions.value = metadata.value?.kpi_definitions ?? []
    } finally {
      loading.value = false
    }
  }

  // --- sessionStorage persistence (keyed by sessionId) ---
  const _storageKey = (sessionId: string) => `dataset-selections:${sessionId}`

  function persistSelections(sessionId: string) {
    const data = {
      selectedMetrics: selectedMetrics.value,
      selectedDimensions: selectedDimensions.value,
      dimensionFilters: dimensionFilters.value,
      aggregation: aggregation.value,
    }
    sessionStorage.setItem(_storageKey(sessionId), JSON.stringify(data))
  }

  function restoreSelections(sessionId: string): boolean {
    const raw = sessionStorage.getItem(_storageKey(sessionId))
    if (!raw) return false
    try {
      const data = JSON.parse(raw)
      if (data.selectedMetrics) selectedMetrics.value = data.selectedMetrics
      if (data.selectedDimensions) selectedDimensions.value = data.selectedDimensions
      if (data.dimensionFilters) dimensionFilters.value = data.dimensionFilters
      if (data.aggregation) aggregation.value = data.aggregation
      return true
    } catch {
      return false
    }
  }

  function toggleMetric(name: string) {
    const idx = selectedMetrics.value.indexOf(name)
    if (idx >= 0) {
      selectedMetrics.value.splice(idx, 1)
    } else {
      selectedMetrics.value.push(name)
    }
  }

  function toggleDimension(name: string) {
    const idx = selectedDimensions.value.indexOf(name)
    if (idx >= 0) {
      selectedDimensions.value.splice(idx, 1)
      delete dimensionFilters.value[name]
    } else {
      selectedDimensions.value.push(name)
    }
  }

  function setDimensionFilter(column: string, values: string[]) {
    if (values.length === 0) {
      delete dimensionFilters.value[column]
    } else {
      dimensionFilters.value[column] = values
    }
  }

  function addKPI(kpi: KPIDefinition) {
    kpiDefinitions.value.push(kpi)
  }

  function removeKPI(name: string) {
    kpiDefinitions.value = kpiDefinitions.value.filter((k) => k.name !== name)
    // Also deselect it if it was selected as a metric
    const idx = selectedMetrics.value.indexOf(name)
    if (idx >= 0) selectedMetrics.value.splice(idx, 1)
  }

  async function saveKPIs(sessionId: string): Promise<string | null> {
    try {
      await apiSaveKPIs(sessionId, kpiDefinitions.value)
      return null
    } catch (e: any) {
      const detail = e.response?.data?.detail
      if (detail?.errors) {
        return Object.entries(detail.errors)
          .map(([name, err]) => `${name}: ${err}`)
          .join('; ')
      }
      return detail?.message || e.message || 'Failed to save KPIs'
    }
  }

  function reset() {
    metadata.value = null
    dimensionValues.value = []
    selectedMetrics.value = []
    selectedDimensions.value = []
    dimensionFilters.value = {}
    aggregation.value = '1h'
    loading.value = false
    kpiDefinitions.value = []
  }

  return {
    metadata,
    dimensionValues,
    selectedMetrics,
    selectedDimensions,
    dimensionFilters,
    aggregation,
    loading,
    kpiDefinitions,
    metricColumns,
    dimensionColumns,
    timestampColumn,
    timeRange,
    loadMetadata,
    persistSelections,
    restoreSelections,
    toggleMetric,
    toggleDimension,
    setDimensionFilter,
    addKPI,
    removeKPI,
    saveKPIs,
    reset,
  }
})
