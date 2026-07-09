<script setup lang="ts">
defineProps<{
  filename: string
  fileSize: string
  status: string
  uploadProgress: number
  parsingProgress: number
  error: string | null
}>()

defineEmits<{
  retry: []
}>()
</script>

<template>
  <div class="progress-card card">
    <div class="progress-header">
      <div class="file-info">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <div>
          <p class="filename">{{ filename }}</p>
          <p class="filesize text-muted">{{ fileSize }}</p>
        </div>
      </div>
    </div>

    <!-- Upload progress -->
    <div v-if="status === 'uploading'" class="progress-section">
      <div class="progress-label">
        <span>Uploading</span>
        <span class="mono">{{ Math.round(uploadProgress) }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-bar__fill" :style="{ width: `${uploadProgress}%` }" />
      </div>
    </div>

    <!-- Parsing progress -->
    <div v-else-if="status === 'parsing'" class="progress-section">
      <div class="progress-label">
        <span>Parsing & analyzing structure</span>
        <span class="mono">{{ Math.round(parsingProgress) }}%</span>
      </div>
      <div class="progress-bar progress-bar--parsing">
        <div class="progress-bar__fill progress-bar__fill--parsing" :style="{ width: `${parsingProgress}%` }" />
      </div>
      <p class="progress-detail text-muted">Detecting headers, classifying columns, converting to optimized format...</p>
    </div>

    <!-- Error -->
    <div v-else-if="status === 'error'" class="progress-section">
      <div class="error-message">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        <span>{{ error }}</span>
      </div>
      <button class="btn btn-secondary" @click="$emit('retry')">Try Again</button>
    </div>

    <!-- Ready -->
    <div v-else-if="status === 'ready'" class="progress-section">
      <div class="success-message">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span>File parsed successfully!</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-card {
  padding: var(--space-lg);
}

.progress-header {
  margin-bottom: var(--space-lg);
}

.file-info {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  color: var(--text-secondary);
}

.filename {
  font-weight: 600;
  color: var(--text-primary);
}

.filesize {
  font-size: 0.85rem;
}

.progress-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  font-weight: 500;
}

.progress-bar {
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar__fill {
  height: 100%;
  background: var(--accent-primary);
  border-radius: 3px;
  transition: width 300ms ease;
}

.progress-bar__fill--parsing {
  background: var(--accent-secondary);
}

.progress-detail {
  font-size: 0.8rem;
}

.error-message {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-error);
  font-weight: 500;
}

.success-message {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-success);
  font-weight: 500;
}
</style>
