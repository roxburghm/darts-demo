<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ModelInfo, TransformId, InfillMethod, DartsAnomalyResult } from '@/api/types'

const INFILL_OPTIONS: { value: InfillMethod; label: string; description: string }[] = [
  { value: 'none', label: 'None', description: 'Leave missing values as-is' },
  { value: 'linear', label: 'Linear Interpolation', description: 'Straight line between known values' },
  { value: 'time', label: 'Time-Weighted', description: 'Interpolation weighted by time gaps' },
  { value: 'ffill', label: 'Forward Fill', description: 'Carry the last known value forward' },
  { value: 'zero', label: 'Fill with Zero', description: 'Replace missing values with 0' },
]

const SCORER_OPTIONS: { value: string; label: string; description: string }[] = [
  { value: 'difference', label: 'Absolute Difference', description: 'Simple |actual − predicted| residuals (default)' },
  { value: 'norm', label: 'Lp Norm', description: 'Lp norm of residuals over sliding windows' },
  { value: 'kmeans', label: 'KMeans', description: 'Clusters residual windows — anomalous patterns far from cluster centers' },
  { value: 'wasserstein', label: 'Wasserstein', description: 'Earth mover\'s distance on residual distribution windows' },
  { value: 'pyod_iforest', label: 'Isolation Forest', description: 'Isolation Forest on residual windows — detects unusual residual patterns' },
  { value: 'pyod_lof', label: 'Local Outlier Factor', description: 'Density-based residual scoring — flags locally sparse residual regions' },
  { value: 'pyod_copod', label: 'COPOD (Copula)', description: 'Copula-based outlier detection on residual windows' },
  { value: 'pyod_knn', label: 'KNN', description: 'K-nearest neighbor distance on residual windows' },
]

const AVAILABLE_TRANSFORMS: { id: TransformId; label: string; description: string }[] = [
  { id: 'winsorize', label: 'Clip Outliers', description: 'Clips extreme values to the 1st/99th percentile — tames spikes for better chart readability' },
  { id: 'log', label: 'Log (log1p)', description: 'Logarithmic transform — stabilizes variance for exponential/multiplicative data' },
  { id: 'boxcox', label: 'Box-Cox', description: 'Power transform — automatically finds the best power to normalize distribution' },
  { id: 'diff', label: 'Differencing', description: 'First-order differencing — removes trends, makes data stationary' },
  { id: 'scale_standard', label: 'Z-Score', description: 'Standard scaling — centers at 0 with unit variance' },
  { id: 'scale_minmax', label: 'Min-Max [0,1]', description: 'Min-max scaling — normalizes values to the [0, 1] range' },
]

const props = defineProps<{
  model: ModelInfo
  params: Record<string, number | boolean | string>
  detectorType: 'quantile' | 'threshold' | 'iqr'
  detectorThreshold: number
  smoothingWindow: number
  transforms: TransformId[]
  infill: InfillMethod
  scorerId: string
  results: DartsAnomalyResult | null
  isRunning: boolean
  persistenceDamping: number
  minAnomalyPoints: number
  volumeGateMetric: string | null
  volumeGateThreshold: number
  availableMetrics: string[]
}>()

const scoreStats = computed(() => {
  if (!props.results || props.results.scores.length === 0) return null
  const vals = props.results.scores.map((s) => s.score).filter((v) => v > 0).sort((a, b) => a - b)
  if (vals.length === 0) return null
  const pct = (p: number) => vals[Math.min(Math.floor(p * vals.length), vals.length - 1)]
  return {
    min: vals[0],
    p50: pct(0.5),
    p90: pct(0.9),
    p95: pct(0.95),
    p99: pct(0.99),
    max: vals[vals.length - 1],
  }
})

const emit = defineEmits<{
  'update:params': [value: Record<string, number | boolean | string>]
  'update:detectorType': [value: 'quantile' | 'threshold' | 'iqr']
  'update:detectorThreshold': [value: number]
  'update:smoothingWindow': [value: number]
  'update:transforms': [value: TransformId[]]
  'update:infill': [value: InfillMethod]
  'update:scorer-id': [value: string]
  'update:persistence-damping': [value: number]
  'update:min-anomaly-points': [value: number]
  'update:volume-gate-metric': [value: string | null]
  'update:volume-gate-threshold': [value: number]
  run: []
  'reset-defaults': []
}>()

function updateParam(name: string, value: number | boolean | string) {
  emit('update:params', { ...props.params, [name]: value })
}

function handleNumberInput(name: string, event: Event) {
  const target = event.target as HTMLInputElement
  updateParam(name, Number(target.value))
}

