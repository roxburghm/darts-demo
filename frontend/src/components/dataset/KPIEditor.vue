<script setup lang="ts">
import { ref, nextTick } from 'vue'
import type { KPIDefinition } from '@/api/types'
import { validateKPIFormula } from '@/api/datasets'

const props = defineProps<{
  kpis: KPIDefinition[]
  selectedMetrics: string[]
  availableColumns: string[]
  sessionId: string
}>()

const emit = defineEmits<{
  add: [kpi: KPIDefinition]
  remove: [name: string]
  toggle: [name: string]
  save: []
}>()

const showForm = ref(false)
const newName = ref('')
const newFormula = ref('')
const error = ref('')
const validating = ref(false)

// Edit mode: tracks the original name of the KPI being edited
const editingName = ref<string | null>(null)

// Autocomplete state
const formulaInput = ref<HTMLTextAreaElement | null>(null)
const suggestions = ref<string[]>([])
const showSuggestions = ref(false)
const highlightIndex = ref(-1)
let blurTimeout: ReturnType<typeof setTimeout> | null = null

function getTokenAtCursor(): { token: string; start: number; end: number } | null {
  const el = formulaInput.value
  if (!el) return null
  const pos = el.selectionStart ?? newFormula.value.length
  const text = newFormula.value

  // Walk backwards from cursor to find token start (alphanumeric, dots, underscores, backticks)
  let start = pos
  while (start > 0 && /[A-Za-z0-9_.]/.test(text[start - 1])) {
    start--
  }
  // Include leading backtick if present
  if (start > 0 && text[start - 1] === '`') {
    start--
  }
  // Walk forwards from cursor to find token end
  let end = pos
  while (end < text.length && /[A-Za-z0-9_.]/.test(text[end])) {
    end++
  }
  // Include trailing backtick if present
  if (end < text.length && text[end] === '`') {
    end++
  }

  const token = text.slice(start, end).replace(/`/g, '')
  if (!token) return null
  return { token, start, end }
}

function updateSuggestions() {
  const result = getTokenAtCursor()
  if (!result || result.token.length < 1) {
    suggestions.value = []
    showSuggestions.value = false
    return
  }

  const query = result.token.toLowerCase()
  const filtered = props.availableColumns.filter((col) =>
    col.toLowerCase().includes(query),
  )

  suggestions.value = filtered.slice(0, 50)
  highlightIndex.value = filtered.length > 0 ? 0 : -1
  showSuggestions.value = filtered.length > 0
}

function onFormulaInput() {
  updateSuggestions()
}

function onFormulaFocus() {
  if (blurTimeout) {
    clearTimeout(blurTimeout)
    blurTimeout = null
  }
  updateSuggestions()
}

function onFormulaBlur() {
  blurTimeout = setTimeout(() => {
    showSuggestions.value = false
  }, 200)
}

function applySuggestion(col: string) {
  const result = getTokenAtCursor()
  const text = newFormula.value
  const backticked = `\`${col}\``

  if (result) {
    newFormula.value = text.slice(0, result.start) + backticked + text.slice(result.end)
  } else {
    newFormula.value += backticked
  }

  showSuggestions.value = false
  highlightIndex.value = -1

  nextTick(() => {
    formulaInput.value?.focus()
  })
}

function onFormulaKeydown(e: KeyboardEvent) {
  if (!showSuggestions.value || suggestions.value.length === 0) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    highlightIndex.value = Math.min(highlightIndex.value + 1, suggestions.value.length - 1)
    scrollToHighlighted()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    highlightIndex.value = Math.max(highlightIndex.value - 1, 0)
    scrollToHighlighted()
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    if (highlightIndex.value >= 0 && highlightIndex.value < suggestions.value.length) {
      e.preventDefault()
      applySuggestion(suggestions.value[highlightIndex.value])
    }
  } else if (e.key === 'Escape') {
    showSuggestions.value = false
    highlightIndex.value = -1
  }
}

function scrollToHighlighted() {
  nextTick(() => {
    const container = document.querySelector('.suggestions-dropdown')
    const active = container?.querySelector('.suggestion-item.active')
    if (active && container) {
      active.scrollIntoView({ block: 'nearest' })
    }
  })
}

function startEdit(kpi: KPIDefinition) {
  editingName.value = kpi.name
  newName.value = kpi.name
  newFormula.value = kpi.formula
  error.value = ''
  showForm.value = true
}

async function submitKPI() {
  error.value = ''

  const name = newName.value.trim()
  const formula = newFormula.value.trim()

  if (!name) {
    error.value = 'Name is required'
    return
  }
  if (!formula) {
    error.value = 'Formula is required'
    return
  }
  // Name uniqueness: skip the KPI being edited
  if (props.kpis.some((k) => k.name === name && k.name !== editingName.value)) {
    error.value = 'A KPI with this name already exists'
    return
  }
  if (props.availableColumns.includes(name)) {
    error.value = 'Name conflicts with an existing column'
    return
  }

  // Validate formula against real data
  validating.value = true
  try {
    const err = await validateKPIFormula(props.sessionId, formula)
    if (err) {
      error.value = err
      return
    }
  } catch (e: any) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : 'Failed to validate formula'
    return
  } finally {
    validating.value = false
  }

  // If editing, remove the old KPI first
  if (editingName.value) {
    emit('remove', editingName.value)
  }

  emit('add', { name, formula, description: '' })
  // Auto-save after add/edit so backend stays in sync
  nextTick(() => emit('save'))

  resetForm()
}

