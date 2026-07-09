<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/dataset'
import { useModelsStore } from '@/stores/models'
import ModelCard from '@/components/models/ModelCard.vue'
import type { ModelInfo } from '@/api/types'

const props = defineProps<{ sessionId: string }>()
const router = useRouter()
const dataset = useDatasetStore()
const models = useModelsStore()

const loading = ref(true)

const searchQuery = ref('')
const filterGpu = ref(false)
const filterFoundation = ref(false)
const filterCompatible = ref(false)
const condensed = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    if (!dataset.metadata || dataset.metadata.session_id !== props.sessionId) {
      await dataset.loadMetadata(props.sessionId)
    }
    dataset.restoreSelections(props.sessionId)
    await models.loadModels()
    await models.loadCompatibility(props.sessionId)
    models.restoreSelection(props.sessionId)
  } finally {
    loading.value = false
  }
})

const REGRESSION_MODELS = new Set(['linear_regression', 'random_forest', 'lightgbm', 'xgboost'])
const DL_MODELS = new Set(['nbeats', 'nhits', 'tft', 'dlinear', 'nlinear', 'tcn', 'transformer', 'block_rnn', 'tide', 'tsmixer'])

const filteredModels = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  return models.models.filter((m: ModelInfo) => {
    if (q && !m.name.toLowerCase().includes(q) && !m.description.toLowerCase().includes(q))
      return false
    if (filterGpu.value && !m.gpu_accelerated) return false
    if (filterFoundation.value && !m.foundation) return false
    if (filterCompatible.value && !models.isCompatible(m.id)) return false
    return true
  })
})

const totalCount = computed(() => models.models.length)
const filteredCount = computed(() => filteredModels.value.length)
const hasActiveFilters = computed(() =>
  searchQuery.value.trim() !== '' || filterGpu.value || filterFoundation.value || filterCompatible.value,
)

const scorerModels = computed(() =>
  filteredModels.value.filter(
    (m) => m.category === 'scorer' && !m.requires_dimensions && !m.foundation,
  ),
)
const peerModels = computed(() =>
  filteredModels.value.filter((m) => m.requires_dimensions),
)
const forecastModels = computed(() =>
  filteredModels.value.filter(
    (m) => m.category === 'forecast' && !REGRESSION_MODELS.has(m.id)
        && !DL_MODELS.has(m.id) && !m.foundation,
  ),
)
const regressionModels = computed(() =>
  filteredModels.value.filter(
    (m) => m.category === 'forecast' && REGRESSION_MODELS.has(m.id),
  ),
)
const dlModels = computed(() =>
  filteredModels.value.filter(
    (m) => m.category === 'forecast' && DL_MODELS.has(m.id),
  ),
)
const foundationModels = computed(() =>
  filteredModels.value.filter((m) => m.foundation),
)

const canProceed = computed(
  () => models.selectedModelId !== null && models.isCompatible(models.selectedModelId),
)

function handleSelect(modelId: string) {
  models.selectModel(modelId)
}

function proceed() {
  models.persistSelection(props.sessionId)
  dataset.persistSelections(props.sessionId)
  router.push({ name: 'analysis', params: { sessionId: props.sessionId } })
}

function goBack() {
  router.push({ name: 'configure', params: { sessionId: props.sessionId } })
}
</script>

