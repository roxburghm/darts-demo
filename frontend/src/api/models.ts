import apiClient from './client'
import type {
  ModelInfo,
  CompatibilityResponse,
  DartsDetectionConfig,
  DartsAnomalyResult,
  AggregationLevel,
} from './types'

export async function getModels(): Promise<ModelInfo[]> {
  const { data } = await apiClient.get<ModelInfo[]>('/models/')
  return data
}

export async function checkCompatibility(
  sessionId: string,
  request: {
    metrics: string[]
    dimensions?: string[] | null
    dimension_filters?: Record<string, string[]> | null
    aggregation: AggregationLevel
  },
): Promise<CompatibilityResponse> {
  const { data } = await apiClient.post<CompatibilityResponse>(
    `/models/${sessionId}/compatibility`,
    request,
  )
  return data
}

export async function triggerDartsDetection(
  sessionId: string,
  config: DartsDetectionConfig,
): Promise<{ run_id: string; status: string }> {
  const { data } = await apiClient.post(`/models/${sessionId}/detect`, config)
  return data
}

export async function getDartsResults(
  sessionId: string,
  runId: string,
): Promise<DartsAnomalyResult> {
  const { data } = await apiClient.get<DartsAnomalyResult>(
    `/models/${sessionId}/results/${runId}`,
  )
  return data
}
