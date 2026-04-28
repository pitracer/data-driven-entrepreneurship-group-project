"use client"
import { useEffect, useState, useMemo } from "react"
import { getFirms, filterFirms } from "@/lib/data"
import { useFilterStore } from "@/lib/store"
import type { Firm } from "@/lib/types"
import Sidebar from "@/components/Sidebar"
import FirmCard from "@/components/FirmCard"
import CategoryBadge from "@/components/CategoryBadge"

const COLS: { key: keyof Firm; label: string }[] = [
  { key: "company_name",        label: "Company" },
  { key: "category_2024",       label: "Category" },
  { key: "nace_letter",         label: "Sector" },
  { key: "employees_2024",      label: "Employees" },
  { key: "growth_2024",         label: "Growth %" },
  { key: "orbis_revenue_latest",label: "Revenue" },
]

export default function FirmsPage() {
  const [allFirms, setAllFirms] = useState<Firm[]>([])
  const [selected, setSelected] = useState<Firm | null>(null)
  const [search, setSearch] = useState("")
  const [sortKey, setSortKey] = useState<keyof Firm>("employees_2024")
  const filters = useFilterStore()

  useEffect(() => { getFirms().then(setAllFirms) }, [])

  const filtered = useMemo(() => {
    let firms = filterFirms(allFirms, filters)
    if (search) firms = firms.filter(f => f.company_name.toLowerCase().includes(search.toLowerCase()))
    return [...firms].sort((a, b) => ((b[sortKey] as number) ?? 0) - ((a[sortKey] as number) ?? 0))
  }, [allFirms, filters, search, sortKey])

  return (
    <div className="flex gap-8">
      <Sidebar firms={allFirms} />
      <div className="flex-1 min-w-0">
        <h1 className="text-3xl font-bold mb-1" style={{ fontFamily: "Rajdhani, sans-serif" }}>Firm Explorer</h1>
        <p className="text-slate-500 text-sm mb-6">Search and explore all {allFirms.length.toLocaleString()} firms</p>

        <div className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Search by company name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={sortKey as string}
            onChange={e => setSortKey(e.target.value as keyof Firm)}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="employees_2024">Sort: Employees</option>
            <option value="orbis_revenue_latest">Sort: Revenue</option>
            <option value="growth_2024">Sort: Growth</option>
          </select>
        </div>

        <p className="text-xs text-slate-400 mb-3">{filtered.length.toLocaleString()} firms — click a row for details</p>

        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
                <tr>
                  {COLS.map(c => <th key={c.key} className="px-4 py-2 text-left">{c.label}</th>)}
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 200).map((f, i) => (
                  <tr
                    key={f.bvd_id}
                    className={`cursor-pointer transition-colors ${i % 2 === 0 ? "bg-white" : "bg-slate-50/50"} hover:bg-blue-50`}
                    onClick={() => setSelected(f)}
                  >
                    <td className="px-4 py-2 font-medium text-slate-800 max-w-[220px] truncate">{f.company_name}</td>
                    <td className="px-4 py-2"><CategoryBadge category={f.category_2024} /></td>
                    <td className="px-4 py-2 text-slate-600">{f.nace_letter ?? "—"}</td>
                    <td className="px-4 py-2 text-right">{f.employees_2024?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-2 text-right">{f.growth_2024 != null ? `${f.growth_2024 > 0 ? "+" : ""}${f.growth_2024.toFixed(1)}%` : "—"}</td>
                    <td className="px-4 py-2 text-right">{f.orbis_revenue_latest != null ? `€${(f.orbis_revenue_latest/1000).toFixed(1)}M` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length > 200 && (
            <p className="text-center text-xs text-slate-400 py-2 border-t border-slate-100">
              Showing 200 of {filtered.length} firms — refine filters or search to narrow down
            </p>
          )}
        </div>
      </div>
      {selected && <FirmCard firm={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
