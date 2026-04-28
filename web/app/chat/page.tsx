"use client"
import { useEffect, useRef, useState } from "react"
import CategoryBadge from "@/components/CategoryBadge"

interface Message { role: "user" | "assistant"; content: string }
interface Source { bvd_id: string; company_name: string; category_2024: string | null; snippet: string | null }

const SUGGESTIONS = [
  "Which Gazelles are in the healthcare sector?",
  "Which firms are hiring and expanding?",
  "What are the digital-native companies?",
  "Tell me about high-growth IT firms",
]

export default function ChatPage() {
  const [apiKey, setApiKey] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  async function send(text: string) {
    if (!text.trim() || !apiKey) return
    const userMsg: Message = { role: "user", content: text }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setLoading(true)

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...messages, userMsg], apiKey }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }])
      setSources(data.sources ?? [])
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Error — check your Groq API key and try again." }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-8 lg:h-[calc(100vh-120px)]">
      {/* Sidebar */}
      <aside className="w-full lg:w-56 flex-shrink-0 space-y-4 border border-slate-200 rounded-xl p-3 lg:border-0 lg:rounded-none lg:p-0">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Groq API Key</p>
          <input
            type="password"
            placeholder="gsk_..."
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-slate-400 mt-1">Get a free key at console.groq.com</p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Suggested questions</p>
          <div className="grid sm:grid-cols-2 lg:block gap-1">
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                onClick={() => send(s)}
                disabled={!apiKey}
                className="w-full text-left text-xs text-slate-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg px-2 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {sources.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Sources</p>
            <div className="space-y-2">
              {sources.map(s => (
                <div key={s.bvd_id} className="border border-slate-200 rounded-lg p-2">
                  <p className="text-xs font-medium text-slate-800">{s.company_name}</p>
                  <CategoryBadge category={s.category_2024} />
                  {s.snippet && <p className="text-xs text-slate-500 mt-1 line-clamp-2">{s.snippet}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>

      {/* Chat */}
      <div className="flex-1 flex flex-col min-w-0 min-h-[520px]">
        <div className="flex-1 overflow-y-auto space-y-4 pb-4">
          {messages.length === 0 && (
            <div className="text-center py-16 text-slate-400">
              <p className="text-5xl mb-4">💬</p>
              <p className="text-lg font-medium">Ask about Düsseldorf&apos;s hidden champions</p>
              <p className="text-sm mt-1">Enter your Groq API key and start asking</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[88%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm
                  ${m.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-800 border border-slate-200"
                  }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl px-4 py-3 text-sm text-slate-500 border border-slate-200">
                Thinking…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="flex flex-col sm:flex-row gap-2 pt-4 border-t border-slate-200">
          <input
            type="text"
            placeholder={apiKey ? "Ask about the firms…" : "Enter your Groq API key first"}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send(input)}
            disabled={!apiKey}
            className="flex-1 border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={() => send(input)}
            disabled={!apiKey || !input.trim() || loading}
            className="bg-blue-600 text-white rounded-xl px-5 py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
