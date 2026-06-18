'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (pathname === '/login') {
      setReady(true)
      return
    }

    const token = localStorage.getItem('umbrella_token')
    if (!token) {
      router.replace('/login')
      return
    }

    setReady(true)
  }, [pathname])

  if (pathname === '/login') return <>{children}</>
  if (!ready) return null
  return <>{children}</>
}
