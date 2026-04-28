import { CATEGORY_BG } from "@/lib/types"

export default function CategoryBadge({ category }: { category: string | null }) {
  const cat = category ?? "Other"
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${CATEGORY_BG[cat] ?? CATEGORY_BG.Other}`}>
      {cat}
    </span>
  )
}
