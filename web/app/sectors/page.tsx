"use client"
import { useEffect, useState, useMemo } from "react"
import { getFirms, getSectorNarratives } from "@/lib/data"
import type { Firm } from "@/lib/types"
import PlotlyChart from "@/components/PlotlyChart"
import Sidebar from "@/components/Sidebar"
import { useFilterStore } from "@/lib/store"
import { filterFirms } from "@/lib/data"

type RawSectorNarrative = string | {
  sector_name?: string
  name?: string
  narrative?: string
  text?: string
  n_gazelles?: number
  n_scalers?: number
}

export default function SectorsPage() {
  const [allFirms, setAllFirms] = useState<Firm[]>([])
  const [narratives, setNarratives] = useState<Record<string, RawSectorNarrative>>({})
  const filters = useFilterStore()

  useEffect(() => {
    getFirms().then(setAllFirms)
    getSectorNarratives().then(setNarratives)
  }, [])

  const firms = useMemo(() => filterFirms(allFirms, filters), [allFirms, filters])

  // Sector aggregation
  const sectorData = useMemo(() => {
    const map: Record<string, { n_gazelles: number; n_scalers: number; employees: number[] }> = {}
    firms.forEach(f => {
      const s = f.nace_letter ?? "?"
      if (!map[s]) map[s] = { n_gazelles: 0, n_scalers: 0, employees: [] }
      if (f.gazelle_2024) map[s].n_gazelles++
      if (f.scaler_2024)  map[s].n_scalers++
      if (f.employees_2024 != null) map[s].employees.push(f.employees_2024)
    })
    return Object.entries(map)
      .map(([letter, d]) => ({ letter, ...d, total: d.n_gazelles + d.n_scalers }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 15)
  }, [firms])

  const sectorCounts = useMemo(() => {
    const map: Record<string, { n_gazelles: number; n_scalers: number; sector_name: string }> = {}
    firms.forEach(f => {
      const s = f.nace_letter ?? "?"
      if (!map[s]) map[s] = { n_gazelles: 0, n_scalers: 0, sector_name: f.nace_section ?? "" }
      if (f.gazelle_2024) map[s].n_gazelles++
      if (f.scaler_2024) map[s].n_scalers++
      if (!map[s].sector_name && f.nace_section) map[s].sector_name = f.nace_section
    })
    return map
  }, [firms])

  // Employee trend data (top 3 sectors by total employees 2024)
  const trendData = useMemo(() => {
    const totals: Record<string, number> = {}
    firms.forEach(f => {
      const s = f.nace_letter ?? "?"
      totals[s] = (totals[s] ?? 0) + (f.employees_2024 ?? 0)
    })
    const top3 = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([s]) => s)
    const years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    return top3.map(sector => {
      const sectorFirms = firms.filter(f => f.nace_letter === sector)
      return {
        sector,
        x: years,
        y: years.map(yr => sectorFirms.reduce((s, f) => s + ((f[`employees_${yr}` as keyof Firm] as number) ?? 0), 0)),
      }
    })
  }, [firms])

  const COLORS = ["#1E6FD4", "#FFD700", "#64B5F6", "#34D399", "#F87171"]

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-8">
      <Sidebar firms={allFirms} />
      <div className="flex-1 min-w-0">
        <h1 className="text-3xl font-bold mb-1" style={{ fontFamily: "Rajdhani, sans-serif" }}>Sector Analysis</h1>
        <p className="text-slate-500 text-sm mb-6">Growth firms and employment trends by NACE sector</p>

        {/* Gazelles & Scalers by sector */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 mb-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Gazelles & Scalers by NACE Sector (top 15)</p>
          <PlotlyChart
            data={[
              { type: "bar", orientation: "h", name: "Gazelles", x: sectorData.map(d => d.n_gazelles), y: sectorData.map(d => d.letter), marker: { color: "#FFD700" } },
              { type: "bar", orientation: "h", name: "Scalers",  x: sectorData.map(d => d.n_scalers),  y: sectorData.map(d => d.letter), marker: { color: "#1E6FD4" } },
            ]}
            layout={{ barmode: "stack", yaxis: { automargin: true }, xaxis: { title: "Number of firms" }, legend: { orientation: "h", y: 1.1 } }}
            height={400}
          />
        </div>

        {/* Employee trend */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 mb-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Employee Trend 2017–2024 (top 3 sectors by size)</p>
          <PlotlyChart
            data={trendData.map((d, i) => ({
              type: "scatter", mode: "lines+markers",
              name: `Sector ${d.sector}`, x: d.x, y: d.y,
              line: { color: COLORS[i], width: 2 },
            }))}
            layout={{ yaxis: { title: "Total employees" }, legend: { orientation: "h", y: 1.1 } }}
          />
        </div>

        {/* Sector narratives */}
        {Object.keys(narratives).length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">AI Sector Intelligence</p>
            <div className="space-y-3">
              {Object.entries(narratives).map(([letter, n]) => {
                const meta = sectorCounts[letter]
                const sectorName = typeof n === "string" ? meta?.sector_name : (n.sector_name ?? n.name ?? meta?.sector_name)
                const narrative = typeof n === "string" ? n : (n.narrative ?? n.text ?? "No narrative available.")
                const nGazelles = typeof n === "string" ? meta?.n_gazelles : (n.n_gazelles ?? meta?.n_gazelles)
                const nScalers = typeof n === "string" ? meta?.n_scalers : (n.n_scalers ?? meta?.n_scalers)

                return (
                  <details key={letter} className="border border-slate-200 rounded-xl overflow-hidden">
                    <summary className="px-4 py-3 bg-slate-50 cursor-pointer text-sm font-medium text-slate-700 flex justify-between items-center gap-4">
                      <span>Sector {letter}{sectorName ? ` — ${sectorName}` : ""}</span>
                      <span className="text-xs text-slate-400 whitespace-nowrap">{nGazelles ?? 0} Gazelles · {nScalers ?? 0} Scalers</span>
                    </summary>
                    <div className="px-4 py-3 border-l-4 border-blue-500 bg-blue-50/50 text-sm text-slate-700">
                      {narrative}
                    </div>
                  </details>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
