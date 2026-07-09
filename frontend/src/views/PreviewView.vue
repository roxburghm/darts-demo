<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/dataset'
import { getPreview } from '@/api/datasets'
import DataPreview from '@/components/dataset/DataPreview.vue'

const props = defineProps<{ sessionId: string }>()
const router = useRouter()
const dataset = useDatasetStore()

const preview = ref<{ columns: string[]; rows: Record<string, unknown>[]; total_rows: number } | null>(null)
const loading = ref(true)

onMounted(async () => {
  loading.value = true
  try {
    await dataset.loadMetadata(props.sessionId)
    preview.value = await getPreview(props.sessionId, 100)
  } finally {
    loading.value = false
  }
})

const nullPcts = computed<Record<string, number>>(() => {
  if (!dataset.metadata) return {}
  const map: Record<string, number> = {}
  for (const col of [...dataset.metadata.dimension_columns, ...dataset.metadata.metric_columns]) {
    map[col.name] = col.null_pct
  }
  return map
})

function proceed() {
  router.push({ name: 'configure', params: { sessionId: props.sessionId } })
}
</script>

<template>
  <div class="preview-view">
    <div v-if="loading" class="loading-state">
      <div class="spinner" />
      <p>Loading dataset...</p>
    </div>

    <template v-else-if="dataset.metadata">
      <div class="preview-header">
        <div class="dataset-summary">
          <h2>Data Preview</h2>
          <div class="summary-cards">
            <div class="summary-card">
              <span class="summary-label">File</span>
              <span class="summary-value">{{ dataset.metadata.filename }}</span>
            </div>
            <div class="summary-card">
              <span class="summary-label">Rows</span>
              <span class="summary-value">{{ dataset.metadata.row_count.toLocaleString() }}</span>
            </div>
            <div class="summary-card">
              <span class="summary-label">Metrics</span>
              <span class="summary-value">{{ dataset.metricColumns.length }}</span>
            </div>
            <div class="summary-card">
              <span class="summary-label">Dimensions</span>
              <span class="summary-value">{{ dataset.dimensionColumns.length }}</span>
            </div>
            <div class="summary-card">
              <span class="summary-label">Time Range</span>
              <span class="summary-value summary-value--small">
                {{ dataset.metadata.time_range[0] }} &mdash; {{ dataset.metadata.time_range[1] }}
              </span>
            </div>
          </div>
        </div>

        <button class="btn btn-primary" @click="proceed">
          Configure Columns
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>
      </div>

      <div class="preview-table">
        <DataPreview
          v-if="preview"
          :columns="preview.columns"
          :rows="preview.rows"
          :total-rows="preview.total_rows"
          :null-pcts="nullPcts"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.preview-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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

.preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-lg);
  flex-shrink: 0;
}

.dataset-summary h2 {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: var(--space-md);
}

.summary-cards {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.summary-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.summary-value {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.summary-value--small {
  font-size: 0.75rem;
  font-weight: 500;
}

.preview-table {
  flex: 1;
  overflow: auto;
  background: var(--bg-surface);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
}
</style>
