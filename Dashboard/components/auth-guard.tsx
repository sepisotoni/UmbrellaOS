'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'

const BASE_URL = process.env.NEXT_PUBLIC_UMBRELLA_API_URL || ''

let authCache: { valid: boolean; checked: boolean } = { valid: false, checked: false }

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [ready, setReady] = useState(authCache.checked)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    // On /login page: render immediately, no check
    if (pathname === '/login') {
      setReady(true)
      return
    }

    // If already checked and valid, render immediately
    if (authCache.checked && authCache.valid) {
      setReady(true)
      return
    }

    // If already checked and invalid, redirect to login
    if (authCache.checked && !authCache.valid) {
      router.replace('/login')
      return
    }

    // Check localStorage for umbrella_token
    const token = localStorage.getItem('umbrella_token')
    if (!token) {
      console.log('[AuthGuard] No token found, redirecting to /login')
      authCache = { valid: false, checked: true }
      router.replace('/login')
      return
    }

    // Verify token with GET /api/v1/auth/me
    setIsLoading(true)
    console.log('[AuthGuard] Verifying token with /api/v1/auth/me')
    fetch(`${BASE_URL}/api/v1/auth/me?session_token=${token}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (res.status === 401) {
          console.log('[AuthGuard] Token invalid (401), clearing and redirecting to /login')
          localStorage.removeItem('umbrella_token')
          authCache = { valid: false, checked: true }
          router.replace('/login')
        } else if (res.ok) {
          console.log('[AuthGuard] Token valid, caching result')
          authCache = { valid: true, checked: true }
          setReady(true)
        } else {
          console.log('[AuthGuard] Unexpected response status:', res.status)
          authCache = { valid: false, checked: true }
          router.replace('/login')
        }
      })
      .catch((error) => {
        console.log('[AuthGuard] Error verifying token:', error)
        // On network error, still allow access (could be backend down)
        authCache = { valid: true, checked: true }
        setReady(true)
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [pathname, router])

  // On /login page: render immediately
  if (pathname === '/login') return <>{children}</>

  // Show loading spinner while checking
  if (!ready || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
        <span className="ml-3 text-muted-foreground">Verifying authentication...</span>
      </div>
    )
  }

  // Render children if authenticated
  return <>{children}</>
}
