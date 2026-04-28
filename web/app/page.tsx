"use client"
import { useEffect, useState } from "react"
import Link from "next/link"
import { getFirms, computeKPIs } from "@/lib/data"
import type { Firm, KPIs } from "@/lib/types"

const NAV_CARDS = [
  { href: "/map",        icon: "📍", title: "Map",        desc: "Geocoded firm locations across Düsseldorf" },
  { href: "/sectors",    icon: "📊", title: "Sectors",    desc: "Growth by NACE sector + AI narratives" },
  { href: "/firms",      icon: "🏢", title: "Firms",      desc: "Search and explore all 1,555 firms" },
  { href: "/leadership", icon: "👔", title: "Leadership", desc: "Management quality and financial health" },
  { href: "/stats",      icon: "📈", title: "Stats",      desc: "Regression analysis of scaling factors" },
  { href: "/clusters",   icon: "🔬", title: "Clusters",   desc: "Business archetypes and growth strategies" },
  { href: "/chat",       icon: "💬", title: "Chat",       desc: "Ask questions about the data" },
]

export default function HomePage() {
  const [kpis, setKpis] = useState<KPIs | null>(null)
  const [catCounts, setCatCounts] = useState<{ Category: string; Firms: number }[]>([])

  useEffect(() => {
    getFirms().then(firms => {
      setKpis(computeKPIs(firms))
      const counts: Record<string, number> = {}
      firms.forEach(f => {
        const c = f.category_2024 ?? "Other"
        counts[c] = (counts[c] ?? 0) + 1
      })
      setCatCounts(Object.entries(counts).map(([Category, Firms]) => ({ Category, Firms }))
        .sort((a, b) => b.Firms - a.Firms))
    })
  }, [])

  return (
    <div>
      {/* Header */}
      <h1 className="text-4xl font-bold text-slate-900 mb-1" style={{ fontFamily: "Rajdhani, sans-serif" }}>
        Düsseldorf&apos;s Hidden Champions
      </h1>
      <p className="text-slate-500 text-base mb-8">
        How unknown mid-sized firms are quietly driving the city&apos;s job growth
      </p>

      {/* KPI row */}
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Key Metrics — 2024</p>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-10">
        {[
          { label: "Total Firms",    value: kpis ? kpis.total_firms.toLocaleString() : "…", sub: "unique BvD IDs" },
          { label: "Gazelles",       value: kpis ? String(kpis.n_gazelles) : "…",           sub: "≥20% growth/year" },
          { label: "Scalers",        value: kpis ? String(kpis.n_scalers) : "…",            sub: "sustained high growth" },
          { label: "Top-10 Job Δ",   value: kpis ? `${kpis.job_change_top10 > 0 ? "+" : ""}${kpis.job_change_top10.toLocaleString()}` : "…", sub: "since earliest baseline" },
          { label: "PhD/Dr Mgmt",    value: kpis ? String(kpis.n_phd_mgmt) : "…",           sub: "firms w/ academic leadership" },
        ].map(k => (
          <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4 text-center shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">{k.label}</p>
            <p className="text-3xl font-bold text-slate-900" style={{ fontFamily: "Rajdhani, sans-serif" }}>{k.value}</p>
            <p className="text-xs text-slate-400 mt-1">{k.sub}</p>
          </div>
        ))}
      </div>

      {/* Category table + nav */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Category Breakdown</p>
          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-2 text-left">Category</th>
                  <th className="px-4 py-2 text-right">Firms</th>
                </tr>
              </thead>
              <tbody>
                {catCounts.map((row, i) => (
                  <tr key={row.Category} className={i % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                    <td className="px-4 py-2 text-slate-700">{row.Category}</td>
                    <td className="px-4 py-2 text-right font-medium text-slate-900">{row.Firms.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Explore</p>
          <div className="grid grid-cols-1 gap-2">
            {NAV_CARDS.map(c => (
              <Link
                key={c.href}
                href={c.href}
                className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50 transition-colors group"
              >
                <span className="text-xl">{c.icon}</span>
                <div>
                  <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-700">{c.title}</p>
                  <p className="text-xs text-slate-500">{c.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
