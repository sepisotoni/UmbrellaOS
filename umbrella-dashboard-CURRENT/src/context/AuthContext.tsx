import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { auth as authApi, UserSchema } from '../lib/api'

interface AuthContextValue {
  token: string | null
  user: UserSchema | null
  loading: boolean
  login: (token: string, user: UserSchema) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<UserSchema | null>(null)
  const [loading, setLoading] = useState(true)

  // On mount, try to restore a session from sessionStorage (survives page refresh,
  // cleared when browser tab is closed — NOT localStorage which persists forever)
  useEffect(() => {
    const saved = sessionStorage.getItem('umbrella_session')
    if (saved) {
      try {
        const { token: t, user: u } = JSON.parse(saved) as { token: string; user: UserSchema }
        // Validate the token is still valid
        authApi.me(t).then((freshUser) => {
          setToken(t)
          setUser(freshUser)
          setLoading(false)
        }).catch(() => {
          sessionStorage.removeItem('umbrella_session')
          setLoading(false)
        })
      } catch {
        sessionStorage.removeItem('umbrella_session')
        setLoading(false)
      }
    } else {
      setLoading(false)
    }
  }, [])

  const login = useCallback((t: string, u: UserSchema) => {
    setToken(t)
    setUser(u)
    sessionStorage.setItem('umbrella_session', JSON.stringify({ token: t, user: u }))
  }, [])

  const logout = useCallback(async () => {
    if (token) {
      try {
        await authApi.logout(token)
      } catch { /* ignore */ }
    }
    setToken(null)
    setUser(null)
    sessionStorage.removeItem('umbrella_session')
  }, [token])

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
