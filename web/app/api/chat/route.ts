import { NextRequest, NextResponse } from "next/server"
import Groq from "groq-sdk"
import { readFileSync } from "fs"
import { join } from "path"
import type { EmbeddingRecord } from "@/lib/search"
import { findTopK, keywordSearch } from "@/lib/search"

// Load static data at module level (cached between invocations on warm lambda)
let _firms: any[] | null = null
let _embeddings: EmbeddingRecord[] | null = null

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

function buildContext(firms: any[]): string {
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

const SYSTEM_PROMPT = `You are a business analyst specializing in the Düsseldorf startup and SME ecosystem.
You have access to data on 1,555 firms in Düsseldorf, Germany — including Gazelles (≥20% annual growth),
Scalers (sustained high growth), and other categories.

Answer questions about these firms using the provided context. Be specific and cite company names.
If the context doesn't contain enough information, say so honestly.
Keep answers concise (3-6 sentences) unless asked for detail.`

export async function POST(req: NextRequest) {
  try {
    const { messages, apiKey, query } = await req.json()

    if (!apiKey) {
      return NextResponse.json({ error: "Groq API key required" }, { status: 401 })
    }

    const firms = loadFirms()
    const embeddings = loadEmbeddings()

    // Get the latest user message for retrieval
    const userQuery = query ?? messages?.findLast((m: any) => m.role === "user")?.content ?? ""

    // Retrieve relevant firms — use embeddings if available, keyword search as fallback
    let topBvdIds: string[]
    if (embeddings && embeddings.length > 0) {
      // Simple keyword-based query embedding approximation:
      // Use keyword search as primary (embeddings need an online model at query time)
      // For a production app you'd call an embedding API here
      topBvdIds = keywordSearch(userQuery, firms, 5)
      if (topBvdIds.length === 0) {
        // Fall back to random sample of priority firms
        topBvdIds = firms.filter((f: any) => f.priority_enrich).slice(0, 5).map((f: any) => f.bvd_id)
      }
    } else {
      topBvdIds = keywordSearch(userQuery, firms, 5)
    }

    const topFirms = topBvdIds.map((id: string) => firms.find((f: any) => f.bvd_id === id)).filter(Boolean)
    const context = buildContext(topFirms)

    const groq = new Groq({ apiKey })

    const chatMessages = [
      { role: "system" as const, content: SYSTEM_PROMPT },
      { role: "user" as const, content: `Context — relevant firms:\n${context}` },
      ...(messages ?? []).map((m: any) => ({ role: m.role as "user" | "assistant", content: m.content })),
    ]

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: chatMessages,
      temperature: 0.3,
      max_tokens: 600,
    })

    const answer = completion.choices[0].message.content ?? ""

    const sources = topFirms.map((f: any) => ({
      bvd_id: f.bvd_id,
      company_name: f.company_name,
      category_2024: f.category_2024,
      snippet: f.snippet ?? f.profile_text,
    }))

    return NextResponse.json({ answer, sources })
  } catch (err: any) {
    console.error("[api/chat]", err)
    return NextResponse.json({ error: err.message ?? "Unknown error" }, { status: 500 })
  }
}