function resetDefaults() {
  const defaults: Record<string, number | boolean | string> = {}
  for (const param of props.model.params) {
    defaults[param.name] = param.default
  }
  emit('update:params', defaults)
}

function toggleTransform(id: TransformId) {
  const current = [...props.transforms]
  const idx = current.indexOf(id)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(id)
  }
  emit('update:transforms', current)
}

const accordion = ref<Record<string, boolean>>({
  preprocessing: false,
  transforms: false,
  filtering: false,
})

function toggleAccordion(key: string) {
  accordion.value[key] = !accordion.value[key]
}
</script>

<template>
  <div class="param-panel">
    <div class="panel-header">
      <h3>{{ model.name }}</h3>
      <span class="badge">{{ model.category === 'scorer' ? 'Scorer' : 'Forecast' }}</span>
    </div>

    <div class="panel-section">
      <h4>Model Parameters</h4>
      <div v-for="param in model.params" :key="param.name" class="param-field">
        <label :for="'param-' + param.name" class="param-label">
          {{ param.label }}
          <span v-if="param.description" class="param-hint" :title="param.description">?</span>
        </label>

        <select
          v-if="param.type === 'select'"
          :id="'param-' + param.name"
          class="param-input"
          :value="params[param.name]"
          @change="updateParam(param.name, ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
        </select>

        <input
          v-else-if="param.type === 'bool'"
          :id="'param-' + param.name"
          type="checkbox"
          class="param-checkbox"
          :checked="Boolean(params[param.name])"
          @change="updateParam(param.name, ($event.target as HTMLInputElement).checked)"
        />

        <input
          v-else
          :id="'param-' + param.name"
          type="number"
          class="param-input"
          :value="params[param.name]"
          :min="param.min"
          :max="param.max"
          :step="param.step"
          @input="handleNumberInput(param.name, $event)"
        />
      </div>

      <button class="btn btn-ghost btn-sm" @click="resetDefaults">Reset Defaults</button>
    </div>

    <div class="panel-section">
      <h4>Detection Threshold</h4>
      <div class="param-field">
        <label class="param-label">Method</label>
        <select
          class="param-input"
          :value="detectorType"
          @change="emit('update:detectorType', ($event.target as HTMLSelectElement).value as any)"
        >
          <option value="quantile">Quantile (top %)</option>
          <option value="threshold">Fixed Score Threshold</option>
          <option value="iqr">IQR (Interquartile Range)</option>
        </select>
      </div>

      <!-- Quantile mode: simple slider 0.5–0.999 -->
      <div v-if="detectorType === 'quantile'" class="param-field">
        <label class="param-label">
          Quantile
          <span class="param-value">{{ detectorThreshold.toFixed(3) }}</span>
          <span class="param-hint" title="Flag the top (1 - q)% of scores as anomalous. E.g. 0.95 = top 5%.">?</span>
        </label>
        <input
          type="range"
          class="param-slider"
          :value="detectorThreshold"
          min="0.5"
          max="0.999"
          step="0.005"
          @input="emit('update:detectorThreshold', Number(($event.target as HTMLInputElement).value))"
        />
      </div>

      <!-- IQR mode: scale multiplier slider -->
      <div v-else-if="detectorType === 'iqr'" class="param-field">
        <label class="param-label">
          IQR Scale
          <span class="param-value">{{ detectorThreshold.toFixed(2) }}</span>
          <span class="param-hint" title="Multiplier for IQR range. Points outside Q1 - scale×IQR or above Q3 + scale×IQR are flagged. Default 1.5 = mild outliers, 3.0 = extreme outliers.">?</span>
        </label>
        <input
          type="range"
          class="param-slider"
          :value="detectorThreshold"
          min="0.5"
          max="5"
          step="0.1"
          @input="emit('update:detectorThreshold', Number(($event.target as HTMLInputElement).value))"
        />
      </div>

      <!-- Fixed threshold mode: number input + score stats from last run -->
      <div v-else class="param-field">
        <label class="param-label">
          Score Threshold
          <span class="param-hint" title="Points with anomaly score above this value are flagged. Run detection first to see score distribution.">?</span>
        </label>
        <input
          type="number"
          class="param-input"
          :value="detectorThreshold"
          min="0"
          step="0.1"
          @input="emit('update:detectorThreshold', Number(($event.target as HTMLInputElement).value))"
        />
        <div v-if="scoreStats" class="score-stats">
          <span class="score-stats-label">Last run scores:</span>
          <div class="score-presets">
            <button
              v-for="(val, key) in { p50: scoreStats.p50, p90: scoreStats.p90, p95: scoreStats.p95, p99: scoreStats.p99, max: scoreStats.max }"
              :key="key"
              class="score-preset-btn"
              :class="{ active: Math.abs(detectorThreshold - val) < 0.001 }"
              :title="`Set threshold to ${key}: ${val.toFixed(4)}`"
              @click="emit('update:detectorThreshold', Math.round(val * 10000) / 10000)"
            >
              {{ key }}
              <small>{{ val < 100 ? val.toFixed(2) : val.toFixed(0) }}</small>
            </button>
          </div>
        </div>
        <p v-else class="score-stats-hint">Run detection to see score distribution</p>
      </div>
    </div>

    <div v-if="model.category === 'forecast'" class="panel-section">
      <h4>Residual Scoring</h4>
      <div class="param-field">
        <label class="param-label">
          Scorer
          <span class="param-hint" title="How forecast residuals are scored. 'Absolute Difference' is the simplest; others use sliding-window analysis for richer anomaly patterns.">?</span>
        </label>
        <select
          class="param-input"
          :value="scorerId"
          @change="emit('update:scorer-id', ($event.target as HTMLSelectElement).value)"
        >
          <option
            v-for="opt in SCORER_OPTIONS"
            :key="opt.value"
            :value="opt.value"
            :title="opt.description"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
      <div v-if="scorerId !== 'difference'" class="param-field">
        <label class="param-label">
          Scorer Window
          <span class="param-value">{{ params.scorer_window ?? 10 }}</span>
          <span class="param-hint" title="Sliding window size for the residual scorer. Larger windows capture longer-term patterns.">?</span>
        </label>
        <input
          type="range"
          class="param-slider"
          :value="params.scorer_window ?? 10"
          min="3"
          max="100"
          step="1"
          @input="updateParam('scorer_window', Number(($event.target as HTMLInputElement).value))"
        />
      </div>
    </div>

    <div class="panel-section accordion" :class="{ 'accordion--open': accordion.preprocessing }">
      <h4 class="accordion-header" @click="toggleAccordion('preprocessing')">
        <svg class="accordion-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
        Pre-processing
        <span v-if="infill !== 'none' || smoothingWindow > 1" class="accordion-badge">Active</span>
      </h4>
      <div v-show="accordion.preprocessing" class="accordion-body">
        <div class="param-field">
          <label class="param-label">
            Data Infill
            <span class="param-hint" title="How to fill missing (NaN) values in the time series before analysis.">?</span>
          </label>
          <select
            class="param-input"
            :value="infill"
            @change="emit('update:infill', ($event.target as HTMLSelectElement).value as InfillMethod)"
          >
            <option
              v-for="opt in INFILL_OPTIONS"
              :key="opt.value"
              :value="opt.value"
              :title="opt.description"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>
        <div class="param-field">
          <label class="param-label">
            Smoothing Window
            <span class="param-value">{{ smoothingWindow === 1 ? 'Off' : smoothingWindow + ' pts' }}</span>
            <span class="param-hint" title="Rolling mean applied before detection. Higher values reduce noise but may hide short anomalies.">?</span>
          </label>
          <input
            type="range"
            class="param-slider"
            :value="smoothingWindow"
            min="1"
            max="60"
            step="1"
            @input="emit('update:smoothingWindow', Number(($event.target as HTMLInputElement).value))"
          />
        </div>
      </div>
    </div>

    <div class="panel-section accordion" :class="{ 'accordion--open': accordion.transforms }">
      <h4 class="accordion-header" @click="toggleAccordion('transforms')">
        <svg class="accordion-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
        Data Transforms
        <span v-if="transforms.length > 0" class="accordion-badge">{{ transforms.length }}</span>
      </h4>
      <div v-show="accordion.transforms" class="accordion-body">
        <div v-for="t in AVAILABLE_TRANSFORMS" :key="t.id" class="transform-item">
          <label class="transform-label">
            <input
              type="checkbox"
              class="param-checkbox"
              :checked="transforms.includes(t.id)"
              @change="toggleTransform(t.id)"
            />
            <span class="transform-name">{{ t.label }}</span>
            <span class="param-hint" :title="t.description">?</span>
          </label>
        </div>
        <p v-if="transforms.length > 0" class="transform-order">
          Applied in order: {{ transforms.join(' → ') }}
        </p>
      </div>
    </div>

    <div class="panel-section accordion" :class="{ 'accordion--open': accordion.filtering }">
      <h4 class="accordion-header" @click="toggleAccordion('filtering')">
        <svg class="accordion-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
        Anomaly Filtering
        <span v-if="persistenceDamping > 0 || minAnomalyPoints > 1 || volumeGateMetric" class="accordion-badge">Active</span>
      </h4>
      <div v-show="accordion.filtering" class="accordion-body">
        <div class="param-field">
          <label class="param-label">
            Persistence Damping
            <span class="param-value">{{ persistenceDamping === 0 ? 'Off' : persistenceDamping.toFixed(1) }}</span>
            <span class="param-hint" title="Boost severity of long-duration anomaly regions using log2(point_count) scaling. Short transient anomalies are de-emphasized, while persistent anomalies are highlighted.">?</span>
          </label>
          <input
            type="range"
            class="param-slider"
            :value="persistenceDamping"
            min="0"
            max="1"
            step="0.1"
            @input="emit('update:persistence-damping', Number(($event.target as HTMLInputElement).value))"
          />
        </div>
        <div class="param-field">
          <label class="param-label">
            Min Region Points
            <span class="param-value">{{ minAnomalyPoints }}</span>
            <span class="param-hint" title="Filter out anomaly regions with fewer than this many consecutive points. Use to suppress single-point noise.">?</span>
          </label>
          <input
            type="range"
            class="param-slider"
            :value="minAnomalyPoints"
            min="1"
            max="10"
            step="1"
            @input="emit('update:min-anomaly-points', Number(($event.target as HTMLInputElement).value))"
          />
        </div>
        <div class="param-field">
          <label class="param-label">
            Volume Gate
            <span class="param-hint" title="Suppress anomalies when a reference metric (e.g. attempts) is below a minimum threshold. Prevents false positives during low-traffic periods. Requires re-running detection.">?</span>
          </label>
          <select
            class="param-input"
            :value="volumeGateMetric ?? ''"
            @change="emit('update:volume-gate-metric', ($event.target as HTMLSelectElement).value || null)"
          >
            <option value="">None (disabled)</option>
            <option v-for="m in availableMetrics" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <div v-if="volumeGateMetric" class="param-field">
          <label class="param-label">
            Min Volume
            <span class="param-hint" title="Anomalies are suppressed when the reference metric is below this value. Uses original (untransformed) data values.">?</span>
          </label>
          <input
            type="number"
            class="param-input"
            :value="volumeGateThreshold"
            min="0"
            step="1"
            @input="emit('update:volume-gate-threshold', Number(($event.target as HTMLInputElement).value))"
          />
        </div>
      </div>
    </div>

    <button
      class="btn btn-primary run-btn"
      :disabled="isRunning"
      @click="emit('run')"
    >
      <template v-if="isRunning">
        <div class="spinner-sm" />
        Running...
      </template>
      <template v-else>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Run Detection
      </template>
    </button>
  </div>
