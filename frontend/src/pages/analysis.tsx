import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"

import { Sparkline } from "@/components/charts/sparkline"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  exportAnalysisResults,
  fetchAnalysisResults,
  type AnalysisResult,
} from "@/lib/api"
import { downloadBlob } from "@/lib/utils"

const ANALYSIS_TYPES = [
  { value: "statistical_analysis", label: "统计 / Markov" },
  { value: "trend_summary", label: "趋势窗口" },
]

/** 分析图表页面，展示统计结果与策略回测。 */
export default function AnalysisPage() {
  const [analysisType, setAnalysisType] = useState("statistical_analysis")
  const statsQuery = useQuery<AnalysisResult[]>({
    queryKey: ["analysis-results", analysisType],
    queryFn: () => fetchAnalysisResults({ limit: 1, analysisType }),
    refetchInterval: 60_000,
  })
  const strategyQuery = useQuery<AnalysisResult[]>({
    queryKey: ["analysis-results", "strategy_backtest"],
    queryFn: () => fetchAnalysisResults({ limit: 1, analysisType: "strategy_backtest" }),
    refetchInterval: 120_000,
  })

  const statsResult = statsQuery.data?.[0]
  const strategyResult = strategyQuery.data?.[0]
  const strategyData = (strategyResult?.result_data ?? {}) as Record<string, number | string>
  const strategyWinRate = Number(strategyData.win_rate ?? 0)
  const strategyPnl = Number(strategyData.pnl ?? 0)
  const statsData = (statsResult?.result_data ?? {}) as Record<string, any>
  const randomness = statsData.randomness as Record<string, number> | undefined
  const sequence = (statsData.sequence as Array<{ sum: number }> | undefined)?.map((item) =>
    Number(item.sum),
  )
  const markov = statsData.markov as Record<string, Record<string, number>> | undefined

  const markovRows = useMemo(() => {
    const parity = markov?.parity ?? {}
    return Object.entries(parity).map(([source, targets]) => ({
      source,
      targets,
    }))
  }, [markov])

  const handleExport = async (format: "json" | "csv") => {
    const payload = await exportAnalysisResults({
      format,
      analysisType,
      limit: 200,
    })
    if ("blob" in payload) {
      downloadBlob(payload.blob, payload.filename)
    } else {
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" })
      downloadBlob(blob, `analysis-${analysisType}.json`)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">统计与策略概览</p>
          <h2 className="text-3xl font-semibold">分析图表</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={analysisType}
            onChange={(event) => setAnalysisType(event.target.value)}
            className="rounded-md border bg-background px-3 py-2 text-sm"
          >
            {ANALYSIS_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <Button variant="outline" onClick={() => handleExport("json")}>
            导出 JSON
          </Button>
          <Button onClick={() => handleExport("csv")}>导出 CSV</Button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>卡方统计</CardTitle>
            <CardDescription>数字频率偏差</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{randomness?.chi_square?.toFixed(2) ?? "—"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>奇偶游程</CardTitle>
            <CardDescription>游程数量越高越随机</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{randomness?.runs ?? "—"}</p>
            <p className="text-sm text-muted-foreground">
              均值: {randomness?.mean_sum?.toFixed(1) ?? "—"} / 方差:
              {randomness?.std_sum?.toFixed(1) ?? "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>最新分析</CardTitle>
            <CardDescription>{statsResult?.result_summary ?? "等待结果"}</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="secondary">更新: {statsResult?.created_at ?? "—"}</Badge>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>和值走势</CardTitle>
          <CardDescription>来自 statistical_analysis.sequence</CardDescription>
        </CardHeader>
        <CardContent>
          <Sparkline data={sequence ?? []} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Markov 转移矩阵</CardTitle>
          <CardDescription>奇偶状态转移概率</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>当前状态</TableHead>
                <TableHead>目标状态</TableHead>
                <TableHead>概率</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {markovRows.map((row) =>
                Object.entries(row.targets).map(([target, value]) => (
                  <TableRow key={`${row.source}-${target}`}>
                    <TableCell>{row.source}</TableCell>
                    <TableCell>{target}</TableCell>
                    <TableCell>{(value * 100).toFixed(2)}%</TableCell>
                  </TableRow>
                )),
              )}
              {!markovRows.length && (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-sm text-muted-foreground">
                    暂无数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {strategyResult && (
        <Card>
          <CardHeader>
            <CardTitle>策略回测</CardTitle>
            <CardDescription>{strategyResult.result_summary}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-3xl font-semibold">PnL: {strategyPnl.toFixed(2)}</p>
              <p className="text-sm text-muted-foreground">
                胜率: {strategyWinRate ? `${(strategyWinRate * 100).toFixed(2)}%` : "—"}
              </p>
            </div>
            <div className="flex gap-2">
              <Badge variant="success">交易: {strategyResult.result_data?.trades ?? 0}</Badge>
              <Badge variant="outline">
                信号: {strategyResult.result_data?.latest_signal ?? "—"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
