<script setup lang="ts">
import { watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUploadStore } from '@/stores/upload'
import { getUploadStatus } from '@/api/upload'
import FileDropZone from '@/components/upload/FileDropZone.vue'
import UploadProgress from '@/components/upload/UploadProgress.vue'
import { formatBytes } from '@/utils/formatters'

const router = useRouter()
const upload = useUploadStore()

let socket: WebSocket | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

function connectWS(sessionId: string) {
  // Clean up previous connection
  if (socket) {
    socket.onclose = null
    socket.close()
    socket = null
  }

  const wsBase = import.meta.env.DEV
    ? 'ws://localhost:8001'
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  const url = `${wsBase}/api/ws/${sessionId}`
  socket = new WebSocket(url)

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'ping') return
      if (msg.type === 'progress' && msg.stage === 'parsing') {
        upload.setParsingProgress(msg.progress ?? 0)
      } else if (msg.type === 'complete' && msg.stage === 'parsing') {
        upload.setReady()
      } else if (msg.type === 'error') {
        upload.setError(msg.detail ?? 'Parsing failed')
      }
    } catch { /* ignore malformed */ }
  }
}

// Fallback: poll status in case WS messages are missed
function startPolling(sessionId: string) {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const status = await getUploadStatus(sessionId)
      if (status.status === 'ready') {
        upload.setReady()
        stopPolling()
      } else if (status.status === 'error') {
        upload.setError(status.error ?? 'Parsing failed')
        stopPolling()
      } else {
        upload.setParsingProgress(status.parsing_progress)
      }
    } catch { /* ignore poll errors */ }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// Connect WS as soon as sessionId is available (during chunk upload),
// so it's ready before completeUpload() triggers the background parsing task.
watch(
  () => upload.sessionId,
  (sessionId) => {
    if (sessionId) {
      connectWS(sessionId)
      startPolling(sessionId)
    }
  },
)

async function handleFile(file: File) {
  await upload.upload(file)
}

watch(
  () => upload.status,
  (status) => {
    if (status === 'ready' && upload.sessionId) {
      stopPolling()
      router.push({ name: 'preview', params: { sessionId: upload.sessionId } })
    }
  },
)

onUnmounted(() => {
  if (socket) {
    socket.onclose = null
    socket.close()
    socket = null
  }
  stopPolling()
})
</script>

<template>
  <div class="upload-view">
    <div class="upload-container">
      <div class="upload-header">
        <h1>Upload Performance Data</h1>
        <p class="text-secondary">
          Drag and drop your CSV or Parquet file, or click to browse. Files up to 500MB are supported.
        </p>
      </div>

      <div class="privacy-notice">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <div>
          <p>Your data is cached temporarily on the server for the duration of your session and used solely for analysis. It is not stored permanently, shared, or used in any other way.</p>
          <p>Use the <strong>Clear</strong> button in the header to immediately delete all traces of your data from the server. Uploading a new file automatically replaces any previously uploaded data.</p>
        </div>
      </div>

      <FileDropZone
        v-if="upload.status === 'idle'"
        @file-selected="handleFile"
      />

      <UploadProgress
        v-else
        :filename="upload.filename"
        :file-size="formatBytes(upload.fileSize)"
        :status="upload.status"
        :upload-progress="upload.uploadProgress"
        :parsing-progress="upload.parsingProgress"
        :error="upload.error"
        @retry="upload.reset()"
      />
    </div>
  </div>
</template>

<style scoped>
.upload-view {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}

.upload-container {
  width: 100%;
  max-width: 600px;
}

.upload-header {
  text-align: center;
  margin-bottom: var(--space-xl);
}

.upload-header h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: var(--space-sm);
}

.upload-header p {
  font-size: 0.95rem;
}

.privacy-notice {
  display: flex;
  gap: var(--space-sm);
  align-items: flex-start;
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  margin-bottom: var(--space-lg);
}

.privacy-notice svg {
  flex-shrink: 0;
  color: var(--accent-primary);
  margin-top: 2px;
}

.privacy-notice p {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.privacy-notice p + p {
  margin-top: var(--space-xs);
}
</style>
