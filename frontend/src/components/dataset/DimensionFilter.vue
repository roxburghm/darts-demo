<script setup lang="ts">
import { ref, watch } from 'vue'
import type { DimensionValues } from '@/api/types'

const props = defineProps<{
  dimensionValues: DimensionValues[]
  selectedDimensions: string[]
  filters: Record<string, string[]>
}>()

const emit = defineEmits<{
  'update-filter': [column: string, values: string[]]
}>()

// Per-dimension mode: 'list' (checkboxes) or 'pattern' (glob input)
const filterMode = ref<Record<string, 'list' | 'pattern'>>({})
const patternText = ref<Record<string, string>>({})

function getMode(column: string): 'list' | 'pattern' {
  return filterMode.value[column] || 'list'
}

function setMode(column: string, mode: 'list' | 'pattern') {
  filterMode.value[column] = mode
  if (mode === 'list') {
    // Switching to list: clear pattern and reset filter
    patternText.value[column] = ''
    emit('update-filter', column, [])
  } else {
    // Switching to pattern: clear checkbox selections
    emit('update-filter', column, [])
  }
}

function globToRegex(pattern: string): RegExp {
  // Escape regex special chars except *, then convert * to .*
  const escaped = pattern.replace(/([.+?^${}()|[\]\\])/g, '\\$1')
  const regexStr = escaped.replace(/\*/g, '.*')
  return new RegExp(`^${regexStr}$`, 'i')
}

function applyPattern(column: string) {
  const raw = (patternText.value[column] || '').trim()
  if (!raw) {
    emit('update-filter', column, [])
    return
  }

  const dim = props.dimensionValues.find((d) => d.column === column)
  if (!dim) return

  // Support multiple patterns separated by commas
  const patterns = raw.split(',').map((p) => p.trim()).filter(Boolean)
  const regexes = patterns.map(globToRegex)

  const matched = dim.values.filter((v) => regexes.some((re) => re.test(v)))
  emit('update-filter', column, matched)
}

// Debounce pattern input
let patternTimers: Record<string, ReturnType<typeof setTimeout>> = {}
function onPatternInput(column: string) {
  if (patternTimers[column]) clearTimeout(patternTimers[column])
  patternTimers[column] = setTimeout(() => applyPattern(column), 400)
}

function toggleValue(column: string, value: string) {
  const current = props.filters[column] || []
  const idx = current.indexOf(value)
  if (idx >= 0) {
    emit('update-filter', column, current.filter((v) => v !== value))
  } else {
    emit('update-filter', column, [...current, value])
  }
}

function getRelevantDimensions() {
  return props.dimensionValues.filter((d) => props.selectedDimensions.includes(d.column))
}

function matchCount(column: string): number {
  return (props.filters[column] || []).length
}
</script>

<template>
  <div class="dimension-filter">
    <h3 class="label">Dimension Filters</h3>
    <p class="text-muted" style="font-size: 0.75rem; margin-bottom: 8px;">
      Leave empty to include all values
    </p>

    <div
      v-for="dim in getRelevantDimensions()"
      :key="dim.column"
      class="filter-group"
    >
      <div class="filter-header">
        <span class="filter-name">{{ dim.column }}</span>
        <div class="filter-header-right">
          <span v-if="getMode(dim.column) === 'pattern' && matchCount(dim.column) > 0" class="match-count">
            {{ matchCount(dim.column) }} matched
          </span>
          <span class="filter-count text-muted">{{ dim.count }} values</span>
          <div class="mode-toggle">
            <button
              class="mode-btn"
              :class="{ 'mode-btn--active': getMode(dim.column) === 'list' }"
              title="Checkbox list"
              @click="setMode(dim.column, 'list')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
              </svg>
            </button>
            <button
              class="mode-btn"
              :class="{ 'mode-btn--active': getMode(dim.column) === 'pattern' }"
              title="Wildcard pattern (e.g. acm*mmk)"
              @click="setMode(dim.column, 'pattern')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 16.8l-6.2 4.5 2.4-7.4L2 9.4h7.6z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Pattern mode -->
      <div v-if="getMode(dim.column) === 'pattern'" class="pattern-input-wrap">
        <input
          type="text"
          class="pattern-input"
          :value="patternText[dim.column] || ''"
          placeholder="e.g. acm*mmk, node02*"
          @input="(e) => { patternText[dim.column] = (e.target as HTMLInputElement).value; onPatternInput(dim.column) }"
        />
        <p class="pattern-hint text-muted">
          Use <code>*</code> as wildcard. Comma-separate multiple patterns.
        </p>
      </div>

      <!-- Checkbox list mode -->
      <div v-else class="filter-values">
        <label
          v-for="val in dim.values.slice(0, 20)"
          :key="val"
          class="filter-value"
          :class="{ 'filter-value--active': (filters[dim.column] || []).includes(val) }"
        >
          <input
            type="checkbox"
            :checked="(filters[dim.column] || []).includes(val)"
            @change="toggleValue(dim.column, val)"
          />
          <span>{{ val }}</span>
        </label>
        <p v-if="dim.values.length > 20" class="text-muted" style="font-size: 0.75rem;">
          +{{ dim.values.length - 20 }} more
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dimension-filter {
  display: flex;
  flex-direction: column;
}

.filter-group {
  margin-bottom: var(--space-md);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xs);
}

.filter-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.filter-name {
  font-size: 0.85rem;
  font-weight: 500;
}

.filter-count {
  font-size: 0.7rem;
}

.match-count {
  font-size: 0.7rem;
  color: var(--accent-primary);
  font-weight: 500;
}

.mode-toggle {
  display: flex;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.mode-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px 5px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mode-btn:first-child {
  border-right: 1px solid var(--border-primary);
}

.mode-btn:hover {
  color: var(--text-primary);
  background: var(--bg-elevated);
}

.mode-btn--active {
  color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.08);
}

.pattern-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pattern-input {
  width: 100%;
  padding: 6px 10px;
  font-size: 0.8rem;
  font-family: var(--font-mono, monospace);
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--transition-fast);
}

.pattern-input:focus {
  border-color: var(--accent-primary);
}

.pattern-input::placeholder {
  color: var(--text-muted);
}

.pattern-hint {
  font-size: 0.7rem;
  margin: 0;
}

.pattern-hint code {
  background: var(--bg-elevated);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.7rem;
}

.filter-values {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 160px;
  overflow-y: auto;
}

.filter-value {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 2px var(--space-xs);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.8rem;
  transition: background var(--transition-fast);
}

.filter-value:hover {
  background: var(--bg-elevated);
}

.filter-value--active {
  background: rgba(99, 102, 241, 0.08);
}

.filter-value input[type="checkbox"] {
  accent-color: var(--accent-primary);
  width: 13px;
  height: 13px;
}
</style>
