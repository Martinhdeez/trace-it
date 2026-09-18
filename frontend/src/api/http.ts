const BASE = import.meta.env.VITE_API_URL ?? '/api'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }

  /** The contract exists but its owner has not filled it in yet (501). */
  get notImplemented(): boolean {
    return this.status === 501
  }

  /** The backend is not up, or CORS blocked us. */
  get unreachable(): boolean {
    return this.status === 0
  }
}

let userId: number | null = null

export function setUserId(id: number | null) {
  userId = id
}

function headers(extra?: HeadersInit): Headers {
  const result = new Headers(extra)
  if (userId != null) result.set('X-Usuario-Id', String(userId))
  return result
}

async function fail(response: Response): Promise<never> {
  let code = 'http_error'
  let message = `${response.status} ${response.statusText}`
  try {
    const body = await response.json()
    if (typeof body?.code === 'string') code = body.code
    if (typeof body?.message === 'string') message = body.message
    else if (typeof body?.detail === 'string') message = body.detail
  } catch {
    // Body was not the `{code, message}` envelope. Keep the status text.
  }
  throw new ApiError(response.status, code, message)
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, init)
  } catch (error) {
    throw new ApiError(0, 'unreachable', error instanceof Error ? error.message : 'Sin conexión')
  }
  if (!response.ok) await fail(response)
  return response
}

export async function get<T>(path: string): Promise<T> {
  const response = await send(path, { headers: headers() })
  return response.json() as Promise<T>
}

export async function getText(path: string): Promise<string> {
  const response = await send(path, { headers: headers() })
  return response.text()
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  const response = await send(path, {
    method: 'POST',
    headers: headers(body === undefined ? undefined : { 'Content-Type': 'application/json' }),
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

export async function put<T>(path: string, body: unknown): Promise<T> {
  const response = await send(path, {
    method: 'PUT',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  return response.json() as Promise<T>
}

export async function upload<T>(path: string, form: FormData): Promise<T> {
  // No Content-Type: the browser sets the multipart boundary.
  const response = await send(path, { method: 'POST', headers: headers(), body: form })
  return response.json() as Promise<T>
}

export function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}
