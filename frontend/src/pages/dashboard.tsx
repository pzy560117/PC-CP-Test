import { useMemo } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"

import {
  fetchAnalysisJobs,
  fetchAnalysisResults,
  fetchDraws,
  fetchFeatures,
  type AnalysisJob,
  type AnalysisResult,
  type Draw,
  type FeatureResponse,
} from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"

const REFRESH_INTERVAL = 60_000

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const drawsQuery = useQuery<Draw[]>({
    queryKey: ["draws"],
    queryFn: () => fetchDraws(20),
    refetchInterval: REFRESH_INTERVAL,
  })

  const latestPeriod = drawsQuery.data?.[0]?.period

  const featuresQuery = useQuery<FeatureResponse>({
    queryKey: ["features", latestPeriod],
    queryFn: () => fetchFeatures(latestPeriod!),
    enabled: Boolean(latestPeriod),
    refetchInterval: REFRESH_INTERVAL,
  })

  const analysisResultsQuery = useQuery<AnalysisResult[]>({
    queryKey: ["analysis-results"],
    queryFn: () => fetchAnalysisResults({ limit: 6 }),
    refetchInterval: REFRESH_INTERVAL,
  })

  const jobsQuery = useQuery<AnalysisJob[]>({
    queryKey: ["analysis-jobs"],
    queryFn: () => fetchAnalysisJobs(6),
    refetchInterval: REFRESH_INTERVAL,
  })

  const latestFeatures = featuresQuery.data?.features
  const basicStats = latestFeatures?.basic_stats?.value as Record<string, number | string> | undefined
  const trendStats = latestFeatures?.trend_summary?.value as Record<string, number | string> | undefined
  const trendDelta =
    trendStats && trendStats.trend_delta !== undefined
      ? Number(trendStats.trend_delta)
      : undefined

  const latestUpdatedAt = drawsQuery.data?.[0]?.draw_time
  const isLoading =
    drawsQuery.isLoading || featuresQuery.isLoading || analysisResultsQuery.isLoading || jobsQuery.isLoading

  const jobsBreakdown = useMemo<Record<string, number>>(() => {
    const counts: Record<string, number> = {}
    jobsQuery.data?.forEach((job) => {
      counts[job.status] = (counts[job.status] ?? 0) + 1
    })
    return counts
  }, [jobsQuery.data])

  const handleManualRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["draws"] })
    queryClient.invalidateQueries({ queryKey: ["analysis-results"] })
    queryClient.invalidateQueries({ queryKey: ["analysis-jobs"] })
    if (latestPeriod) {
      queryClient.invalidateQueries({ queryKey: ["features", latestPeriod] })
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10 md:px-8">
        <section className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">腾讯分分彩数据平台</p>
            <h1 className="text-3xl font-semibold tracking-tight">实时仪表盘</h1>
            <p className="text-sm text-muted-foreground">
              展示采集数据、分析结果与特征提取状态，默认每分钟自动刷新。
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={handleManualRefresh}>
              手动刷新
            </Button>
            <Badge variant="secondary">
              上次更新: {latestUpdatedAt ? new Date(latestUpdatedAt).toLocaleString() : "—"}
            </Badge>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <InfoCard
            title="最新开奖"
            description={`期号 ${latestPeriod ?? "—"}`}
            value={drawsQuery.data ? formatNumbers(drawsQuery.data[0]?.numbers) : "—"}
            footer={`和值 ${basicStats?.sum ?? "—"} / 跨度 ${basicStats?.span ?? "—"}`}
            loading={drawsQuery.isLoading}
          />
          <InfoCard
            title="特征摘要"
            description="basic_stats"
            value={`奇偶 ${basicStats?.odd_even ?? "—"} / 大小 ${basicStats?.big_small ?? "—"}`}
            footer={`平均值 ${basicStats?.mean ?? "—"} / 计数 ${basicStats?.count ?? "—"}`}
            loading={featuresQuery.isLoading}
          />
          <InfoCard
            title="趋势漂移"
            description="trend_summary"
            value={
              trendDelta !== undefined
                ? `${trendDelta > 0 ? "上升" : "下降"} ${Math.abs(trendDelta).toFixed(2)}`
                : "—"
            }
            footer={`窗口 ${trendStats?.window ?? "—"} / 最新和值 ${trendStats?.latest_sum ?? "—"}`}
            loading={featuresQuery.isLoading}
          />
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>最近开奖</CardTitle>
              <CardDescription>展示最近 5 期的开奖与基础衍生数据。</CardDescription>
            </CardHeader>
            <CardContent>
              {drawsQuery.isLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>期号</TableHead>
                      <TableHead>开奖号码</TableHead>
                      <TableHead>奇偶/大小</TableHead>
                      <TableHead className="text-right">和值</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {drawsQuery.data?.slice(0, 5).map((draw) => (
                      <TableRow key={draw.period}>
                        <TableCell className="font-medium">{draw.period}</TableCell>
                        <TableCell>{formatNumbers(draw.numbers)}</TableCell>
                        <TableCell>{`${draw.odd_even}/${draw.big_small}`}</TableCell>
                        <TableCell className="text-right">{draw.sum}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                  <TableCaption>数据来源于当前 MySQL + FastAPI 接口。</TableCaption>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>分析任务状态</CardTitle>
              <CardDescription>
                pending: {jobsBreakdown.pending ?? 0} ｜ processing: {jobsBreakdown.processing ?? 0} ｜ failed:{" "}
                {jobsBreakdown.failed ?? 0}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {jobsQuery.isLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <div className="space-y-2">
                  {(jobsQuery.data ?? []).map((job) => (
                    <div
                      className="flex flex-col gap-1 rounded-lg border border-border p-3"
                      key={job.id}
                    >
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{job.job_type}</span>
                        <Badge variant={statusToBadge(job.status)}>{job.status}</Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        payload: {JSON.stringify(job.payload)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        <section>
          <Card>
            <CardHeader>
              <CardTitle>分析结果看板</CardTitle>
              <CardDescription>最近 6 条 analysis_results 输出，包含摘要与时间。</CardDescription>
            </CardHeader>
            <CardContent>
              {analysisResultsQuery.isLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <div className="grid gap-4">
                  {analysisResultsQuery.data?.map((result) => (
                    <div
                      key={result.id}
                      className="rounded-lg border border-border p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium">{result.analysis_type}</p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(result.created_at).toLocaleString()}
                          </p>
                        </div>
                        <Badge variant="outline">#{result.id}</Badge>
                      </div>
                      <Separator className="my-3" />
                      <p className="text-sm text-muted-foreground">
                        {result.result_summary ||
                          JSON.stringify(result.result_data).slice(0, 120)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        {isLoading && (
          <p className="text-center text-xs text-muted-foreground">
            正在同步后端数据，请稍候…
          </p>
        )}
      </div>
    </div>
  )
}

interface InfoCardProps {
  title: string
  description: string
  value: string
  footer?: string
  loading?: boolean
}

function InfoCard({ title, description, value, footer, loading }: InfoCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardDescription>{description}</CardDescription>
        <CardTitle className="text-xl">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {loading ? (
          <Skeleton className="h-8 w-3/4" />
        ) : (
          <p className="text-2xl font-semibold">{value}</p>
        )}
        {footer && <p className="text-sm text-muted-foreground">{footer}</p>}
      </CardContent>
    </Card>
  )
}

function formatNumbers(value?: string | string[]) {
  if (!value) return "—"
  try {
    const parsed = typeof value === "string" ? JSON.parse(value) : value
    if (Array.isArray(parsed)) {
      return parsed.join(" ")
    }
  } catch {
    // ignore parse errors
  }
  return typeof value === "string" ? value : value.join(" ")
}

function statusToBadge(status: string) {
  switch (status) {
    case "finished":
      return "success"
    case "failed":
      return "destructive"
    case "processing":
      return "warning"
    default:
      return "secondary"
  }
}
