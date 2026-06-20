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
    if (pathname === '/login' || pathname === '/no-access' || !API_V1) return
    const token = localStorage.getItem('umbrella_token')
    if (!token || (!isLoading && !user)) {
      router.replace('/login')
      return
    }
    if (!isLoading && user && !user.role_id) {
      router.replace('/no-access')
    }
  }, [pathname, isLoading, user, router])
  if (pathname === '/login' || pathname === '/no-access') return <>{children}</>
  if (!API_V1) return <>{children}</>
  if (isLoading) return null
  if (!user || !user.role_id) return null
  return <>{children}</>
}