function resetForm() {
  showForm.value = false
  newName.value = ''
  newFormula.value = ''
  error.value = ''
  editingName.value = null
  showSuggestions.value = false
}
</script>

<template>
  <div class="kpi-editor">
    <div class="kpi-header">
      <h3>KPIs</h3>
      <span class="badge">{{ kpis.length }}</span>
    </div>

    <div v-if="kpis.length > 0" class="kpi-list">
      <div v-for="kpi in kpis" :key="kpi.name" class="kpi-item">
        <label class="kpi-checkbox">
          <input
            type="checkbox"
            :checked="selectedMetrics.includes(kpi.name)"
            @change="emit('toggle', kpi.name)"
          />
          <div class="kpi-info">
            <span class="kpi-name">{{ kpi.name }}</span>
            <span class="kpi-formula text-muted">{{ kpi.formula }}</span>
          </div>
        </label>
        <div class="kpi-item-actions">
          <button class="btn-icon" title="Edit KPI" @click="startEdit(kpi)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="btn-icon btn-icon-danger" title="Remove KPI" @click="emit('remove', kpi.name)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showForm" class="kpi-modal-overlay" @click.self="resetForm">
        <div class="kpi-modal">
          <div class="kpi-modal-header">
            <h3>{{ editingName ? 'Edit KPI' : 'New KPI' }}</h3>
            <button class="btn-icon" @click="resetForm">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="kpi-modal-body">
            <label class="form-label">Name</label>
            <input
              v-model="newName"
              type="text"
              placeholder="KPI name (e.g. AttachSuccessRate)"
              class="form-input"
              :disabled="validating"
            />
            <label class="form-label">Formula</label>
            <div class="formula-wrapper">
              <textarea
                ref="formulaInput"
                v-model="newFormula"
                placeholder="Type to search columns... e.g. `ColumnA` / `ColumnB` * 100"
                class="form-input formula-textarea"
                :disabled="validating"
                rows="4"
                @input="onFormulaInput"
                @focus="onFormulaFocus"
                @blur="onFormulaBlur"
                @keydown="onFormulaKeydown"
              />
              <div v-if="showSuggestions && suggestions.length > 0" class="suggestions-dropdown">
                <div
                  v-for="(col, i) in suggestions"
                  :key="col"
                  class="suggestion-item"
                  :class="{ active: i === highlightIndex }"
                  @mousedown.prevent="applySuggestion(col)"
                  @mouseenter="highlightIndex = i"
                >
                  {{ col }}
                </div>
              </div>
            </div>
            <div v-if="error" class="form-error">{{ error }}</div>
          </div>
          <div class="kpi-modal-footer">
            <button class="btn btn-ghost" :disabled="validating" @click="resetForm">Cancel</button>
            <button class="btn btn-primary" :disabled="validating" @click="submitKPI">
              <template v-if="validating">Validating...</template>
              <template v-else>{{ editingName ? 'Update' : 'Add' }}</template>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <div class="kpi-actions">
      <button v-if="!showForm" class="btn btn-ghost btn-sm" @click="showForm = true">
        + Add KPI
      </button>
      <button
        v-if="kpis.length > 0 && !showForm"
        class="btn btn-ghost btn-sm"
        @click="emit('save')"
      >
        Save
      </button>
    </div>
  </div>
</template>

<style scoped>
.kpi-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.kpi-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kpi-header h3 {
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

.kpi-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
}

.kpi-item:hover {
  background: var(--bg-elevated);
}

.kpi-checkbox {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.kpi-checkbox input[type="checkbox"] {
  accent-color: var(--accent-primary);
  width: 14px;
  height: 14px;
}

.kpi-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.kpi-name {
  font-size: 0.85rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-formula {
  font-size: 0.7rem;
  font-family: var(--font-mono);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-item-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.kpi-item:hover .kpi-item-actions {
  opacity: 1;
}

/* Modal overlay */
.kpi-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.kpi-modal {
  background: var(--bg-surface);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg, 12px);
  width: 90%;
  max-width: 540px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

.kpi-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg, var(--space-md));
  border-bottom: 1px solid var(--border-primary);
}

.kpi-modal-header h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.kpi-modal-body {
  padding: var(--space-lg, var(--space-md));
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.kpi-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg, var(--space-md));
  border-top: 1px solid var(--border-primary);
}

.form-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input {
  font-size: 0.85rem;
  padding: var(--space-xs) var(--space-sm);
  width: 100%;
  box-sizing: border-box;
}

.formula-textarea {
  font-family: var(--font-mono);
  resize: vertical;
  min-height: 80px;
  line-height: 1.5;
}

.formula-wrapper {
  position: relative;
}

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 180px;
  overflow-y: auto;
  background: var(--bg-surface);
  border: 1px solid var(--border-primary);
  border-top: none;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  z-index: 1010;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.suggestion-item {
  padding: 6px var(--space-sm);
  font-size: 0.8rem;
  font-family: var(--font-mono);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.suggestion-item:hover,
.suggestion-item.active {
  background: var(--accent-primary);
  color: white;
}

.form-error {
  font-size: 0.8rem;
  color: var(--color-error);
}

.btn-sm {
  font-size: 0.75rem;
  padding: 2px var(--space-sm);
}

.btn-icon {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.12);
}

.btn-icon-danger:hover {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.12);
}

.kpi-actions {
  display: flex;
  gap: var(--space-xs);
}
</style>
