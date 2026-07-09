<script setup lang="ts">
import type { ModelInfo } from '@/api/types'

const props = withDefaults(defineProps<{
  model: ModelInfo
  compatible: boolean
  reason: string | null
  selected: boolean
  condensed?: boolean
}>(), {
  condensed: false,
})

const emit = defineEmits<{
  select: []
  proceed: []
}>()

function handleClick() {
  if (props.compatible) {
    emit('select')
  }
}

function handleDblClick() {
  if (props.compatible) {
    emit('select')
    emit('proceed')
  }
}

const isFoundation = props.model.foundation
</script>

<template>
  <!-- Condensed row variant -->
  <div
    v-if="condensed"
    class="model-row"
    :class="{
      'model-row--selected': selected,
      'model-row--disabled': !compatible,
    }"
    @click="handleClick"
    @dblclick="handleDblClick"
  >
    <div class="model-row__icon" :class="{ 'model-card__icon--foundation': isFoundation }">
      <svg v-if="model.category === 'scorer'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <svg v-else-if="isFoundation" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
      </svg>
      <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    </div>
    <span class="model-row__name">{{ model.name }}</span>
    <div class="model-row__badges">
      <span v-if="isFoundation" class="badge badge--foundation">Foundation</span>
      <span v-if="model.gpu_accelerated" class="badge badge--gpu">GPU</span>
      <span v-if="!model.supports_multivariate" class="badge badge--univariate">Uni</span>
    </div>
    <div v-if="selected" class="model-row__check">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
    </div>
  </div>

  <!-- Full card variant -->
  <div
    v-else
    class="model-card"
    :class="{
      'model-card--selected': selected,
      'model-card--disabled': !compatible,
    }"
    @click="handleClick"
    @dblclick="handleDblClick"
  >
    <div class="model-card__header">
      <div class="model-card__icon" :class="{ 'model-card__icon--foundation': isFoundation }">
        <svg v-if="model.category === 'scorer'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <svg v-else-if="isFoundation" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
        </svg>
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      </div>
      <div class="model-card__badges">
        <span v-if="isFoundation" class="badge badge--foundation">Foundation</span>
        <span v-else class="badge badge--category">{{ model.category === 'scorer' ? 'Scorer' : 'Forecast' }}</span>
        <span v-if="model.gpu_accelerated" class="badge badge--gpu">GPU</span>
        <span v-if="!model.supports_multivariate" class="badge badge--univariate">Univariate</span>
      </div>
    </div>

    <h3 class="model-card__name">{{ model.name }}</h3>
    <p class="model-card__desc">{{ model.description }}</p>

    <div class="model-card__meta">
      <span>Min {{ model.min_data_points }} points</span>
      <span v-if="model.requires_seasonality">Seasonal data</span>
    </div>

    <div v-if="!compatible && reason" class="model-card__warning">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      {{ reason }}
    </div>

    <div v-if="selected" class="model-card__check">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.model-card {
  position: relative;
  background: var(--bg-surface);
  border: 2px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.model-card:hover:not(.model-card--disabled) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 1px var(--accent-primary);
}

.model-card--selected {
  border-color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.06);
  box-shadow: 0 0 0 1px var(--accent-primary);
}

.model-card--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.model-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.model-card__icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  color: var(--accent-primary);
}

.model-card__badges {
  display: flex;
  gap: 4px;
}

.badge {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.badge--category {
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-primary);
}

.badge--foundation {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.badge--gpu {
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
}

.badge--univariate {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.model-card__icon--foundation {
  color: #10b981;
}

.model-card__name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.model-card__desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
  flex: 1;
}

.model-card__meta {
  display: flex;
  gap: var(--space-md);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.model-card__warning {
  display: flex;
  align-items: flex-start;
  gap: var(--space-xs);
  font-size: 0.75rem;
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.08);
  padding: var(--space-sm);
  border-radius: var(--radius-sm);
  line-height: 1.3;
}

.model-card__check {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
  color: var(--accent-primary);
}

/* --- Condensed row variant --- */

.model-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 8px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.model-row:hover:not(.model-row--disabled) {
  border-color: var(--accent-primary);
}

.model-row--selected {
  border-color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.06);
}

.model-row--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.model-row__icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  color: var(--accent-primary);
  flex-shrink: 0;
}

.model-row__name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.model-row__badges {
  display: flex;
  gap: 3px;
  margin-left: auto;
  flex-shrink: 0;
}

.model-row__badges .badge {
  font-size: 0.55rem;
  padding: 1px 4px;
}

.model-row__check {
  color: var(--accent-primary);
  flex-shrink: 0;
}
</style>
