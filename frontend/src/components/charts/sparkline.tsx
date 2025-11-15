interface SparklineProps {
  data: number[]
  width?: number
  height?: number
}

/** 纯 SVG Sparkline，用于展示和值走势。 */
export function Sparkline({ data, width = 320, height = 120 }: SparklineProps) {
  if (!data.length) {
    return <div className="text-sm text-muted-foreground">暂无数据</div>
  }
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const points = data
    .map((value, index) => {
      const x = (index / Math.max(1, data.length - 1)) * width
      const y = height - ((value - min) / range) * height
      return `${x},${y}`
    })
    .join(" ")

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
      <polyline fill="none" stroke="hsl(var(--primary))" strokeWidth={2} points={points} />
    </svg>
  )
}
