"use client"
import { useFilterStore } from "@/lib/store"
import type { Firm } from "@/lib/types"

const CATEGORIES = ["Gazelle", "Scaler", "HighGrowth", "Mature", "Other"]

interface Props {
  firms: Firm[]
}

export default function Sidebar({ firms }: Props) {
  const { categories, sectors, minEmployees, priorityOnly,
          setCategories, setSectors, setMinEmployees, setPriorityOnly, reset } = useFilterStore()

  const allSectors = Array.from(new Set(firms.map(f => f.nace_letter).filter(Boolean))).sort() as string[]

  function toggleCat(cat: string) {
    setCategories(categories.includes(cat) ? categories.filter(c => c !== cat) : [...categories, cat])
  }
  function toggleSector(s: string) {
    setSectors(sectors.includes(s) ? sectors.filter(x => x !== s) : [...sectors, s])
  }

  const hasFilters = categories.length > 0 || sectors.length > 0 || minEmployees > 0 || priorityOnly

  return (
    <aside className="w-full lg:w-56 flex-shrink-0">
      <div className="lg:sticky lg:top-20 space-y-4 lg:space-y-6 border border-slate-200 rounded-xl p-3 lg:border-0 lg:rounded-none lg:p-0 bg-white">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Filters</span>
          {hasFilters && (
            <button onClick={reset} className="text-xs text-blue-600 hover:underline">Reset</button>
          )}
        </div>

        {/* Category */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Category</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:block">
            {CATEGORIES.map(cat => (
              <label key={cat} className="flex items-center gap-2 py-0.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={categories.includes(cat)}
                  onChange={() => toggleCat(cat)}
                  className="accent-blue-600"
                />
                <span className="text-sm text-slate-700">{cat}</span>
              </label>
            ))}
          </div>
        </div>

        {/* NACE Sector */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">NACE Sector</p>
          <div className="max-h-28 sm:max-h-36 lg:max-h-48 overflow-y-auto grid grid-cols-2 sm:grid-cols-3 lg:block gap-x-3 space-y-0.5 pr-1">
            {allSectors.map(s => (
              <label key={s} className="flex items-center gap-2 py-0.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sectors.includes(s)}
                  onChange={() => toggleSector(s)}
                  className="accent-blue-600"
                />
                <span className="text-sm text-slate-700">{s}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Min Employees */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Min employees: <span className="text-slate-900">{minEmployees}</span>
          </p>
          <input
            type="range" min={0} max={500} step={10}
            value={minEmployees}
            onChange={e => setMinEmployees(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
        </div>

        {/* Priority only */}
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={priorityOnly}
            onChange={e => setPriorityOnly(e.target.checked)}
            className="accent-blue-600"
          />
          <span className="text-sm text-slate-700">Priority firms only</span>
        </label>
      </div>
    </aside>
  )
}
