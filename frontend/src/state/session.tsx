import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { User } from '../api/contracts'
import { setUserId } from '../api/http'

const STORAGE_KEY = 'trace.usuario'

function stored(): User | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

type Session = {
  user: User | null
  /** Activating or retiring a rule is only for a `responsable` (P9, step 4). */
  isManager: boolean
  signIn: (email: string) => Promise<User>
  use: (user: User) => void
  signOut: () => void
}

const Ctx = createContext<Session | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(stored)
  const queryClient = useQueryClient()

  // The header travels on every request, so set it before anything fetches.
  useEffect(() => {
    setUserId(user?.id ?? null)
  }, [user])

  const use = useCallback(
    (next: User) => {
      setUserId(next.id)
      setUser(next)
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      void queryClient.invalidateQueries()
    },
    [queryClient],
  )

  const signIn = useCallback(
    async (email: string) => {
      const next = await api.login(email)
      use(next)
      return next
    },
    [use],
  )

  const signOut = useCallback(() => {
    setUserId(null)
    setUser(null)
    window.localStorage.removeItem(STORAGE_KEY)
    void queryClient.invalidateQueries()
  }, [queryClient])

  const value = useMemo(
    () => ({ user, isManager: user?.rol === 'responsable', signIn, use, signOut }),
    [user, signIn, use, signOut],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSession(): Session {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useSession fuera de SessionProvider')
  return ctx
}