</template>

<style scoped>
.param-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.panel-header h3 {
  font-size: 1rem;
  font-weight: 700;
}

.badge {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-primary);
}

.panel-section h4 {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-sm);
}

.panel-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.accordion-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  margin-bottom: 0;
}

.accordion-header:hover {
  color: var(--text-secondary);
}

.accordion-chevron {
  transition: transform var(--transition-fast);
  flex-shrink: 0;
}

.accordion--open > .accordion-header > .accordion-chevron {
  transform: rotate(90deg);
}

.accordion-badge {
  margin-left: auto;
  font-size: 0.6rem;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-primary);
  text-transform: none;
  letter-spacing: 0;
}

.accordion-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding-top: var(--space-sm);
}

.param-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.param-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--bg-elevated);
  font-size: 0.6rem;
  color: var(--text-muted);
  cursor: help;
}

.param-value {
  margin-left: auto;
  font-weight: 600;
  color: var(--accent-primary);
}

.param-input {
  width: 100%;
  padding: 6px 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.param-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.param-slider {
  width: 100%;
  accent-color: var(--accent-primary);
}

.param-checkbox {
  accent-color: var(--accent-primary);
  width: 16px;
  height: 16px;
}

.transform-item {
  padding: 2px 0;
}

.transform-label {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.transform-name {
  font-weight: 500;
}

.transform-order {
  font-size: 0.7rem;
  color: var(--accent-primary);
  margin-top: var(--space-xs);
}

.score-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

.score-stats-label {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.score-presets {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.score-preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3px 8px;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: 1.2;
}

.score-preset-btn small {
  font-weight: 400;
  color: var(--text-muted);
  font-size: 0.6rem;
}

.score-preset-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.score-preset-btn.active {
  border-color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.12);
  color: var(--accent-primary);
}

.score-stats-hint {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-style: italic;
  margin-top: 2px;
}

.btn-sm {
  font-size: 0.75rem;
  padding: 4px 8px;
  align-self: flex-start;
}

.run-btn {
  width: 100%;
  padding: var(--space-md);
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
