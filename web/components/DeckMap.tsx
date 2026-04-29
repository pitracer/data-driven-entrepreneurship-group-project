"use client"
import { useState } from "react"
import DeckGL from "@deck.gl/react"
import { ScatterplotLayer } from "@deck.gl/layers"
import { Map } from "react-map-gl/maplibre"
import "maplibre-gl/dist/maplibre-gl.css"
import type { Firm } from "@/lib/types"
import { CATEGORY_COLORS } from "@/lib/types"

interface Props { firms: Firm[] }

const INITIAL_VIEW = { longitude: 6.78, latitude: 51.22, zoom: 11, pitch: 0, bearing: 0 }

function jitter(id: string, axis: string): number {
  let h = 0
  for (const c of id + axis) h = (h * 31 + c.charCodeAt(0)) & 0xffffffff
  return ((h & 0xffff) / 0xffff - 0.5) * 0.0003 // ~15m spread, deterministic per firm
}

function hexToRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b]
}

function markerRadius(firm: Firm): number {
  const employees = Math.max(0, firm.employees_2024 ?? 0)
  const categoryBoost = firm.category_2024 === "Gazelle" ? 3 : firm.category_2024 === "Scaler" ? 2 : 0
  return Math.min(18, Math.max(4, Math.log1p(employees) * 1.15 + categoryBoost))
}

export default function DeckMap({ firms }: Props) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; firm: Firm } | null>(null)

  const layer = new ScatterplotLayer<Firm>({
    id: "firms",
    data: firms,
    getPosition: f => [f.lon! + jitter(f.bvd_id, "x"), f.lat! + jitter(f.bvd_id, "y")],
    getRadius: markerRadius,
    getFillColor: f => [...hexToRgb(CATEGORY_COLORS[f.category_2024 ?? "Other"] ?? "#94A3B8"), 150] as [number,number,number,number],
    getLineColor: [255, 255, 255, 210],
    getLineWidth: 1,
    pickable: true,
    stroked: true,
    radiusUnits: "pixels",
    radiusMinPixels: 4,
    radiusMaxPixels: 18,
    onHover: info => {
      if (info.object) setTooltip({ x: info.x, y: info.y, firm: info.object })
      else setTooltip(null)
    },
  })

  return (
    <div className="relative w-full h-full">
      <DeckGL
        initialViewState={INITIAL_VIEW}
        controller={true}
        layers={[layer]}
        style={{ width: "100%", height: "100%" }}
      >
        <Map
          mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
          style={{ width: "100%", height: "100%" }}
        />
      </DeckGL>
      {tooltip && (
        <div
          className="absolute bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs pointer-events-none z-10 max-w-[220px]"
          style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
        >
          <p className="font-semibold text-slate-800">{tooltip.firm.company_name}</p>
          <p className="text-slate-500">{tooltip.firm.category_2024 ?? "Other"} · NACE {tooltip.firm.nace_letter}</p>
          {tooltip.firm.employees_2024 && <p className="text-slate-600">{tooltip.firm.employees_2024.toLocaleString()} employees</p>}
          {tooltip.firm.snippet && <p className="text-slate-500 mt-1 line-clamp-2">{tooltip.firm.snippet}</p>}
        </div>
      )}
    </div>
  )
}
