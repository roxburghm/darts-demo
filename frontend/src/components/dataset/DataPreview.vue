<script setup lang="ts">
defineProps<{
  columns: string[]
  rows: Record<string, unknown>[]
  totalRows: number
  nullPcts?: Record<string, number>
}>()
</script>

<template>
  <div class="data-preview">
    <div class="preview-header">
      <h3>Data Preview</h3>
      <span class="text-secondary">
        Showing {{ rows.length }} of {{ totalRows.toLocaleString() }} rows
      </span>
    </div>

    <div class="table-wrapper">
      <table class="preview-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
          <tr v-if="nullPcts" class="null-pct-row">
            <th v-for="col in columns" :key="col" class="null-pct-cell">
              <span :class="{
                'null-pct-all': (nullPcts[col] ?? 0) >= 1,
                'null-pct-none': (nullPcts[col] ?? 0) === 0,
                'null-pct-mixed': (nullPcts[col] ?? 0) > 0 && (nullPcts[col] ?? 0) < 1,
              }">
                {{ ((nullPcts[col] ?? 0) * 100).toFixed(1) }}% null
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="idx">
            <td v-for="col in columns" :key="col" :title="String(row[col] ?? '')">
              <span v-if="row[col] === null || row[col] === undefined" class="null-value">null</span>
              <span v-else>{{ row[col] }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.data-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-header h3 {
  font-size: 1rem;
  font-weight: 600;
}

.table-wrapper {
  overflow: auto;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  max-height: calc(100vh - 200px);
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  font-family: var(--font-mono);
}

.preview-table th {
  position: sticky;
  top: 0;
  background: var(--bg-elevated);
  padding: var(--space-sm) var(--space-md);
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
  border-bottom: 2px solid var(--border-primary);
  color: var(--text-secondary);
  font-size: 0.75rem;
  z-index: 1;
}

.null-pct-row th {
  position: sticky;
  top: 33px;
  z-index: 1;
}

.null-pct-cell {
  padding: 2px var(--space-md) !important;
  font-size: 0.65rem !important;
  font-weight: 400 !important;
  text-transform: none !important;
  letter-spacing: normal !important;
  color: var(--text-muted) !important;
  border-bottom: 1px solid var(--border-primary) !important;
}

.null-pct-all {
  color: #ef4444 !important;
}

.null-pct-mixed {
  color: #f97316 !important;
}

.null-pct-none {
  color: var(--color-success) !important;
}

.preview-table td {
  padding: var(--space-xs) var(--space-md);
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-table tbody tr:hover {
  background: var(--bg-elevated);
}

.null-value {
  color: var(--text-muted);
  font-style: italic;
}
</style>
