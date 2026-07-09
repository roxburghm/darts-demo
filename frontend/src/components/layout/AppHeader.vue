<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUploadStore } from '@/stores/upload'
import { useDatasetStore } from '@/stores/dataset'
import { useModelsStore } from '@/stores/models'
import { useAnalysisStore } from '@/stores/analysis'
import { deleteSession } from '@/api/upload'

const route = useRoute()
const router = useRouter()

const theme = ref(localStorage.getItem('theme') ?? 'dark')

onMounted(() => {
  document.documentElement.dataset.theme = theme.value
})

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('theme', theme.value)
}

const steps = [
  { name: 'upload', label: 'Upload', number: 1 },
  { name: 'preview', label: 'Preview', number: 2 },
  { name: 'configure', label: 'Configure', number: 3 },
  { name: 'models', label: 'Models', number: 4 },
  { name: 'analysis', label: 'Analysis', number: 5 },
]

const currentStep = computed(() => {
  const stepMap: Record<string, number> = {
    upload: 1,
    preview: 2,
    configure: 3,
    models: 4,
    analysis: 5,
  }
  return stepMap[route.name as string] ?? 1
})

const sessionId = computed(() => route.params.sessionId as string | undefined)

function navigateStep(step: { name: string; number: number }) {
  if (step.number > currentStep.value) return
  if (step.number === currentStep.value) return
  if (step.name === 'upload') {
    router.push({ name: 'upload' })
  } else if (sessionId.value) {
    router.push({ name: step.name, params: { sessionId: sessionId.value } })
  }
}

async function clearAll() {
  const sid = sessionId.value
  // Delete server-side data
  if (sid) {
    try { await deleteSession(sid) } catch { /* session may already be gone */ }
    // Clear session storage keys for this session
    sessionStorage.removeItem(`dataset-selections:${sid}`)
    sessionStorage.removeItem(`model-selection:${sid}`)
  }
  // Reset all stores
  useUploadStore().reset()
  useDatasetStore().reset()
  useModelsStore().reset()
  useAnalysisStore().reset()
  // Navigate to upload
  router.push({ name: 'upload' })
}

function downloadParquet() {
  if (!sessionId.value) return
  window.open(`/api/datasets/${sessionId.value}/download`, '_blank')
}
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo">
        <svg width="28" height="28" viewBox="0 0 32 32">
          <rect width="32" height="32" rx="6" fill="#6366f1"/>
          <polyline points="4,22 10,14 16,18 22,8 28,12" fill="none" stroke="#22d3ee" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="16" cy="18" r="3" fill="#ef4444" opacity="0.8"/>
        </svg>
        <span class="logo-text">Anomaly Detection Playground</span>
      </div>
    </div>

    <nav class="header-nav">
      <div
        v-for="step in steps"
        :key="step.name"
        class="nav-step"
        :class="{
          'nav-step--active': currentStep === step.number,
          'nav-step--completed': currentStep > step.number,
          'nav-step--disabled': step.number > currentStep,
          'nav-step--clickable': step.number < currentStep,
        }"
        @click="navigateStep(step)"
      >
        <span class="nav-step__number">{{ step.number }}</span>
        <span class="nav-step__label">{{ step.label }}</span>
      </div>
    </nav>

    <div class="header-right">
      <button
        class="theme-toggle-btn"
        :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        <!-- Sun icon (shown in dark mode → click to go light) -->
        <svg v-if="theme === 'dark'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
        <!-- Moon icon (shown in light mode → click to go dark) -->
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </button>
      <button
        v-if="sessionId"
        class="download-btn"
        title="Download as Parquet"
        @click="downloadParquet"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        <span class="download-btn__label">Parquet</span>
      </button>
      <button
        v-if="sessionId"
        class="clear-btn"
        title="Clear all data and start over"
        @click="clearAll"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
        <span class="clear-btn__label">Clear</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: var(--header-height);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-lg);
  flex-shrink: 0;
}

.header-left {
  flex: 1;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.logo-text {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
}

.header-nav {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.nav-step {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.nav-step--active {
  color: var(--text-primary);
  background: var(--bg-elevated);
}

.nav-step--completed {
  color: var(--color-success);
}

.nav-step--clickable {
  cursor: pointer;
}

.nav-step--clickable:hover {
  background: var(--bg-elevated);
}

.nav-step--disabled {
  opacity: 0.4;
}

.nav-step__number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1.5px solid currentColor;
  font-size: 0.7rem;
  font-weight: 600;
}

.nav-step--active .nav-step__number {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.nav-step--completed .nav-step__number {
  background: var(--color-success);
  border-color: var(--color-success);
  color: white;
}

.nav-step__label {
  display: none;
}

@media (min-width: 768px) {
  .nav-step__label {
    display: inline;
  }
}

.header-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-primary);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.theme-toggle-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.08);
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-primary);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.download-btn:hover {
  color: var(--accent-secondary);
  border-color: var(--accent-secondary);
  background: rgba(34, 211, 238, 0.08);
}

.download-btn__label {
  display: none;
}

.clear-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
  color: var(--color-error);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.clear-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: var(--color-error);
}

.clear-btn__label {
  display: none;
}

@media (min-width: 640px) {
  .download-btn__label {
    display: inline;
  }
  .clear-btn__label {
    display: inline;
  }
}
</style>
