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
  margin:        { l: 10, r: 10, t: 36, b: 10 },
}

export default function PlotlyChart({ data, layout = {}, height = 380, className = "" }: Props) {
  return (
    <Plot
      data={data}
      layout={{
        ...BASE_LAYOUT,
        ...layout,
        height,
        autosize: true,
      }}
      config={{ responsive: true, displayModeBar: false }}
      className={`w-full ${className}`}
      style={{ width: "100%" }}
    />
  )
}