<template>
  <div class="model-select-view">
    <div v-if="loading" class="loading-state">
      <div class="spinner" />
      <p>Loading models...</p>
    </div>

    <template v-else>
      <div class="model-select-header">
        <button class="btn btn-ghost" @click="goBack">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
          </svg>
          Back
        </button>
        <div>
          <h2>Select Detection Model</h2>
          <p class="text-secondary">
            {{ dataset.selectedMetrics.length }} metric{{ dataset.selectedMetrics.length !== 1 ? 's' : '' }} selected
            <span v-if="dataset.selectedDimensions.length > 0">
              &middot; {{ dataset.selectedDimensions.length }} dimension{{ dataset.selectedDimensions.length !== 1 ? 's' : '' }}
            </span>
          </p>
        </div>
      </div>

      <div class="filter-bar">
        <div class="filter-search">
          <svg class="filter-search__icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            class="filter-search__input"
            placeholder="Search models..."
          />
        </div>
        <div class="filter-chips">
          <button
            class="filter-chip"
            :class="{ 'filter-chip--active': filterGpu }"
            @click="filterGpu = !filterGpu"
          >GPU</button>
          <button
            class="filter-chip"
            :class="{ 'filter-chip--active': filterFoundation }"
            @click="filterFoundation = !filterFoundation"
          >Foundation</button>
          <button
            class="filter-chip"
            :class="{ 'filter-chip--active': filterCompatible }"
            @click="filterCompatible = !filterCompatible"
          >Compatible</button>
        </div>
        <span v-if="hasActiveFilters" class="filter-count">{{ filteredCount }} / {{ totalCount }}</span>
        <button
          class="view-toggle"
          :title="condensed ? 'Card view' : 'Compact view'"
          @click="condensed = !condensed"
        >
          <!-- Grid icon -->
          <svg v-if="condensed" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
          </svg>
          <!-- List icon -->
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
            <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
          </svg>
        </button>
      </div>

      <div class="model-sections">
        <section v-if="scorerModels.length > 0">
          <h3 class="section-title">Standalone Scorers</h3>
          <p v-if="!condensed" class="section-desc">Detect anomalies directly from the data without forecasting.</p>
          <div class="model-grid" :class="{ 'model-grid--condensed': condensed }">
            <ModelCard
              v-for="model in scorerModels"
              :key="model.id"
              :model="model"
              :compatible="models.isCompatible(model.id)"
              :reason="models.getIncompatibilityReason(model.id)"
              :selected="models.selectedModelId === model.id"
              :condensed="condensed"
              @select="handleSelect(model.id)"
              @proceed="proceed"
            />
          </div>
        </section>

        <section v-if="peerModels.length > 0">
          <h3 class="section-title">Peer / Cohort Analysis</h3>
          <p v-if="!condensed" class="section-desc">Compare groups (e.g. network nodes) against the collective norm and flag divergent ones.</p>
          <div class="model-grid" :class="{ 'model-grid--condensed': condensed }">
            <ModelCard
              v-for="model in peerModels"
              :key="model.id"
              :model="model"
              :compatible="models.isCompatible(model.id)"
              :reason="models.getIncompatibilityReason(model.id)"
              :selected="models.selectedModelId === model.id"
              :condensed="condensed"
              @select="handleSelect(model.id)"
              @proceed="proceed"
            />
          </div>
        </section>

        <section v-if="forecastModels.length > 0">
          <h3 class="section-title">Forecast-Based</h3>
          <p v-if="!condensed" class="section-desc">Build a forecast model and detect where actuals deviate from predictions.</p>
          <div class="model-grid" :class="{ 'model-grid--condensed': condensed }">
            <ModelCard
              v-for="model in forecastModels"
              :key="model.id"
              :model="model"
              :compatible="models.isCompatible(model.id)"
              :reason="models.getIncompatibilityReason(model.id)"
              :selected="models.selectedModelId === model.id"
              :condensed="condensed"
              @select="handleSelect(model.id)"
              @proceed="proceed"
            />
          </div>
        </section>

        <section v-if="regressionModels.length > 0">
          <h3 class="section-title">Regression / ML</h3>
          <p v-if="!condensed" class="section-desc">Machine learning models using lagged features. Support multivariate data and learn cross-metric patterns.</p>
          <div class="model-grid" :class="{ 'model-grid--condensed': condensed }">
            <ModelCard
              v-for="model in regressionModels"
              :key="model.id"
              :model="model"
              :compatible="models.isCompatible(model.id)"
              :reason="models.getIncompatibilityReason(model.id)"
              :selected="models.selectedModelId === model.id"
              :condensed="condensed"
              @select="handleSelect(model.id)"
              @proceed="proceed"
            />
          </div>
        </section>

        <section v-if="dlModels.length > 0">
          <h3 class="section-title">Deep Learning</h3>
          <p v-if="!condensed" class="section-desc">Neural network models powered by PyTorch. Capture complex non-linear patterns but require more training time.</p>
          <div class="model-grid" :class="{ 'model-grid--condensed': condensed }">
            <ModelCard
              v-for="model in dlModels"
              :key="model.id"
              :model="model"
              :compatible="models.isCompatible(model.id)"
              :reason="models.getIncompatibilityReason(model.id)"
              :selected="models.selectedModelId === model.id"
              :condensed="condensed"
              @select="handleSelect(model.id)"
              @proceed="proceed"
            />
          </div>
        </section>

        <section v-if="foundationModels.length > 0">
          <h3 class="section-title">Foundation Models</h3>
          <p v-if="!condensed" class="section-desc">Pre-trained on massive datasets. Zero-shot anomaly detection with no training required. First run downloads weights from HuggingFace Hub.</p>
          <div class="model-grid" :class="{ 'model-grid--condensed': condensed }">
            <ModelCard
              v-for="model in foundationModels"
              :key="model.id"
              :model="model"
              :compatible="models.isCompatible(model.id)"
              :reason="models.getIncompatibilityReason(model.id)"
              :selected="models.selectedModelId === model.id"
              :condensed="condensed"
              @select="handleSelect(model.id)"
              @proceed="proceed"
            />
          </div>
        </section>

        <div v-if="filteredCount === 0 && hasActiveFilters" class="no-results">
          No models match your filters.
          <button class="btn btn-ghost btn-sm" @click="searchQuery = ''; filterGpu = false; filterFoundation = false; filterCompatible = false">
            Clear filters
          </button>
        </div>
      </div>

      <div class="model-select-footer">
        <div v-if="models.selectedModel" class="selected-summary">
          Selected: <strong>{{ models.selectedModel.name }}</strong>
        </div>
        <div v-else class="text-muted">Choose a model to continue</div>
        <button class="btn btn-primary" :disabled="!canProceed" @click="proceed">
          Run Analysis
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.model-select-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--space-lg);
  gap: var(--space-lg);
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

.model-select-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
}

.model-select-header h2 {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 2px;
}

.model-sections {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  flex: 1;
}

.section-title {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.section-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: var(--space-md);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.filter-search {
  position: relative;
  flex: 1;
  min-width: 180px;
  max-width: 300px;
}

.filter-search__icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.filter-search__input {
  width: 100%;
  padding: 6px 10px 6px 30px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.filter-search__input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.filter-search__input::placeholder {
  color: var(--text-muted);
}

.filter-chips {
  display: flex;
  gap: 4px;
}

.filter-chip {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.filter-chip:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.filter-chip--active {
  background: rgba(99, 102, 241, 0.15);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.filter-count {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.view-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-primary);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.view-toggle:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-md);
}

.model-grid--condensed {
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 4px;
}

.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xl);
  color: var(--text-muted);
  font-size: 0.9rem;
}

.model-select-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) 0;
  border-top: 1px solid var(--border-primary);
}

.selected-summary {
  font-size: 0.9rem;
  color: var(--text-primary);
}
</style>
