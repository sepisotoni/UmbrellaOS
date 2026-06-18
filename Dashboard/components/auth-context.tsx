'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

const BASE_URL = process.env.NEXT_PUBLIC_UMBRELLA_API_URL || ''

interface User {
  username: string
  role: string
  // Add other user fields as needed
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const refreshUser = async () => {
    const token = localStorage.getItem('umbrella_token')
    if (!token) {
      setUser(null)
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`${BASE_URL}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setUser(data)
      } else {
        setUser(null)
      }
    } catch (error) {
      console.log('[AuthProvider] Error fetching user:', error)
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
