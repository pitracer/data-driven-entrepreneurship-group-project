import type { Metadata } from "next"
import { Inter, Rajdhani } from "next/font/google"
import "./globals.css"
import Nav from "@/components/Nav"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })
const rajdhani = Rajdhani({ subsets: ["latin"], weight: ["600", "700"], variable: "--font-rajdhani" })

export const metadata: Metadata = {
  title: "Düsseldorf Growth Dashboard",
  description: "Hidden Champions — how unknown mid-sized firms are driving Düsseldorf's job growth",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${rajdhani.variable} h-full antialiased`}>
      <body className="bg-white text-slate-900 min-h-screen">
        <Nav />
        <main className="max-w-screen-xl mx-auto px-3 sm:px-4 py-4 sm:py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
