'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'

let authCache: { valid: boolean; checked: boolean } = { valid: false, checked: false }

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [ready, setReady] = useState(authCache.checked)

  useEffect(() => {
    if (pathname === '/login') { setReady(true); return }
    if (authCache.checked && authCache.valid) { setReady(true); return }

    const token = localStorage.getItem('umbrella_token')
    if (!token) { router.replace('/login'); return }

    if (authCache.checked && !authCache.valid) { router.replace('/login'); return }

    fetch(process.env.NEXT_PUBLIC_UMBRELLA_API_URL + '/auth/me', {
      headers: { Authorization: 'Bearer ' + token }
    })
      .then(res => {
        if (res.status === 401) {
          localStorage.removeItem('umbrella_token')
          authCache = { valid: false, checked: true }
          router.replace('/login')
        } else {
          authCache = { valid: true, checked: true }
          setReady(true)
        }
      })
      .catch(() => {
        authCache = { valid: true, checked: true }
        setReady(true)
      })
  }, [pathname])

  if (pathname === '/login') return <>{children}</>
  if (!ready) return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-muted-foreground text-sm">Loading...</div>
    </div>
  )
  return <>{children}</>
}
