import apiClient from './client'
import type { UploadInitRequest, UploadInitResponse, UploadStatusResponse } from './types'

export async function initUpload(request: UploadInitRequest): Promise<UploadInitResponse> {
  const { data } = await apiClient.post<UploadInitResponse>('/upload/init', request)
  return data
}

export async function uploadChunk(
  sessionId: string,
  chunkIndex: number,
  chunk: Blob,
): Promise<{ chunk_index: number; chunks_received: number }> {
  const formData = new FormData()
  formData.append('file', chunk, `chunk_${chunkIndex}`)

  const { data } = await apiClient.post(
    `/upload/${sessionId}/chunk?chunk_index=${chunkIndex}`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function completeUpload(
  sessionId: string,
): Promise<{ session_id: string; status: string }> {
  const { data } = await apiClient.post(`/upload/${sessionId}/complete`)
  return data
}

export async function getUploadStatus(sessionId: string): Promise<UploadStatusResponse> {
  const { data } = await apiClient.get<UploadStatusResponse>(`/upload/${sessionId}/status`)
  return data
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/datasets/${sessionId}`)
}
