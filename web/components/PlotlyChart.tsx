"use client"
import dynamic from "next/dynamic"

// Plotly must be client-side only (no SSR)
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false })

interface Props {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layout?: Record<string, any>
  height?: number
  className?: string
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const BASE_LAYOUT: Record<string, any> = {
  paper_bgcolor: "#ffffff",
  plot_bgcolor:  "#f8fafc",
  font:          { color: "#0f172a", family: "Inter, sans-serif", size: 12 },
  margin:        { l: 74, r: 28, t: 48, b: 66 },
  xaxis:         { automargin: true, title: { standoff: 18 }, tickfont: { size: 11 } },
  yaxis:         { automargin: true, title: { standoff: 18 }, tickfont: { size: 11 } },
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mergeAxis(baseAxis: Record<string, any>, axis?: Record<string, any>) {
  if (!axis) return baseAxis
  const title = axis.title
  const mergedTitle = typeof title === "string"
    ? { ...(baseAxis.title ?? {}), text: title }
    : { ...(baseAxis.title ?? {}), ...(title ?? {}) }

  return {
    ...baseAxis,
    ...axis,
    title: mergedTitle,
    tickfont: { ...(baseAxis.tickfont ?? {}), ...(axis.tickfont ?? {}) },
  }
}

export default function PlotlyChart({ data, layout = {}, height = 380, className = "" }: Props) {
  const mergedLayout = {
    ...BASE_LAYOUT,
    ...layout,
    margin: { ...BASE_LAYOUT.margin, ...(layout.margin ?? {}) },
    xaxis: mergeAxis(BASE_LAYOUT.xaxis, layout.xaxis),
    yaxis: mergeAxis(BASE_LAYOUT.yaxis, layout.yaxis),
    height,
    autosize: true,
  }

  return (
    <Plot
      data={data}
      layout={mergedLayout}
      config={{ responsive: true, displayModeBar: false }}
      className={`w-full ${className}`}
      style={{ width: "100%" }}
    />
  )
}
