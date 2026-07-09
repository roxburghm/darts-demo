import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { initUpload, uploadChunk, completeUpload } from '@/api/upload'

const CHUNK_SIZE = 2 * 1024 * 1024 // 2MB

export const useUploadStore = defineStore('upload', () => {
  const sessionId = ref<string | null>(null)
  const uploadId = ref<string | null>(null)
  const filename = ref('')
  const fileSize = ref(0)
  const chunksUploaded = ref(0)
  const totalChunks = ref(0)
  const parsingProgress = ref(0)
  const status = ref<'idle' | 'uploading' | 'parsing' | 'ready' | 'error'>('idle')
  const error = ref<string | null>(null)

  const uploadProgress = computed(() =>
    totalChunks.value > 0 ? (chunksUploaded.value / totalChunks.value) * 100 : 0,
  )

  async function upload(file: File) {
    status.value = 'uploading'
    error.value = null
    filename.value = file.name
    fileSize.value = file.size
    chunksUploaded.value = 0

    try {
      // Detect file type from extension
      const fileType = file.name.toLowerCase().endsWith('.parquet') ? 'parquet' as const : 'csv' as const

      // Init
      const initResp = await initUpload({
        filename: file.name,
        file_size: file.size,
        chunk_size: CHUNK_SIZE,
        file_type: fileType,
      })

      sessionId.value = initResp.session_id
      uploadId.value = initResp.upload_id
      totalChunks.value = initResp.total_chunks

      // Upload chunks
      for (let i = 0; i < initResp.total_chunks; i++) {
        const start = i * CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, file.size)
        const chunk = file.slice(start, end)

        await uploadChunk(initResp.session_id, i, chunk)
        chunksUploaded.value = i + 1
      }

      // Complete
      status.value = 'parsing'
      await completeUpload(initResp.session_id)
    } catch (err: any) {
      status.value = 'error'
      error.value = err?.message || 'Upload failed'
    }
  }

  function setParsingProgress(progress: number) {
    parsingProgress.value = progress
  }

  function setReady() {
    status.value = 'ready'
    parsingProgress.value = 100
  }

  function setError(msg: string) {
    status.value = 'error'
    error.value = msg
  }

  function reset() {
    sessionId.value = null
    uploadId.value = null
    filename.value = ''
    fileSize.value = 0
    chunksUploaded.value = 0
    totalChunks.value = 0
    parsingProgress.value = 0
    status.value = 'idle'
    error.value = null
  }

  return {
    sessionId,
    uploadId,
    filename,
    fileSize,
    chunksUploaded,
    totalChunks,
    parsingProgress,
    status,
    error,
    uploadProgress,
    upload,
    setParsingProgress,
    setReady,
    setError,
    reset,
  }
})
