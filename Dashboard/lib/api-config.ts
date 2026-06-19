export const API_ROOT = (process.env.NEXT_PUBLIC_UMBRELLA_API_URL || '').replace(/\/$/, '')
export const API_V1 = API_ROOT ? `${API_ROOT}/api/v1` : ''
export const ADMIN_KEY = process.env.NEXT_PUBLIC_UMBRELLA_ADMIN_KEY || ''

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('umbrella_token')
}

export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...extra }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (ADMIN_KEY) headers['X-Admin-Key'] = ADMIN_KEY
  return headers
}
