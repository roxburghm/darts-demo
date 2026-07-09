import apiClient from './client'
import type { TimeSeriesRequest, TimeSeriesResponse } from './types'

export async function getTimeSeries(
  sessionId: string,
  request: TimeSeriesRequest,
): Promise<TimeSeriesResponse> {
  const { data } = await apiClient.post<TimeSeriesResponse>(
    `/viz/${sessionId}/timeseries`,
    request,
  )
  return data
}
