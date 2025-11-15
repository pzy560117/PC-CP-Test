const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export interface Draw {
  period: string
  draw_time: string
  numbers: string
  sum: number
  span: number
  odd_even: string
  big_small: string
}

export interface AnalysisResult {
  id: number
  analysis_type: string
  result_summary?: string
  result_data: Record<string, unknown>
  created_at: string
}

export interface AnalysisJob {
  id: number
  job_type: string
  status: string
  priority: number
  payload: Record<string, unknown>
  created_at: string
  updated_at?: string
}

export interface FeatureResponse {
  period: string
  features: Record<
    string,
    {
      schema_version?: number
      meta?: Record<string, unknown>
      value: Record<string, unknown>
    }
  >
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

export const fetchDraws = (limit = 20) =>
  apiGet<{ items: Draw[] }>(`/api/v1/draws?limit=${limit}`).then((r) => r.items)

export const fetchAnalysisResults = (limit = 6) =>
  apiGet<{ items: AnalysisResult[] }>(
    `/api/v1/analysis/results?limit=${limit}&offset=0`,
  ).then((r) => r.items)

export const fetchAnalysisJobs = (limit = 5) =>
  apiGet<{ items: AnalysisJob[] }>(
    `/api/v1/analysis/jobs?limit=${limit}&status=pending&offset=0`,
  ).then((r) => r.items)

export const fetchFeatures = (period: string) =>
  apiGet<FeatureResponse>(`/api/v1/features/${period}`)
