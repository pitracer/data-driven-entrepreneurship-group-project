// Pure JS cosine similarity search over pre-computed embeddings.
// Used by the /api/chat route — no external vector DB needed.

export interface EmbeddingRecord {
  bvd_id: string
  vector: number[]
}

export function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0, normA = 0, normB = 0
  for (let i = 0; i < a.length; i++) {
    dot   += a[i] * b[i]
    normA += a[i] * a[i]
    normB += b[i] * b[i]
  }
  if (normA === 0 || normB === 0) return 0
  return dot / (Math.sqrt(normA) * Math.sqrt(normB))
}

export function findTopK(
  queryVector: number[],
  embeddings: EmbeddingRecord[],
  k = 5
): string[] {
  return embeddings
    .map(e => ({ bvd_id: e.bvd_id, score: cosineSimilarity(queryVector, e.vector) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map(e => e.bvd_id)
}

const STOPWORDS = new Set([
  "about", "after", "also", "and", "are", "ask", "bei", "can", "companies",
  "company", "data", "der", "die", "das", "for", "firm", "firms", "from",
  "give", "has", "have", "how", "into", "mit", "show", "tell", "the",
  "their", "them", "these", "und", "was", "were", "what", "which", "with",
])

const TOKEN_ALIASES: Record<string, string[]> = {
  gazelles: ["gazelle"],
  scalers: ["scaler"],
  scaleups: ["scaler", "growth"],
  healthcare: ["healthcare", "health", "medical", "pharma"],
  health: ["healthcare", "health", "medical", "pharma"],
  hiring: ["hiring", "careers", "jobs", "recruiting"],
  expanding: ["expanding", "expansion", "growth"],
  expansion: ["expanding", "expansion", "growth"],
  digital: ["digital", "platform", "software", "online"],
  native: ["digital", "platform", "software"],
}

interface SearchFirm {
  bvd_id: string
  company_name: string
  employees_2024?: number | null
  category_2024?: string | null
  nace_letter?: string | null
  nace_section?: string | null
  snippet?: string | null
  profile_text?: string | null
  archetype_cluster?: string | null
  growth_cluster?: string | null
  business_model_refined?: string | null
  target_segment?: string | null
  value_proposition_keywords?: string | null
  growth_evidence?: string | null
  scaling_types?: string | null
}

function tokensFor(query: string): string[] {
  const rawTokens = query
    .toLowerCase()
    .split(/[^a-z0-9äöüß]+/i)
    .filter(t => t.length > 2 && !STOPWORDS.has(t))

  return Array.from(new Set(rawTokens.flatMap(t => TOKEN_ALIASES[t] ?? [t])))
}

function searchableText(firm: SearchFirm): string {
  return [
    firm.company_name,
    firm.category_2024,
    firm.nace_letter,
    firm.nace_section,
    firm.snippet,
    firm.profile_text,
    firm.archetype_cluster,
    firm.growth_cluster,
    firm.business_model_refined,
    firm.target_segment,
    firm.value_proposition_keywords,
    firm.growth_evidence,
    firm.scaling_types,
  ].filter(Boolean).join(" ").toLowerCase()
}

// Keyword fallback when embeddings are unavailable
export function keywordSearch(query: string, firms: SearchFirm[], k = 5): string[] {
  const tokens = tokensFor(query)
  if (tokens.length === 0) return []

  return firms
    .map(f => {
      const text = searchableText(f)
      const score = tokens.reduce((sum, token) => {
        if (!text.includes(token)) return sum
        if ((f.company_name ?? "").toLowerCase().includes(token)) return sum + 4
        if ((f.category_2024 ?? "").toLowerCase().includes(token)) return sum + 3
        return sum + 1
      }, 0)
      return { bvd_id: f.bvd_id, score, employees: Number(f.employees_2024 ?? 0) }
    })
    .filter(f => f.score > 0)
    .sort((a, b) => b.score - a.score || b.employees - a.employees)
    .slice(0, k)
    .map(f => f.bvd_id)
}
