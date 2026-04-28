"use client"
import type { Firm } from "@/lib/types"
import CategoryBadge from "./CategoryBadge"

interface Props {
  firm: Firm
  onClose: () => void
}

function fmt(n: number | null, unit = "") {
  if (n == null) return "—"
  return `${n.toLocaleString("de-DE")}${unit}`
}
function fmtM(n: number | null) {
  if (n == null) return "—"
  return `€${(n / 1000).toFixed(1)}M`
}

export default function FirmCard({ firm, onClose }: Props) {
  const website = firm.website || firm.orbis_website
  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto p-6"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900" style={{ fontFamily: "Rajdhani, sans-serif" }}>
              {firm.company_name}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <CategoryBadge category={firm.category_2024} />
              {firm.nace_letter && (
                <span className="text-xs text-slate-500">NACE {firm.nace_letter} · {firm.nace_section}</span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-2xl leading-none">×</button>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Employees 2024</p>
            <p className="text-xl font-bold text-slate-900">{fmt(firm.employees_2024)}</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Growth 2024</p>
            <p className="text-xl font-bold text-slate-900">
              {firm.growth_2024 != null ? `${firm.growth_2024 > 0 ? "+" : ""}${firm.growth_2024.toFixed(1)}%` : "—"}
            </p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Founded</p>
            <p className="text-xl font-bold text-slate-900">{firm.founded_year ?? "—"}</p>
          </div>
        </div>

        {/* Snippet / Profile */}
        {(firm.profile_text || firm.snippet) && (
          <div className="border-l-4 border-blue-500 bg-blue-50 rounded-r-lg p-3 mb-4">
            <p className="text-sm text-slate-700">{firm.profile_text || firm.snippet}</p>
          </div>
        )}

        {/* Financials */}
        {(firm.orbis_revenue_latest || firm.orbis_profit_latest) && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Financials</p>
            <div className="flex gap-4 text-sm">
              <span className="text-slate-600">Revenue: <strong>{fmtM(firm.orbis_revenue_latest)}</strong></span>
              <span className="text-slate-600">Profit: <strong>{fmtM(firm.orbis_profit_latest)}</strong></span>
              {firm.orbis_equity_ratio_latest != null && (
                <span className="text-slate-600">Equity ratio: <strong>{firm.orbis_equity_ratio_latest.toFixed(1)}%</strong></span>
              )}
            </div>
          </div>
        )}

        {/* Management */}
        {(firm.has_phd || firm.n_doctors) && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Management</p>
            <div className="flex gap-2 flex-wrap text-xs">
              {firm.has_phd && <span className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded">Has PhD/Dr</span>}
              {firm.has_professor && <span className="bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">Has Professor</span>}
              {firm.n_doctors != null && <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded">{firm.n_doctors} doctors</span>}
              {firm.avg_manager_age != null && <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded">Avg age {firm.avg_manager_age.toFixed(0)}</span>}
            </div>
          </div>
        )}

        {/* Archetype */}
        {(firm.archetype_cluster || firm.growth_cluster) && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Business signals</p>
            <div className="flex gap-2 flex-wrap text-xs">
              {firm.archetype_cluster && <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">{firm.archetype_cluster}</span>}
              {firm.growth_cluster && <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded">{firm.growth_cluster}</span>}
            </div>
            {firm.growth_evidence && <p className="text-xs text-slate-500 mt-1">{firm.growth_evidence}</p>}
          </div>
        )}

        {/* Website */}
        {website && (
          <a
            href={website.startsWith("http") ? website : `https://${website}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            {website.replace(/^https?:\/\//, "")} ↗
          </a>
        )}
      </div>
    </div>
  )
}
