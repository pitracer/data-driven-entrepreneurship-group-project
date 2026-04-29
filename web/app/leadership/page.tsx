"use client"
import { useEffect, useState, useMemo } from "react"
import { getFirms, filterFirms } from "@/lib/data"
import type { Firm } from "@/lib/types"
import PlotlyChart from "@/components/PlotlyChart"
import Sidebar from "@/components/Sidebar"
import { useFilterStore } from "@/lib/store"

function median(arr: number[]) {
  if (!arr.length) return null
  const s = [...arr].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}
function avg(arr: number[]) {
  return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : null
}

export default function LeadershipPage() {
  const [allFirms, setAllFirms] = useState<Firm[]>([])
  const filters = useFilterStore()
  const firms = useMemo(() => filterFirms(allFirms, filters), [allFirms, filters])

  useEffect(() => { getFirms().then(setAllFirms) }, [])

  // Only use categories that actually exist in the data to avoid null traces breaking Plotly
  const cats = ["Gazelle", "Scaler", "Other"]
  const colors: Record<string, string> = { Gazelle: "#FFD700", Scaler: "#1E6FD4", Other: "#94A3B8" }

  // Single trace (multi-bar) — avoids Plotly null-trace rendering issues
  const ageByCategory = [{
    type: "bar" as const,
    x: cats,
    y: cats.map(cat => {
      const vals = firms.filter(f => f.category_2024 === cat && f.avg_manager_age != null).map(f => f.avg_manager_age!)
      const a = avg(vals)
      return a != null ? Math.round(a) : null
    }),
    marker: { color: cats.map(cat => colors[cat]) },
  }]

  const phdByCategory = [{
    type: "bar" as const,
    x: cats,
    y: cats.map(cat => {
      const sub = firms.filter(f => f.category_2024 === cat)
      // Return null (not 0) when empty — Plotly updates correctly from null→value but not from 0→value
      return sub.length ? Math.round((sub.filter(f => f.has_phd).length / sub.length) * 1000) / 10 : null
    }),
    marker: { color: cats.map(cat => colors[cat]) },
  }]

  const equityData = cats.map(cat => ({
    type: "box" as const,
    name: cat,
    y: firms.filter(f => f.category_2024 === cat && f.orbis_equity_ratio_latest != null).map(f => f.orbis_equity_ratio_latest!),
    marker: { color: colors[cat] },
  }))

  // Academic leadership by sector
  const sectorPhd = useMemo(() => {
    const map: Record<string, { total: number; withPhd: number }> = {}
    firms.forEach(f => {
      const s = f.nace_letter ?? "?"
      if (!map[s]) map[s] = { total: 0, withPhd: 0 }
      map[s].total++
      if (f.has_phd) map[s].withPhd++
    })
    return Object.entries(map)
      .map(([s, d]) => ({ sector: s, pct: d.total > 5 ? (d.withPhd / d.total) * 100 : 0 }))
      .sort((a, b) => b.pct - a.pct)
      .slice(0, 12)
  }, [firms])

  const n_gazelle = firms.filter(f => f.gazelle_2024).length
  const gazelleAge = avg(firms.filter(f => f.gazelle_2024 && f.avg_manager_age != null).map(f => f.avg_manager_age!))
  const otherAge   = avg(firms.filter(f => !f.gazelle_2024 && f.avg_manager_age != null).map(f => f.avg_manager_age!))
  const gazellePhd = n_gazelle ? firms.filter(f => f.gazelle_2024 && f.has_phd).length / n_gazelle * 100 : 0
  const otherPhd   = firms.filter(f => !f.gazelle_2024).length
    ? firms.filter(f => !f.gazelle_2024 && f.has_phd).length / firms.filter(f => !f.gazelle_2024).length * 100 : 0
  const gazelleEq  = median(firms.filter(f => f.gazelle_2024 && f.orbis_equity_ratio_latest != null).map(f => f.orbis_equity_ratio_latest!))
  const scalerEq   = median(firms.filter(f => f.scaler_2024 && f.orbis_equity_ratio_latest != null).map(f => f.orbis_equity_ratio_latest!))
  const nOrbis     = firms.filter(f => f.orbis_revenue_latest != null).length

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-8">
      <Sidebar firms={allFirms} />
      <div className="flex-1 min-w-0">
        <h1 className="text-3xl font-bold mb-1" style={{ fontFamily: "Rajdhani, sans-serif" }}>Leadership Profile</h1>
        <p className="text-slate-500 text-sm mb-6">Management quality and financial health by firm category</p>

        {/* KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 mb-8">
          {[
            { label: "Gazelle Mgmt Age", value: gazelleAge ? gazelleAge.toFixed(1) : "—", sub: `vs ${otherAge ? otherAge.toFixed(1) : "—"} other firms` },
            { label: "PhD in Gazelles",  value: `${gazellePhd.toFixed(1)}%`, sub: `vs ${otherPhd.toFixed(1)}% other firms` },
            { label: "Gazelle Equity",   value: gazelleEq ? `${gazelleEq.toFixed(1)}%` : "—", sub: `vs ${scalerEq ? scalerEq.toFixed(1) + "% scalers" : "—"}` },
            { label: "Orbis Coverage",   value: nOrbis.toLocaleString(), sub: "firms with financial data" },
          ].map(k => (
            <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">{k.label}</p>
              <p className="text-2xl font-bold text-slate-900" style={{ fontFamily: "Rajdhani, sans-serif" }}>{k.value}</p>
              <p className="text-xs text-slate-400 mt-1">{k.sub}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Avg Manager Age by Category</p>
            <PlotlyChart data={ageByCategory} layout={{ showlegend: false, yaxis: { title: "Age (years)", tickformat: ".0f", rangemode: "tozero" } }} height={280} />
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">PhD / Dr Leadership Rate (%)</p>
            <PlotlyChart data={phdByCategory} layout={{ showlegend: false, yaxis: { title: "% of firms", tickformat: ".1f", rangemode: "tozero" } }} height={280} />
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Equity Ratio by Category</p>
            <PlotlyChart data={equityData} layout={{ showlegend: false, yaxis: { title: "Equity ratio (%)", tickformat: ".1f", hoverformat: ".1f" } }} height={280} />
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Academic Leadership by Sector (top 12)</p>
            <PlotlyChart
              data={[{ type: "bar", orientation: "h", x: sectorPhd.map(d => d.pct), y: sectorPhd.map(d => d.sector), marker: { color: "#1E6FD4" } }]}
              layout={{ showlegend: false, xaxis: { title: "% with PhD/Dr" }, yaxis: { automargin: true } }}
              height={280}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
