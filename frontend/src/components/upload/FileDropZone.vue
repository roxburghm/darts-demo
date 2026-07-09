<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  'file-selected': [file: File]
}>()

const isDragging = ref(false)
const fileInput = ref<HTMLInputElement>()

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    emit('file-selected', files[0])
  }
}

function handleFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    emit('file-selected', input.files[0])
  }
}

function openFilePicker() {
  fileInput.value?.click()
}
</script>

<template>
  <div
    class="dropzone"
    :class="{ 'dropzone--active': isDragging }"
    @dragenter.prevent="isDragging = true"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
    @click="openFilePicker"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".csv,.csb,.txt,.parquet"
      class="dropzone__input"
      @change="handleFileInput"
    />

    <div class="dropzone__icon">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    </div>

    <p class="dropzone__text">
      <span v-if="isDragging">Drop your file here</span>
      <span v-else>Drag & drop your CSV or Parquet file here</span>
    </p>
    <p class="dropzone__subtext">or click to browse</p>
    <p class="dropzone__hint">.csv, .csb, .parquet files up to 500MB</p>
  </div>
</template>

<style scoped>
.dropzone {
  border: 2px dashed var(--border-primary);
  border-radius: var(--radius-xl);
  padding: var(--space-2xl) var(--space-xl);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-normal);
  background: var(--bg-surface);
}

.dropzone:hover {
  border-color: var(--accent-primary);
  background: var(--bg-elevated);
}

.dropzone--active {
  border-color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.08);
  border-style: solid;
}

.dropzone__input {
  display: none;
}

.dropzone__icon {
  color: var(--text-muted);
  margin-bottom: var(--space-md);
  transition: color var(--transition-fast);
}

.dropzone:hover .dropzone__icon,
.dropzone--active .dropzone__icon {
  color: var(--accent-primary);
}

.dropzone__text {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: var(--space-xs);
}

.dropzone__subtext {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--space-md);
}

.dropzone__hint {
  color: var(--text-muted);
  font-size: 0.8rem;
}
</style>
