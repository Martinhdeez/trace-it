import type { ApiClient } from './contracts'
import { ApiError } from './http'
import { liveClient } from './live'
import { mockClient } from './mock'

export type Mode = 'mock' | 'live' | 'auto'
export type Source = 'live' | 'mock'

export const mode: Mode = (import.meta.env.VITE_API_MODE as Mode) ?? 'auto'

type Method = keyof ApiClient

const sources = new Map<Method, Source>()
const listeners = new Set<() => void>()
let version = 0

function record(method: Method, source: Source) {
  if (sources.get(method) === source) return
  sources.set(method, source)
  version += 1
  for (const listener of listeners) listener()
}

/** Which endpoints answered for real and which ones the mock covered. */
export const apiTrace = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  snapshot: () => version,
  entries: () => [...sources.entries()].sort(([a], [b]) => a.localeCompare(b)),
}

/**
 * The endpoint is not there yet. Vite's proxy answers 502 with an empty body
 * when nothing is listening on 8000, so that has to count as "backend down"
 * the same as a failed fetch (status 0). A 500 that carries our `{code, message}`
 * envelope is a real answer and must reach the UI.
 */
function missingEndpoint(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false
  if (error.notImplemented || error.unreachable) return true
  if (error.status === 502 || error.status === 503 || error.status === 504) return true
  return error.status === 404 && error.code === 'http_error'
}

function withFallback(): ApiClient {
  return new Proxy({} as ApiClient, {
    get(_target, prop: string) {
      const method = prop as Method
      return async (...args: unknown[]) => {
        try {
          const result = await (liveClient[method] as (...a: unknown[]) => Promise<unknown>)(
            ...args,
          )
          record(method, 'live')
          return result
        } catch (error) {
          if (!missingEndpoint(error)) throw error
          record(method, 'mock')
          return (mockClient[method] as (...a: unknown[]) => Promise<unknown>)(...args)
        }
      }
    },
  })
}

export const api: ApiClient =
  mode === 'live' ? liveClient : mode === 'mock' ? mockClient : withFallback()

export { ApiError }
