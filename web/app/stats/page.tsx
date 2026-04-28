"use client"
import { useEffect, useState } from "react"
import PlotlyChart from "@/components/PlotlyChart"

interface StatsResult {
  n_firms: number
  n_growth: number
  pseudo_r2: number
  log_likelihood: number
  aic: number
  coefficients: { feature: string; label: string; coef: number; odds_ratio: number; p_value: number; significant: boolean }[]
  correlation_matrix: { labels: string[]; values: number[][] }
  mann_whitney: Record<string, number>
}

export default function StatsPage() {
  const [stats, setStats] = useState<{ without_equity: StatsResult; with_equity: StatsResult } | null>(null)
  const [useEquity, setUseEquity] = useState(false)

  useEffect(() => {
    fetch("/data/stats.json").then(r => r.json()).then(setStats)
  }, [])

  const result = stats ? (useEquity ? stats.with_equity : stats.without_equity) : null

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-1" style={{ fontFamily: "Rajdhani, sans-serif" }}>What Makes a Firm Scale?</h1>
      <p className="text-slate-500 text-sm mb-6">
        Logistic regression and correlation analysis identifying which structural factors
        predict whether a Düsseldorf firm becomes a Gazelle or Scaler.
      </p>

      {!result ? (
        <div className="bg-slate-50 rounded-xl p-8 text-slate-500 text-center">Loading stats…</div>
      ) : (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: "Growth firms (target=1)", value: result.n_growth, sub: `${(result.n_growth / result.n_firms * 100).toFixed(1)}% of sample` },
              { label: "Non-growth firms (target=0)", value: result.n_firms - result.n_growth, sub: "" },
              { label: "Sample size", value: result.n_firms.toLocaleString(), sub: "firms with complete data" },
            ].map(k => (
              <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4 text-center shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">{k.label}</p>
                <p className="text-2xl font-bold text-slate-900" style={{ fontFamily: "Rajdhani, sans-serif" }}>{k.value.toLocaleString()}</p>
                {k.sub && <p className="text-xs text-slate-400 mt-1">{k.sub}</p>}
              </div>
            ))}
          </div>

          {/* Equity toggle */}
          <label className="flex items-center gap-2 mb-6 text-sm text-slate-700 cursor-pointer">
            <input type="checkbox" checked={useEquity} onChange={e => setUseEquity(e.target.checked)} className="accent-blue-600" />
            Include equity ratio (reduces sample to ~{stats?.with_equity.n_firms} firms)
          </label>

          {/* Model label */}
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">
            Logistic Regression — Regression sample: {result.n_firms.toLocaleString()} firms
          </p>

          {/* Results table */}
          <div className="border border-slate-200 rounded-xl overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
                <tr>
                  {["Feature", "Coef (std)", "Odds Ratio", "p-value"].map(h => (
                    <th key={h} className="px-4 py-2 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.coefficients.map((row, i) => (
                  <tr key={row.feature} className={`${row.significant ? "bg-amber-50" : i % 2 === 0 ? "bg-white" : "bg-slate-50/50"}`}>
                    <td className="px-4 py-2 font-medium text-slate-800">
                      {row.label}
                      {row.significant && <span className="ml-2 text-amber-600 text-xs">★</span>}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">{row.coef.toFixed(3)}</td>
                    <td className="px-4 py-2 text-right font-mono">{row.odds_ratio.toFixed(3)}</td>
                    <td className="px-4 py-2 text-right font-mono">{row.p_value.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Coefficient plot */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 mb-6">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Feature Importance (Standardised Coefficients)</p>
            <PlotlyChart
              data={[{
                type: "bar", orientation: "h",
                x: [...result.coefficients].sort((a, b) => a.coef - b.coef).map(r => r.coef),
                y: [...result.coefficients].sort((a, b) => a.coef - b.coef).map(r => r.label),
                marker: { color: [...result.coefficients].sort((a, b) => a.coef - b.coef).map(r => r.significant ? "#FFB300" : "#1E6FD4") },
              }]}
              layout={{ yaxis: { automargin: true }, xaxis: { title: "Standardised coefficient" }, showlegend: false }}
              height={300}
            />
          </div>

          {/* Significant findings */}
          {result.coefficients.some(r => r.significant) && (
            <div className="border-l-4 border-blue-500 bg-blue-50 rounded-r-xl p-4 mb-6">
              <p className="font-semibold text-slate-800 mb-2">Significant factors:</p>
              {result.coefficients.filter(r => r.significant).map(r => (
                <p key={r.feature} className="text-sm text-slate-700">
                  <strong>{r.label}</strong>{" "}
                  {r.coef > 0
                    ? `increases scaling odds by ${((r.odds_ratio - 1) * 100).toFixed(0)}%`
                    : `decreases scaling odds`}
                  {" "}(p={r.p_value.toFixed(3)})
                </p>
              ))}
            </div>
          )}

          <p className="text-xs text-slate-400 mb-8">
            Pseudo R²: {result.pseudo_r2.toFixed(3)} · Log-likelihood: {result.log_likelihood.toFixed(1)} · AIC: {result.aic.toFixed(1)} · n={result.n_firms.toLocaleString()}
          </p>

          {/* Correlation heatmap */}
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Feature Correlation Matrix</p>
            <PlotlyChart
              data={[{
                type: "heatmap",
                z: result.correlation_matrix.values,
                x: result.correlation_matrix.labels,
                y: result.correlation_matrix.labels,
                colorscale: [[0, "#1E3A5F"], [0.5, "#E2E8F0"], [1, "#FFB300"]],
                zmin: -1, zmax: 1,
                text: result.correlation_matrix.values.map(row => row.map(v => v.toFixed(2))),
                texttemplate: "%{text}",
              }]}
              layout={{ height: 420 }}
            />
          </div>
        </>
      )}
    </div>
  )
}
