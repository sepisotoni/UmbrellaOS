const raw = (process.env.NEXT_PUBLIC_UMBRELLA_API_URL || '').replace(/\/$/, '')

/** Base URL of Umbrella Core (without /api/v1). */
export const API_ROOT = raw.endsWith('/api/v1') ? raw.replace(/\/api\/v1$/, '') : raw

/** Versioned API prefix used by dashboard fetch calls. */
export const API_V1 = raw.endsWith('/api/v1') ? raw : `${raw}/api/v1`

export const ADMIN_KEY = process.env.NEXT_PUBLIC_UMBRELLA_ADMIN_KEY || ''

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('umbrella_token')
}

export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...extra }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}
