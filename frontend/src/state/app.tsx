import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

type AppState = {
  paletteOpen: boolean
  setPaletteOpen: (open: boolean) => void
}

const Ctx = createContext<AppState | null>(null)

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const value = useMemo(() => ({ paletteOpen, setPaletteOpen }), [paletteOpen])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAppState() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAppState fuera de AppStateProvider')
  return ctx
}
