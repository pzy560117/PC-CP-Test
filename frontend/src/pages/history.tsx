import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  exportFeatures,
  fetchDraws,
  fetchFeaturesBatch,
  type Draw,
  type FeatureResponse,
} from "@/lib/api"
import { downloadBlob } from "@/lib/utils"

/** 历史数据页面，提供筛选与特征导出。 */
export default function HistoryPage() {
  const [limit, setLimit] = useState(50)
  const [periodFilter, setPeriodFilter] = useState("")
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([])
  const drawsQuery = useQuery<Draw[]>({
    queryKey: ["history-draws", limit],
    queryFn: () => fetchDraws(limit),
    refetchInterval: 60_000,
  })

  const filteredDraws = useMemo(() => {
    if (!drawsQuery.data) return []
    if (!periodFilter) return drawsQuery.data
    return drawsQuery.data.filter((draw) => draw.period.includes(periodFilter))
  }, [drawsQuery.data, periodFilter])

  const featuresQuery = useQuery<FeatureResponse[]>({
    queryKey: ["features-batch", selectedPeriods],
    queryFn: () => fetchFeaturesBatch(selectedPeriods),
    enabled: selectedPeriods.length > 0,
  })

  const selectedFeatureMap = useMemo(() => {
    const map = new Map<string, FeatureResponse>()
    featuresQuery.data?.forEach((item) => map.set(item.period, item))
    return map
  }, [featuresQuery.data])

  const activeFeature = selectedFeatureMap.get(selectedPeriods[0] ?? "")

  const toggleSelection = (period: string) => {
    setSelectedPeriods((prev) =>
      prev.includes(period) ? prev.filter((item) => item !== period) : [...prev, period],
    )
  }

  const handleExport = async (format: "json" | "csv") => {
    if (!selectedPeriods.length) return
    const payload = await exportFeatures({ periods: selectedPeriods, format })
    if ("blob" in payload) {
      downloadBlob(payload.blob, payload.filename)
    } else {
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" })
      downloadBlob(blob, "features.json")
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">历史开奖与特征</p>
          <h2 className="text-3xl font-semibold">历史数据</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="number"
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value) || 1)}
            className="w-24 rounded-md border px-2 py-1 text-sm"
            min={10}
            max={200}
          />
          <input
            type="text"
            placeholder="期号筛选"
            value={periodFilter}
            onChange={(event) => setPeriodFilter(event.target.value)}
            className="rounded-md border px-3 py-1 text-sm"
          />
          <Button variant="outline" disabled={!selectedPeriods.length} onClick={() => handleExport("json")}>
            导出 JSON
          </Button>
          <Button disabled={!selectedPeriods.length} onClick={() => handleExport("csv")}>
            导出 CSV
          </Button>
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>开奖记录</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>选择</TableHead>
                <TableHead>期号</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>号码</TableHead>
                <TableHead>和值</TableHead>
                <TableHead>奇偶/大小</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDraws.map((draw) => (
                <TableRow key={draw.period}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedPeriods.includes(draw.period)}
                      onChange={() => toggleSelection(draw.period)}
                    />
                  </TableCell>
                  <TableCell>{draw.period}</TableCell>
                  <TableCell>{new Date(draw.draw_time).toLocaleString()}</TableCell>
                  <TableCell>{Array.isArray(draw.numbers) ? draw.numbers.join(",") : draw.numbers}</TableCell>
                  <TableCell>{draw.sum}</TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {draw.odd_even} / {draw.big_small}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
              {!filteredDraws.length && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-sm text-muted-foreground">
                    暂无记录
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>特征详情</CardTitle>
        </CardHeader>
        <CardContent>
          {activeFeature ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-semibold">期号 {activeFeature.period}</h3>
                <Badge variant="secondary">已选择 {selectedPeriods.length} 条</Badge>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {Object.entries(activeFeature.features).map(([type, payload]) => (
                  <div key={type} className="rounded-lg border p-3">
                    <p className="text-sm text-muted-foreground">{type}</p>
                    <p className="text-sm">
                      {JSON.stringify(payload.value, null, 2).slice(0, 200)}
                      {JSON.stringify(payload.value).length > 200 ? "..." : ""}
                    </p>
                    <p className="text-xs text-muted-foreground">更新: {payload.updated_at ?? "—"}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">选择任意期号即可查看特征。</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
