'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { API_V1, authHeaders } from '@/lib/api-config'

interface User {
  id: string
  discord_id: string
  username: string
  email?: string
  role?: string
  role_id?: string
  is_active: boolean
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = async () => {
    if (!API_V1) {
      setUser(null)
      setIsLoading(false)
      return
    }

    const token = localStorage.getItem('umbrella_token')
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`${API_V1}/auth/me`, { headers: authHeaders() })
      setUser(response.ok ? await response.json() : null)
      if (!response.ok) localStorage.removeItem('umbrella_token')
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshUser()
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
