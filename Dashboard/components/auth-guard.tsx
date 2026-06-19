'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth-context'
import { API_V1 } from '@/lib/api-config'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, isLoading } = useAuth()

  useEffect(() => {
    if (pathname === '/login' || !API_V1) return
    const token = localStorage.getItem('umbrella_token')
    if (!token || (!isLoading && !user)) {
      router.replace('/login')
    }
  }, [pathname, isLoading, user, router])

  if (pathname === '/login') return <>{children}</>
  if (!API_V1) return <>{children}</>
  if (isLoading) return null
  if (!user) return null
  return <>{children}</>
}
