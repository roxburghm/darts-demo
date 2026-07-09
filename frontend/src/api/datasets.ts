import type { DatasetMetadata, DimensionValues, KPIDefinition } from './types'
import apiClient from './client'

export async function getDatasetMetadata(sessionId: string): Promise<DatasetMetadata> {
  const { data } = await apiClient.get<DatasetMetadata>(`/datasets/${sessionId}`)
  return data
}

export async function getPreview(
  sessionId: string,
  rows: number = 100,
): Promise<{ columns: string[]; rows: Record<string, unknown>[]; total_rows: number }> {
  const { data } = await apiClient.get(`/datasets/${sessionId}/preview`, { params: { rows } })
  return data
}

export async function getDimensionValues(sessionId: string): Promise<DimensionValues[]> {
  const { data } = await apiClient.get<DimensionValues[]>(`/datasets/${sessionId}/dimension-values`)
  return data
}

export async function validateKPIFormula(
  sessionId: string,
  formula: string,
): Promise<string | null> {
  const { data } = await apiClient.post(`/datasets/${sessionId}/kpis/validate`, { formula })
  if (data.valid) return null
  return data.error || 'Invalid formula'
}

export async function saveKPIs(
  sessionId: string,
  kpis: KPIDefinition[],
): Promise<{ status: string; kpi_count: number }> {
  const { data } = await apiClient.put(`/datasets/${sessionId}/kpis`, kpis)
  return data
}
