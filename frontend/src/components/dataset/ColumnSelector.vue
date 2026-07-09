<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ColumnInfo } from '@/api/types'

const props = defineProps<{
  title: string
  columns: ColumnInfo[]
  selected: string[]
}>()

const emit = defineEmits<{
  toggle: [name: string]
}>()

const search = ref('')

const filteredColumns = computed(() => {
  if (!search.value) return props.columns
  const q = search.value.toLowerCase()
  return props.columns.filter((c) => c.name.toLowerCase().includes(q))
})

function selectAll() {
  for (const col of filteredColumns.value) {
    if (!props.selected.includes(col.name)) {
      emit('toggle', col.name)
    }
  }
}

function clearAll() {
  for (const name of [...props.selected]) {
    emit('toggle', name)
  }
}
</script>

<template>
  <div class="column-selector">
    <div class="selector-header">
      <h3>{{ title }}</h3>
      <span class="badge">{{ selected.length }}/{{ columns.length }}</span>
    </div>

    <input
      v-if="columns.length > 8"
      v-model="search"
      type="text"
      placeholder="Search columns..."
      class="search-input"
    />

    <div class="selector-actions">
      <button class="btn btn-ghost btn-sm" @click="selectAll">Select All</button>
      <button class="btn btn-ghost btn-sm" @click="clearAll">Clear</button>
    </div>

    <div class="column-list">
      <label
        v-for="col in filteredColumns"
        :key="col.name"
        class="column-item"
        :class="{ 'column-item--selected': selected.includes(col.name) }"
      >
        <input
          type="checkbox"
          :checked="selected.includes(col.name)"
          @change="emit('toggle', col.name)"
        />
        <div class="column-info">
          <span class="column-name">{{ col.name }}</span>
          <span class="column-meta text-muted">
            {{ col.dtype }}
            <span v-if="col.null_pct > 0" class="null-badge">
              {{ (col.null_pct * 100).toFixed(0) }}% null
            </span>
          </span>
        </div>
      </label>
    </div>
  </div>
</template>

<style scoped>
.column-selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.selector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selector-header h3 {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}

.badge {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.12);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.search-input {
  font-size: 0.85rem;
  padding: var(--space-xs) var(--space-sm);
}

.selector-actions {
  display: flex;
  gap: var(--space-xs);
}

.btn-sm {
  font-size: 0.75rem;
  padding: 2px var(--space-sm);
}

.column-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 280px;
  overflow-y: auto;
}

.column-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.column-item:hover {
  background: var(--bg-elevated);
}

.column-item--selected {
  background: rgba(99, 102, 241, 0.08);
}

.column-item input[type="checkbox"] {
  accent-color: var(--accent-primary);
  width: 14px;
  height: 14px;
}

.column-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.column-name {
  font-size: 0.85rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.column-meta {
  font-size: 0.7rem;
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.null-badge {
  color: var(--color-warning);
  font-weight: 500;
}
</style>
