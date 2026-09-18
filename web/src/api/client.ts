import { mockClient } from './mock'
import type { ApiClient } from './types'

const mode = import.meta.env.VITE_API_MODE ?? 'mock'

export const api: ApiClient = mode === 'live' ? mockClient : mockClient
