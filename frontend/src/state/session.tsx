import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { User } from '../api/contracts'
import { setOnIdentityRejected, setUserId } from '../api/http'

/**
 * The console is local and has no login screen: it signs in as the pack's manager on its
 * own. Every write still carries that user's id, so each action keeps its author.
 */
const DEFAULT_EMAIL = import.meta.env.VITE_DEFAULT_USER_EMAIL || 'martin@trace-it.local'

type Session = {
  user: User | null
  /** Why the automatic identity failed, while there is no user. */
  identityError: unknown
  /** Only a manager handles escalations, and the backend refuses everyone else. */
  isManager: boolean
  /** Act as another user of the process, from Ajustes. */
  signIn: (email: string) => Promise<User>
}

const Ctx = createContext<Session | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [identityError, setIdentityError] = useState<unknown>(null)
  const current = useRef<User | null>(null)
  const pending = useRef<Promise<User> | null>(null)
  const queryClient = useQueryClient()

  const signIn = useCallback(
    async (email: string) => {
      const next = await api.login(email)
      const changed = current.current?.id !== next.id
      current.current = next
      setUserId(next.id)
      setUser(next)
      setIdentityError(null)
      // Only a new identity changes what the backend answers. Refetching on the same one
      // would loop on a 403 that no identity can fix.
      if (changed) void queryClient.invalidateQueries()
      return next
    },
    [queryClient],
  )

  /** The automatic identity, at most one request at a time. */
  const identify = useCallback(() => {
    pending.current ??= signIn(DEFAULT_EMAIL)
      .catch((error: unknown) => {
        setIdentityError(error)
        throw error
      })
      .finally(() => {
        pending.current = null
      })
    return pending.current
  }, [signIn])

  useEffect(() => {
    identify().catch(() => undefined)
  }, [identify])

  // A 401 or 403 retries the automatic identity; the screen still shows its ErrorNotice.
  useEffect(() => {
    setOnIdentityRejected(() => identify().catch(() => undefined))
    return () => setOnIdentityRejected(null)
  }, [identify])

  const value = useMemo(
    () => ({ user, identityError, isManager: user?.role === 'manager', signIn }),
    [user, identityError, signIn],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSession(): Session {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useSession fuera de SessionProvider')
  return ctx
}
