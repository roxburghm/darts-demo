<script setup lang="ts">
defineProps<{
  progress: number
  stage: string
}>()
</script>

<template>
  <div class="analysis-progress">
    <div class="progress-icon">
      <div class="spinner-lg" />
    </div>
    <div class="progress-info">
      <p class="progress-stage">{{ stage || 'Processing...' }}</p>
      <div class="progress-bar">
        <div class="progress-bar__fill" :style="{ width: `${progress}%` }" />
      </div>
      <span class="mono text-muted" style="font-size: 0.75rem;">{{ Math.round(progress) }}%</span>
    </div>
  </div>
</template>

<style scoped>
.analysis-progress {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-lg);
}

.spinner-lg {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-primary);
  border-top-color: var(--accent-secondary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.progress-stage {
  font-weight: 500;
  font-size: 0.9rem;
}

.progress-bar {
  height: 4px;
  background: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar__fill {
  height: 100%;
  background: var(--accent-secondary);
  border-radius: 2px;
  transition: width 300ms ease;
}
</style>
