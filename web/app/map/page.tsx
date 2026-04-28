"use client"
import { useEffect, useState, useMemo } from "react"
import dynamic from "next/dynamic"
import { getFirms, filterFirms } from "@/lib/data"
import type { Firm } from "@/lib/types"
import { useFilterStore } from "@/lib/store"
import Sidebar from "@/components/Sidebar"
import { CATEGORY_COLORS } from "@/lib/types"

// DeckGL must be client-only
const DeckMap = dynamic(() => import("@/components/DeckMap"), { ssr: false, loading: () => (
  <div className="flex-1 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400">Loading map…</div>
)})

export default function MapPage() {
  const [allFirms, setAllFirms] = useState<Firm[]>([])
  const filters = useFilterStore()

  useEffect(() => { getFirms().then(setAllFirms) }, [])

  const firms = useMemo(() => filterFirms(allFirms, filters), [allFirms, filters])
  const geocoded = firms.filter(f => f.lat != null && f.lon != null)
  const missing = firms.length - geocoded.length

  return (
    <div className="flex gap-8 h-[calc(100vh-120px)]">
      <Sidebar firms={allFirms} />
      <div className="flex-1 flex flex-col min-w-0">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold" style={{ fontFamily: "Rajdhani, sans-serif" }}>Firm Map</h1>
            <p className="text-slate-500 text-sm">{geocoded.length} geocoded · {missing} missing coordinates</p>
          </div>
          {/* Legend */}
          <div className="flex gap-3 text-xs">
            {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
              <div key={cat} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-slate-600">{cat}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex-1 rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
          <DeckMap firms={geocoded} />
        </div>
      </div>
    </div>
  )
}
