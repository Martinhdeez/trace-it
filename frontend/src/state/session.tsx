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
import { ApiError, setOnUnauthenticated, setUserId } from '../api/http'

const STORAGE_KEY = 'trace.usuario'

function stored(): User | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const user = raw ? (JSON.parse(raw) as Partial<User>) : null
    // An older build stored the Spanish shape; treat it as signed out.
    return user && typeof user.id === 'number' && (user.role === 'manager' || user.role === 'operator')
      ? (user as User)
      : null
  } catch {
    return null
  }
}

type Session = {
  user: User | null
  /** Only a manager handles escalations, and the backend refuses everyone else. */
  isManager: boolean
  signIn: (email: string) => Promise<User>
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

  const signIn = useCallback(
    async (email: string) => {
      const next = await api.login(email)
      setUserId(next.id)
      setUser(next)
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      void queryClient.invalidateQueries()
      return next
    },
    [queryClient],
  )

  const signOut = useCallback(() => {
    setUserId(null)
    setUser(null)
    window.localStorage.removeItem(STORAGE_KEY)
    queryClient.clear()
  }, [queryClient])

  // A stored id can outlive its user (a database reset). Ask the backend once on boot.
  useEffect(() => {
    if (!user) return
    api.me().then(setUser, (error) => {
      if (error instanceof ApiError && (error.status === 404 || error.status === 401)) signOut()
    })
    // Only on boot: `user` changes on every sign-in, which already came from the backend.
  }, [])

  // The console shows Login as soon as there is no user, so signing out is the whole reaction.
  useEffect(() => {
    setOnUnauthenticated(signOut)
    return () => setOnUnauthenticated(null)
  }, [signOut])

  const value = useMemo(
    () => ({ user, isManager: user?.role === 'manager', signIn, signOut }),
    [user, signIn, signOut],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSession(): Session {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useSession fuera de SessionProvider')
  return ctx
}
