'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { Loader2 } from 'lucide-react'

const BASE_URL = process.env.NEXT_PUBLIC_UMBRELLA_API_URL || ''

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      // Skip auth check for login page
      if (pathname === '/login') {
        setIsLoading(false)
        setIsAuthenticated(true)
        return
      }

      // Check for token in localStorage
      const token = localStorage.getItem('umbrella_token')
      if (!token) {
        console.log('[AuthGuard] No token found, redirecting to /login')
        router.push('/login')
        return
      }

      try {
        // Verify token with /api/v1/auth/me
        const response = await fetch(`${BASE_URL}/api/v1/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.status === 401) {
          console.log('[AuthGuard] Token invalid (401), clearing and redirecting to /login')
          localStorage.removeItem('umbrella_token')
          router.push('/login')
          return
        }

        if (!response.ok) {
          console.log('[AuthGuard] Auth check failed with status:', response.status)
          router.push('/login')
          return
        }

        console.log('[AuthGuard] Auth check successful')
        setIsAuthenticated(true)
      } catch (error) {
        console.log('[AuthGuard] Auth check error:', error)
        router.push('/login')
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [pathname, router])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
        <span className="ml-3 text-muted-foreground">Checking authentication...</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null // Will redirect in useEffect
  }

  return <>{children}</>
}
