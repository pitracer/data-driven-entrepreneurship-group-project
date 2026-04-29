import { NextRequest, NextResponse } from "next/server"
import Groq from "groq-sdk"
import { readFileSync } from "fs"
import { join } from "path"
import type { Firm } from "@/lib/types"
import type { EmbeddingRecord } from "@/lib/search"
import { keywordSearch } from "@/lib/search"

// Load static data at module level (cached between invocations on warm lambda)
let _firms: Firm[] | null = null
let _embeddings: EmbeddingRecord[] | null = null

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

interface ChatRequest {
  messages?: ChatMessage[]
  apiKey?: string
  query?: string
}

function loadFirms() {
  if (!_firms) {
    const p = join(process.cwd(), "public", "data", "firms.json")
    _firms = JSON.parse(readFileSync(p, "utf-8"))
  }
  return _firms!
}

function loadEmbeddings(): EmbeddingRecord[] | null {
  if (_embeddings) return _embeddings
  try {
    const p = join(process.cwd(), "public", "data", "embeddings.json")
    _embeddings = JSON.parse(readFileSync(p, "utf-8"))
    return _embeddings!
  } catch {
    return null
  }
}

function buildContext(firms: Firm[]): string {
  return firms.map(f => {
    const parts = [
      `**${f.company_name}** (${f.category_2024 ?? "Other"}, NACE ${f.nace_letter ?? "?"})`,
      f.employees_2024 ? `Employees 2024: ${f.employees_2024.toLocaleString()}` : null,
      f.growth_2024 != null ? `Growth: ${f.growth_2024 > 0 ? "+" : ""}${f.growth_2024.toFixed(1)}%` : null,
      f.snippet ?? f.profile_text ?? null,
      f.archetype_cluster ? `Archetype: ${f.archetype_cluster}` : null,
      f.growth_cluster ? `Growth strategy: ${f.growth_cluster}` : null,
      f.growth_evidence ?? null,
      f.website ? `Website: ${f.website}` : null,
    ]
    return parts.filter(Boolean).join(" | ")
  }).join("\n")
}

function buildDatasetSummary(firms: Firm[]): string {
  const gazelles = firms.filter(f => f.gazelle_2024).length
  const scalers = firms.filter(f => f.scaler_2024).length
  const sectors = new Set(firms.map(f => f.nace_letter).filter(Boolean)).size
  const geocoded = firms.filter(f => f.lat != null && f.lon != null).length

  return [
    `Dataset: ${firms.length.toLocaleString()} Düsseldorf firms`,
    `${gazelles} Gazelles`,
    `${scalers} Scalers`,
    `${sectors} NACE sectors`,
    `${geocoded.toLocaleString()} firms with map coordinates`,
  ].join(" | ")
}

const SYSTEM_PROMPT = `You are a business analyst specializing in the Düsseldorf startup and SME ecosystem.
You have summary statistics on all 1,555 firms in Düsseldorf, Germany — including Gazelles (≥20% annual growth),
Scalers (sustained high growth), and other categories.
For each question, the most relevant firms are retrieved and shown to you as context.
Use them specifically and cite company names when answering.
If the retrieved context doesn't cover the question well, say so honestly.
Keep answers concise (3–6 sentences) unless asked for more detail.`

export async function POST(req: NextRequest) {
  try {
    const { messages = [], apiKey, query } = await req.json() as ChatRequest

    if (!apiKey) {
      return NextResponse.json({ error: "Groq API key required" }, { status: 401 })
    }

    const firms = loadFirms()
    const embeddings = loadEmbeddings()

    // Get the latest user message for retrieval
    const userQuery = query ?? messages.findLast((m) => m.role === "user")?.content ?? ""

    // Retrieve relevant firms — use embeddings if available, keyword search as fallback
    let topBvdIds = keywordSearch(userQuery, firms, 20)
    if (embeddings && embeddings.length > 0 && topBvdIds.length === 0) {
      topBvdIds = firms.filter(f => f.priority_enrich).slice(0, 12).map(f => f.bvd_id)
    }

    const topFirms = topBvdIds
      .map((id: string) => firms.find(f => f.bvd_id === id))
      .filter((firm): firm is Firm => Boolean(firm))
    const context = [
      buildDatasetSummary(firms),
      "Relevant firms:",
      buildContext(topFirms) || "No firm-level matches found for this query.",
    ].join("\n")

    const groq = new Groq({ apiKey })

    const chatMessages = [
      { role: "system" as const, content: SYSTEM_PROMPT },
      { role: "user" as const, content: `Context — relevant firms:\n${context}` },
      ...messages.map(m => ({ role: m.role, content: m.content })),
    ]

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: chatMessages,
      temperature: 0.3,
      max_tokens: 600,
    })

    const answer = completion.choices[0].message.content ?? ""

    const sources = topFirms.map(f => ({
      bvd_id: f.bvd_id,
      company_name: f.company_name,
      category_2024: f.category_2024,
      snippet: f.snippet ?? f.profile_text,
    }))

    return NextResponse.json({ answer, sources })
  } catch (err: unknown) {
    console.error("[api/chat]", err)
    const message = err instanceof Error ? err.message : "Unknown error"
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
