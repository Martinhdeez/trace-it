import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { defaultVersionId } from '../data/versions'
import { PROCESS } from '../lib/paths'

type AppState = {
  versionFor: (processId: string) => string
  setVersion: (processId: string, id: string) => void
  versionsOpen: boolean
  setVersionsOpen: (open: boolean) => void
  paletteOpen: boolean
  setPaletteOpen: (open: boolean) => void
}

const Ctx = createContext<AppState | null>(null)

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [versions, setVersions] = useState<Record<string, string>>({
    [PROCESS.reconcilePayments]: defaultVersionId(PROCESS.reconcilePayments),
    [PROCESS.landRegistry]: defaultVersionId(PROCESS.landRegistry),
    [PROCESS.vendorOnboarding]: defaultVersionId(PROCESS.vendorOnboarding),
  })
  const [versionsOpen, setVersionsOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)

  const versionFor = useCallback(
    (processId: string) => versions[processId] ?? defaultVersionId(processId),
    [versions],
  )

  const setVersion = useCallback((processId: string, id: string) => {
    setVersions((current) => ({ ...current, [processId]: id }))
  }, [])

  const value = useMemo(
    () => ({
      versionFor,
      setVersion,
      versionsOpen,
      setVersionsOpen,
      paletteOpen,
      setPaletteOpen,
    }),
    [versionFor, setVersion, versionsOpen, paletteOpen],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAppState() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAppState fuera de AppStateProvider')
  return ctx
}
