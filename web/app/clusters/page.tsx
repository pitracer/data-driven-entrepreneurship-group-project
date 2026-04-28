"use client"
import { useEffect, useState, useMemo } from "react"
import { getFirms, filterFirms } from "@/lib/data"
import type { Firm } from "@/lib/types"
import PlotlyChart from "@/components/PlotlyChart"
import Sidebar from "@/components/Sidebar"
import { useFilterStore } from "@/lib/store"
import CategoryBadge from "@/components/CategoryBadge"

export default function ClustersPage() {
  const [allFirms, setAllFirms] = useState<Firm[]>([])
  const filters = useFilterStore()
  const firms = useMemo(() => filterFirms(allFirms, filters), [allFirms, filters])

  useEffect(() => { getFirms().then(setAllFirms) }, [])

  const withClusters = firms.filter(f => f.archetype_cluster)

  // Archetype distribution
  const archetypeCounts = useMemo(() => {
    const m: Record<string, number> = {}
    withClusters.forEach(f => { m[f.archetype_cluster!] = (m[f.archetype_cluster!] ?? 0) + 1 })
    return Object.entries(m).sort((a, b) => b[1] - a[1])
  }, [withClusters])

  // Growth cluster distribution
  const growthCounts = useMemo(() => {
    const m: Record<string, number> = {}
    withClusters.forEach(f => { if (f.growth_cluster) m[f.growth_cluster] = (m[f.growth_cluster] ?? 0) + 1 })
    return Object.entries(m).sort((a, b) => b[1] - a[1])
  }, [withClusters])

  // Scatter: scaling_signal_score vs digital_leverage_score (colored by archetype)
  const archetypes = [...new Set(withClusters.map(f => f.archetype_cluster!))]
  const COLORS = ["#1E6FD4", "#FFD700", "#34D399", "#F87171", "#A78BFA"]
  const scatterData = archetypes.map((arch, i) => {
    const sub = withClusters.filter(f => f.archetype_cluster === arch)
    return {
      type: "scatter" as const, mode: "markers" as const, name: arch,
      x: sub.map(f => f.scaling_signal_score ?? 0),
      y: sub.map(f => f.digital_leverage_score ?? 0),
      text: sub.map(f => f.company_name),
      marker: { color: COLORS[i % COLORS.length], size: 6, opacity: 0.7 },
    }
  })

  if (!withClusters.length) {
    return (
      <div className="flex gap-8">
        <Sidebar firms={allFirms} />
        <div className="flex-1">
          <h1 className="text-3xl font-bold mb-4" style={{ fontFamily: "Rajdhani, sans-serif" }}>Business Clusters</h1>
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 text-blue-700">
            Cluster data not yet available. Run <code className="bg-blue-100 px-1 rounded">python -m pipeline.step_07_extract_signals</code> and <code className="bg-blue-100 px-1 rounded">python -m pipeline.step_08_cluster</code> to generate clusters.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-8">
      <Sidebar firms={allFirms} />
      <div className="flex-1 min-w-0">
        <h1 className="text-3xl font-bold mb-1" style={{ fontFamily: "Rajdhani, sans-serif" }}>Business Clusters</h1>
        <p className="text-slate-500 text-sm mb-6">{withClusters.length} firms clustered by archetype and growth strategy</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Archetype Distribution</p>
            <PlotlyChart
              data={[{ type: "bar", orientation: "h", x: archetypeCounts.map(d => d[1]), y: archetypeCounts.map(d => d[0]), marker: { color: "#1E6FD4" } }]}
              layout={{ showlegend: false, xaxis: { title: "Firms" }, yaxis: { automargin: true } }}
              height={280}
            />
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Growth Strategy Distribution</p>
            <PlotlyChart
              data={[{ type: "bar", orientation: "h", x: growthCounts.map(d => d[1]), y: growthCounts.map(d => d[0]), marker: { color: "#FFD700" } }]}
              layout={{ showlegend: false, xaxis: { title: "Firms" }, yaxis: { automargin: true } }}
              height={280}
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 mb-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Scaling Signal vs Digital Leverage</p>
          <PlotlyChart
            data={scatterData}
            layout={{ xaxis: { title: "Scaling signal score (0–3)" }, yaxis: { title: "Digital leverage score (0–3)" }, legend: { orientation: "h", y: 1.1 } }}
            height={380}
          />
        </div>

        {/* Detail table */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 px-4 py-3 border-b border-slate-100">Firm Detail</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
                <tr>
                  {["Company", "Category", "Archetype", "Growth Strategy", "Scale", "Digital", "Growth Evidence"].map(h => (
                    <th key={h} className="px-3 py-2 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {withClusters.slice(0, 100).map((f, i) => (
                  <tr key={f.bvd_id} className={i % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                    <td className="px-3 py-2 font-medium text-slate-800 max-w-[160px] truncate">{f.company_name}</td>
                    <td className="px-3 py-2"><CategoryBadge category={f.category_2024} /></td>
                    <td className="px-3 py-2 text-slate-600">{f.archetype_cluster ?? "—"}</td>
                    <td className="px-3 py-2 text-slate-600">{f.growth_cluster ?? "—"}</td>
                    <td className="px-3 py-2 text-center">{f.scaling_signal_score ?? "—"}</td>
                    <td className="px-3 py-2 text-center">{f.digital_leverage_score ?? "—"}</td>
                    <td className="px-3 py-2 text-slate-500 max-w-[200px] truncate">{f.growth_evidence ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
