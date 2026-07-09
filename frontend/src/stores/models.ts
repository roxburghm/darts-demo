import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ModelInfo,
  ModelCompatibility,
  DartsDetectionConfig,
  DartsAnomalyResult,
  DartsAnomalyPoint,
  AnomalyRegion,
  AnomalySummary,
  TransformId,
  InfillMethod,
} from '@/api/types'
import {
  getModels,
  checkCompatibility,
  triggerDartsDetection,
  getDartsResults,
} from '@/api/models'
import { useDatasetStore } from './dataset'
import { useAnalysisStore } from './analysis'
import { explainRegion } from '@/utils/explainer'

export const useModelsStore = defineStore('models', () => {
  const models = ref<ModelInfo[]>([])
  const compatibility = ref<ModelCompatibility[]>([])
  const selectedModelId = ref<string | null>(null)
  const params = ref<Record<string, number | boolean | string>>({})
  const detectorType = ref<'quantile' | 'threshold' | 'iqr'>('quantile')
  const detectorThreshold = ref(0.95)
  const smoothingWindow = ref(1)
  const transforms = ref<TransformId[]>([])
  const infill = ref<InfillMethod>('none')
  const scorerId = ref('difference')
  const showFitLine = ref(true)
  // Anomaly filtering
  const persistenceDamping = ref(0)
  const minAnomalyPoints = ref(1)
  const volumeGateMetric = ref<string | null>(null)
  const volumeGateThreshold = ref(0)

  // Detection state
  const currentRunId = ref<string | null>(null)
  const results = ref<DartsAnomalyResult | null>(null)
  const isRunning = ref(false)
  const progress = ref(0)
  const progressStage = ref('')
  const error = ref<string | null>(null)

  const selectedModel = computed(() =>
    models.value.find((m) => m.id === selectedModelId.value) ?? null,
  )

  // --- Client-side threshold recomputation ---

  /** The actual score cutoff value derived from the current threshold setting */
  const thresholdScore = computed<number | null>(() => {
    if (!results.value || results.value.scores.length === 0) return null
    const scores = results.value.scores.map((s) => s.score).filter((v) => v > 0)
    if (scores.length === 0) return null
    if (detectorType.value === 'threshold') return detectorThreshold.value
    if (detectorType.value === 'iqr') {
      scores.sort((a, b) => a - b)
      const q1 = scores[Math.floor(scores.length * 0.25)]
      const q3 = scores[Math.floor(scores.length * 0.75)]
      const iqr = q3 - q1
      return q3 + detectorThreshold.value * iqr // upper fence
    }
    scores.sort((a, b) => a - b)
    const idx = Math.min(Math.floor(detectorThreshold.value * scores.length), scores.length - 1)
    return scores[idx]
  })

  /** Anomaly points recomputed from raw scores + current threshold */
  const effectiveAnomalies = computed<DartsAnomalyPoint[]>(() => {
    const cutoff = thresholdScore.value
    if (!results.value || cutoff == null) return []
    return results.value.scores
      .filter((s) => s.score >= cutoff)
      .map((s) => ({
        timestamp: s.timestamp,
        metric: s.metric,
        value: 0, // chart lookup handles actual y-value
        score: s.score,
        is_anomaly: true,
        severity: classifySeverity(s.score, cutoff),
      }))
  })

  /** Anomaly regions merged from effective anomalies */
  const effectiveRegions = computed<AnomalyRegion[]>(() => {
    const points = effectiveAnomalies.value
    if (points.length === 0) return []

    const grouped = new Map<string, DartsAnomalyPoint[]>()
    for (const p of points) {
      const key = p.metric
      if (!grouped.has(key)) grouped.set(key, [])
      grouped.get(key)!.push(p)
    }

    const regions: AnomalyRegion[] = []
    for (const [metric, group] of grouped) {
      group.sort((a, b) => a.timestamp.localeCompare(b.timestamp))

      // Compute median time step for gap detection
      let medianStep = 3600000 // 1 hour default (ms)
      if (group.length > 1) {
        const diffs: number[] = []
        for (let i = 1; i < group.length; i++) {
          const d = new Date(group[i].timestamp).getTime() - new Date(group[i - 1].timestamp).getTime()
          if (d > 0) diffs.push(d)
        }
        if (diffs.length > 0) {
          diffs.sort((a, b) => a - b)
          medianStep = diffs[Math.floor(diffs.length / 2)]
        }
      }

      let region: DartsAnomalyPoint[] = [group[0]]
      for (let i = 1; i < group.length; i++) {
        const gap = new Date(group[i].timestamp).getTime() - new Date(region[region.length - 1].timestamp).getTime()
        if (gap <= medianStep * 2) {
          region.push(group[i])
        } else {
          regions.push(buildRegion(region, metric))
          region = [group[i]]
        }
      }
      regions.push(buildRegion(region, metric))
    }

    // Apply client-side persistence damping
    const damping = persistenceDamping.value
    const minPts = minAnomalyPoints.value
    const cutoff = thresholdScore.value
    if ((damping <= 0 && minPts <= 1) || cutoff == null) return regions
    return regions
      .filter((r) => r.point_count >= minPts)
      .map((r) => {
        if (damping > 0 && r.point_count > 1) {
          const eff = r.avg_score * (1 + damping * Math.log2(r.point_count))
          return { ...r, severity: classifySeverity(eff, cutoff) }
        }
        return r
      })
  })

  /** Summary recomputed from effective anomalies */
  const effectiveSummary = computed<AnomalySummary | null>(() => {
    if (!results.value) return null
    const points = effectiveAnomalies.value
    const bySeverity: Record<string, number> = { low: 0, medium: 0, high: 0 }
    const byMetric: Record<string, number> = {}
    for (const p of points) {
      bySeverity[p.severity] = (bySeverity[p.severity] ?? 0) + 1
      byMetric[p.metric] = (byMetric[p.metric] ?? 0) + 1
    }
    return {
      total_points_analyzed: results.value.summary.total_points_analyzed,
      total_anomalies: points.length,
      total_regions: effectiveRegions.value.length,
      by_severity: bySeverity,
      by_metric: byMetric,
    }
  })

  /** Human-readable explanation for each effective region, keyed by metric|start|end */
  const regionExplanations = computed<Map<string, string>>(() => {
    const analysis = useAnalysisStore()
    const map = new Map<string, string>()
    if (!analysis.chartData) return map
    for (const region of effectiveRegions.value) {
      const key = `${region.metric}|${region.start}|${region.end}`
      map.set(key, explainRegion(region, analysis.chartData.series))
    }
    return map
  })

  async function loadModels() {
    models.value = await getModels()
  }

  async function loadCompatibility(sessionId: string) {
    const dataset = useDatasetStore()
    try {
      const response = await checkCompatibility(sessionId, {
        metrics: dataset.selectedMetrics,
        dimensions: dataset.selectedDimensions.length > 0 ? dataset.selectedDimensions : null,
        dimension_filters:
          Object.keys(dataset.dimensionFilters).length > 0 ? dataset.dimensionFilters : null,
        aggregation: dataset.aggregation,
      })
      compatibility.value = response.models
    } catch (err) {
      console.warn('Failed to load compatibility, showing all models:', err)
      compatibility.value = []
    }
  }

  function selectModel(modelId: string) {
    selectedModelId.value = modelId
    const model = models.value.find((m) => m.id === modelId)
    if (model) {
      const defaults: Record<string, number | boolean | string> = {}
      for (const param of model.params) {
        defaults[param.name] = param.default
      }
      params.value = defaults
    }
  }

  function isCompatible(modelId: string): boolean {
    const entry = compatibility.value.find((c) => c.model_id === modelId)
    return entry?.compatible ?? true
  }

  function getIncompatibilityReason(modelId: string): string | null {
    const entry = compatibility.value.find((c) => c.model_id === modelId)
    return entry?.reason ?? null
  }

  async function runDetection(sessionId: string) {
    if (!selectedModelId.value) return

    const dataset = useDatasetStore()
    isRunning.value = true
    progress.value = 0
    error.value = null
    results.value = null

    const config: DartsDetectionConfig = {
      model_id: selectedModelId.value,
      metrics: dataset.selectedMetrics,
      dimensions: dataset.selectedDimensions.length > 0 ? dataset.selectedDimensions : null,
      dimension_filters:
        Object.keys(dataset.dimensionFilters).length > 0 ? dataset.dimensionFilters : null,
      aggregation: dataset.aggregation,
      params: { ...params.value },
      detector_type: detectorType.value,
      detector_threshold: detectorThreshold.value,
      smoothing_window: smoothingWindow.value,
      transforms: [...transforms.value],
      infill: infill.value,
      scorer_id: scorerId.value,
      random_seed: null,
      persistence_damping: persistenceDamping.value,
      min_anomaly_points: minAnomalyPoints.value,
      volume_gate_metric: volumeGateMetric.value,
      volume_gate_threshold: volumeGateThreshold.value,
    }

    try {
      const { run_id } = await triggerDartsDetection(sessionId, config)
      currentRunId.value = run_id
    } catch (err: any) {
      error.value = err?.message || 'Detection failed'
      isRunning.value = false
    }
  }

  async function loadResults(sessionId: string, runId: string) {
    try {
      results.value = await getDartsResults(sessionId, runId)
      isRunning.value = false
    } catch (err: any) {
      error.value = err?.message || 'Failed to load results'
      isRunning.value = false
    }
  }

  function setProgress(stage: string, value: number) {
    progressStage.value = stage
    progress.value = value
  }

  function setComplete(runId: string) {
    currentRunId.value = runId
    progress.value = 100
    // Note: isRunning stays true until loadResults resolves, so the UI
    // keeps showing the progress indicator instead of the empty state.
  }

  function persistSelection(sessionId: string) {
    sessionStorage.setItem(
      `model-selection:${sessionId}`,
      JSON.stringify({
        selectedModelId: selectedModelId.value,
        params: params.value,
        detectorType: detectorType.value,
        detectorThreshold: detectorThreshold.value,
        smoothingWindow: smoothingWindow.value,
        transforms: transforms.value,
        infill: infill.value,
        scorerId: scorerId.value,
        showFitLine: showFitLine.value,
        persistenceDamping: persistenceDamping.value,
        minAnomalyPoints: minAnomalyPoints.value,
        volumeGateMetric: volumeGateMetric.value,
        volumeGateThreshold: volumeGateThreshold.value,
      }),
    )
  }

  function restoreSelection(sessionId: string): boolean {
    const raw = sessionStorage.getItem(`model-selection:${sessionId}`)
    if (!raw) return false
    try {
      const data = JSON.parse(raw)
      selectedModelId.value = data.selectedModelId
      params.value = data.params
      detectorType.value = data.detectorType
      detectorThreshold.value = data.detectorThreshold
      smoothingWindow.value = data.smoothingWindow ?? 1
      transforms.value = data.transforms ?? []
      infill.value = data.infill ?? 'none'
      scorerId.value = data.scorerId ?? 'difference'
      showFitLine.value = data.showFitLine ?? true
      persistenceDamping.value = data.persistenceDamping ?? 0
      minAnomalyPoints.value = data.minAnomalyPoints ?? 1
      volumeGateMetric.value = data.volumeGateMetric ?? null
      volumeGateThreshold.value = data.volumeGateThreshold ?? 0
      return true
    } catch {
      return false
    }
  }

  function reset() {
    models.value = []
    compatibility.value = []
    selectedModelId.value = null
    params.value = {}
    smoothingWindow.value = 1
    transforms.value = []
    infill.value = 'none'
    scorerId.value = 'difference'
    showFitLine.value = true
    persistenceDamping.value = 0
    minAnomalyPoints.value = 1
    volumeGateMetric.value = null
    volumeGateThreshold.value = 0
    currentRunId.value = null
    results.value = null
    isRunning.value = false
    progress.value = 0
    error.value = null
  }

  return {
    models,
    compatibility,
    selectedModelId,
    params,
    detectorType,
    detectorThreshold,
    smoothingWindow,
    transforms,
    infill,
    scorerId,
    showFitLine,
    persistenceDamping,
    minAnomalyPoints,
    volumeGateMetric,
    volumeGateThreshold,
    selectedModel,
    thresholdScore,
    effectiveAnomalies,
    effectiveRegions,
    effectiveSummary,
    regionExplanations,
    currentRunId,
    results,
    isRunning,
    progress,
    progressStage,
    error,
    loadModels,
    loadCompatibility,
    selectModel,
    isCompatible,
    getIncompatibilityReason,
    runDetection,
    loadResults,
    setProgress,
    setComplete,
    persistSelection,
    restoreSelection,
    reset,
  }
})

function classifySeverity(score: number, threshold: number): 'low' | 'medium' | 'high' {
  if (score > threshold * 2.0) return 'high'
  if (score > threshold * 1.5) return 'medium'
  return 'low'
}

function buildRegion(points: DartsAnomalyPoint[], metric: string): AnomalyRegion {
  const scores = points.map((p) => p.score)
  const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length
  const sevOrder = { low: 0, medium: 1, high: 2 } as const
  const worstSev = points.reduce((worst, p) =>
    sevOrder[p.severity] > sevOrder[worst.severity] ? p : worst,
  ).severity
  return {
    start: points[0].timestamp,
    end: points[points.length - 1].timestamp,
    metric,
    severity: worstSev,
    avg_score: Math.round(avgScore * 10000) / 10000,
    point_count: points.length,
  }
}
