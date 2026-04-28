import type { Firm, KPIs, SectorNarrative } from "./types"

// In Next.js App Router, fetch from /public at build-time or client-side
// We export simple loaders that work both server and client side.

let _firms: Firm[] | null = null
let _narratives: Record<string, SectorNarrative> | null = null

export async function getFirms(): Promise<Firm[]> {
  if (_firms) return _firms
  const res = await fetch("/data/firms.json")
  _firms = await res.json()
  return _firms!
}

export async function getSectorNarratives(): Promise<Record<string, SectorNarrative>> {
  if (_narratives) return _narratives
  const res = await fetch("/data/sector_narratives.json")
  _narratives = await res.json()
  return _narratives!
}

export function computeKPIs(firms: Firm[]): KPIs {
  const n_gazelles = firms.filter(f => f.gazelle_2024).length
  const n_scalers  = firms.filter(f => f.scaler_2024).length
  const n_sectors  = new Set(firms.map(f => f.nace_letter).filter(Boolean)).size
  const n_phd_mgmt = firms.filter(f => f.has_phd).length

  const top10 = [...firms]
    .filter(f => f.employees_2024 != null)
    .sort((a, b) => (b.employees_2024 ?? 0) - (a.employees_2024 ?? 0))
    .slice(0, 10)
  const job_change_top10 = top10.reduce((sum, f) => sum + (f.employee_change_abs ?? 0), 0)

  return { total_firms: firms.length, n_gazelles, n_scalers, job_change_top10, n_phd_mgmt, n_sectors }
}

export function filterFirms(
  firms: Firm[],
  {
    categories,
    sectors,
    minEmployees,
    priorityOnly,
  }: {
    categories: string[]
    sectors: string[]
    minEmployees: number
    priorityOnly: boolean
  }
): Firm[] {
  return firms.filter(f => {
    if (categories.length > 0 && !categories.includes(f.category_2024 ?? "Other")) return false
    if (sectors.length > 0 && !sectors.includes(f.nace_letter ?? "")) return false
    if ((f.employees_2024 ?? 0) < minEmployees) return false
    if (priorityOnly && !f.priority_enrich) return false
    return true
  })
}
