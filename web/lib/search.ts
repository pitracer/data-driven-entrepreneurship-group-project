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

// Keyword fallback when embeddings are unavailable
export function keywordSearch(query: string, firms: { bvd_id: string; company_name: string; snippet?: string | null }[], k = 5): string[] {
  const q = query.toLowerCase()
  return firms
    .filter(f =>
      f.company_name.toLowerCase().includes(q) ||
      (f.snippet ?? "").toLowerCase().includes(q)
    )
    .slice(0, k)
    .map(f => f.bvd_id)
}
