import { create } from "zustand"

interface FilterState {
  categories: string[]
  sectors: string[]
  minEmployees: number
  priorityOnly: boolean
  setCategories: (v: string[]) => void
  setSectors: (v: string[]) => void
  setMinEmployees: (v: number) => void
  setPriorityOnly: (v: boolean) => void
  reset: () => void
}

export const useFilterStore = create<FilterState>((set) => ({
  categories: [],
  sectors: [],
  minEmployees: 0,
  priorityOnly: false,
  setCategories: (categories) => set({ categories }),
  setSectors: (sectors) => set({ sectors }),
  setMinEmployees: (minEmployees) => set({ minEmployees }),
  setPriorityOnly: (priorityOnly) => set({ priorityOnly }),
  reset: () => set({ categories: [], sectors: [], minEmployees: 0, priorityOnly: false }),
}))
