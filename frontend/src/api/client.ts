import type { ApiClient } from './contracts'
import { ApiError } from './http'
import { liveClient } from './live'
import { mockClient } from './mock'

export type Mode = 'mock' | 'live'

/** The real backend unless `VITE_API_MODE=mock` asks for the in-memory simulator. */
export const mode: Mode = import.meta.env.VITE_API_MODE === 'mock' ? 'mock' : 'live'

export const api: ApiClient = mode === 'mock' ? mockClient : liveClient

export { ApiError }
