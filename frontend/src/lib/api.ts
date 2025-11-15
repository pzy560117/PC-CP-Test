const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
const JSON_HEADERS = { "Content-Type": "application/json" }

export interface Draw {
  period: string
  draw_time: string
  numbers: string | string[]
  sum: number
  span: number
  odd_even: string
  big_small: string
}

export interface AnalysisResult {
  id: number
  analysis_type: string
  schema_version: number
  result_summary?: string
  result_data: Record<string, unknown>
  metadata?: Record<string, unknown>
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
      updated_at?: string
    }
  >
}

interface AnalysisQueryParams {
  limit?: number
  offset?: number
  analysisType?: string
}

interface AnalysisExportParams extends AnalysisQueryParams {
  format: "json" | "csv"
}

interface FeatureExportParams {
  periods: string[]
  format: "json" | "csv"
}

/** 构造查询字符串。 */
function buildQuery(params: Record<string, string | number | undefined | null>) {
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join("&")
  return query ? `?${query}` : ""
}

/** 发起 GET 请求。 */
async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

/** 发起 POST 请求。 */
async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

/** 查询最近开奖记录。 */
export const fetchDraws = (limit = 20) =>
  apiGet<{ items: Draw[] }>(`/api/v1/draws${buildQuery({ limit })}`).then((r) => r.items)

/** 按期号查询单条开奖。 */
export const fetchDraw = (period: string) => apiGet<Draw>(`/api/v1/draws/${period}`)

/** 查询分析结果，可选类型/分页。 */
export const fetchAnalysisResults = (params: AnalysisQueryParams = {}) => {
  const { limit = 6, offset = 0, analysisType } = params
  const query = buildQuery({ limit, offset, analysis_type: analysisType })
  return apiGet<{ items: AnalysisResult[] }>(`/api/v1/analysis/results${query}`).then((r) => r.items)
}

/** 导出分析结果，JSON 返回解析后对象，CSV 返回 blob。 */
export const exportAnalysisResults = async (params: AnalysisExportParams) => {
  const { format, limit = 100, offset = 0, analysisType } = params
  const query = buildQuery({ limit, offset, analysis_type: analysisType, export_format: format })
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/results/export${query}`)
  if (!response.ok) {
    throw new Error(`Export failed: ${response.status}`)
  }
  if (format === "json") {
    return response.json()
  }
  const blob = await response.blob()
  return {
    blob,
    filename: parseFilename(response.headers.get("Content-Disposition"), "analysis-results.csv"),
  }
}

/** 查询分析任务状态。 */
export const fetchAnalysisJobs = (limit = 5, status = "pending") => {
  const query = buildQuery({ limit, offset: 0, status })
  return apiGet<{ items: AnalysisJob[] }>(`/api/v1/analysis/jobs${query}`).then((r) => r.items)
}

/** 查询单期特征。 */
export const fetchFeatures = (period: string) => apiGet<FeatureResponse>(`/api/v1/features/${period}`)

/** 批量查询多期特征。 */
export const fetchFeaturesBatch = (periods: string[]) =>
  apiPost<{ items: FeatureResponse[]; count: number }>(`/api/v1/features/batch`, { periods }).then(
    (r) => r.items,
  )

/** 导出特征结果。 */
export const exportFeatures = async ({ periods, format }: FeatureExportParams) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/features/export`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ periods, export_format: format }),
  })
  if (!response.ok) {
    throw new Error(`Export failed: ${response.status}`)
  }
  if (format === "json") {
    return response.json()
  }
  const blob = await response.blob()
  return {
    blob,
    filename: parseFilename(response.headers.get("Content-Disposition"), "features.csv"),
  }
}

/** 从响应头解析文件名。 */
function parseFilename(headerValue: string | null, fallback: string) {
  if (!headerValue) return fallback
  const match = /filename="?([^\";]+)"?/i.exec(headerValue)
  return match ? match[1] : fallback
}
