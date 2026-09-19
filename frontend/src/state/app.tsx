import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

const SIDEBAR_KEY = 'traceit.sidebar'

type AppState = {
  paletteOpen: boolean
  setPaletteOpen: (open: boolean) => void
  /** The mobile drawer: the sidebar slides in over the shell. */
  navOpen: boolean
  setNavOpen: (open: boolean) => void
  /** The desktop rail: the sidebar compressed to icons. Kept in this browser. */
  sidebarCollapsed: boolean
  toggleSidebar: () => void
}

const Ctx = createContext<AppState | null>(null)

function storedCollapsed(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_KEY) === 'collapsed'
  } catch {
    return false
  }
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(storedCollapsed)

  const toggleSidebar = () => {
    const next = !sidebarCollapsed
    setSidebarCollapsed(next)
    try {
      if (next) window.localStorage.setItem(SIDEBAR_KEY, 'collapsed')
      else window.localStorage.removeItem(SIDEBAR_KEY)
    } catch {
      /* private mode */
    }
  }

  const value = useMemo(
    () => ({ paletteOpen, setPaletteOpen, navOpen, setNavOpen, sidebarCollapsed, toggleSidebar }),
    [paletteOpen, navOpen, sidebarCollapsed],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAppState() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAppState fuera de AppStateProvider')
  return ctx
}
