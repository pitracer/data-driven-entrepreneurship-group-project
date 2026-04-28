export interface Firm {
  bvd_id: string
  company_name: string
  nace_code: string | null
  nace_section: string | null
  nace_letter: string | null
  founded_year: number | null
  incorporation_year: number | null

  // Classification
  category_2024: "Gazelle" | "Scaler" | "HighGrowth" | "Mature" | "Other" | null
  priority_enrich: boolean
  gazelle_2024: boolean | null
  scaler_2024: boolean | null
  high_growth_2024: boolean | null

  // Employees
  employees_2017: number | null
  employees_2018: number | null
  employees_2019: number | null
  employees_2020: number | null
  employees_2021: number | null
  employees_2022: number | null
  employees_2023: number | null
  employees_2024: number | null
  employee_change_abs: number | null
  employee_change_pct: number | null

  // Growth
  growth_2018: number | null
  growth_2019: number | null
  growth_2020: number | null
  growth_2021: number | null
  growth_2022: number | null
  growth_2023: number | null
  growth_2024: number | null
  aagr_2023: number | null
  aagr_2024: number | null

  // Web enrichment
  website: string | null
  orbis_website: string | null
  address: string | null
  snippet: string | null
  profile_text: string | null
  lat: number | null
  lon: number | null

  // Orbis financial
  orbis_revenue_latest: number | null
  orbis_profit_latest: number | null
  orbis_equity_ratio_latest: number | null
  orbis_street: string | null
  orbis_postcode: string | null
  orbis_city: string | null

  // Management
  n_managers: number | null
  has_phd: boolean | null
  has_professor: boolean | null
  n_doctors: number | null
  mgmt_education_score: string | null
  avg_manager_age: number | null
  pct_university_educated: number | null

  // Signal clusters
  archetype_cluster: string | null
  growth_cluster: string | null
  business_model_refined: string | null
  target_segment: string | null
  value_proposition_keywords: string | null
  scaling_signal_score: number | null
  scaling_types: string | null
  growth_evidence: string | null
  digital_leverage_score: number | null
  has_careers: boolean | null
  has_content_engine: boolean | null
  has_product_platform: boolean | null
}

export interface SectorNarrative {
  sector_letter: string
  sector_name: string
  narrative: string
  n_gazelles: number
  n_scalers: number
  avg_growth: number
}

export interface KPIs {
  total_firms: number
  n_gazelles: number
  n_scalers: number
  job_change_top10: number
  n_phd_mgmt: number
  n_sectors: number
}

export const CATEGORY_COLORS: Record<string, string> = {
  Gazelle:    "#FFD700",
  Scaler:     "#1E6FD4",
  HighGrowth: "#64B5F6",
  Mature:     "#78909C",
  Other:      "#94A3B8",
}

export const CATEGORY_BG: Record<string, string> = {
  Gazelle:    "bg-amber-100 text-amber-800",
  Scaler:     "bg-blue-100 text-blue-800",
  HighGrowth: "bg-sky-100 text-sky-800",
  Mature:     "bg-slate-100 text-slate-700",
  Other:      "bg-gray-100 text-gray-600",
}
