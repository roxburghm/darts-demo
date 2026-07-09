<script setup lang="ts">
import { AGGREGATION_OPTIONS } from '@/utils/constants'

defineProps<{
  value: string
}>()

const emit = defineEmits<{
  update: [value: string]
}>()
</script>

<template>
  <div class="aggregation-control">
    <h3 class="label">Time Aggregation</h3>
    <div class="agg-options">
      <button
        v-for="opt in AGGREGATION_OPTIONS"
        :key="opt.value"
        class="agg-option"
        :class="{ 'agg-option--active': value === opt.value }"
        @click="emit('update', opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.aggregation-control {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.agg-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.agg-option {
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.agg-option:hover {
  border-color: var(--text-muted);
  color: var(--text-primary);
}

.agg-option--active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}
</style>
