import { ApiError } from './http'
import { liveClient } from './live'

/** The backend is the only source: the console shows its data or its errors. */
export const api = liveClient

export { ApiError }
