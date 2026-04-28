"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"

const LINKS = [
  { href: "/",           label: "Home" },
  { href: "/map",        label: "Map" },
  { href: "/sectors",    label: "Sectors" },
  { href: "/firms",      label: "Firms" },
  { href: "/leadership", label: "Leadership" },
  { href: "/stats",      label: "Stats" },
  { href: "/clusters",   label: "Clusters" },
  { href: "/chat",       label: "Chat" },
]

export default function Nav() {
  const path = usePathname()
  return (
    <nav className="border-b border-slate-200 bg-white sticky top-0 z-50">
      <div className="max-w-screen-xl mx-auto px-3 sm:px-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-1 py-2 sm:h-14 sm:py-0">
        <span
          className="text-xl font-bold text-slate-900 sm:mr-4 whitespace-nowrap"
          style={{ fontFamily: "Rajdhani, sans-serif" }}
        >
          Düsseldorf Growth
        </span>
        <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0 -mx-1 px-1">
          {LINKS.map(l => (
            <Link
              key={l.href}
              href={l.href}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap
                ${path === l.href
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}
