'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Check if this is a callback from Discord OAuth
    const code = searchParams.get('code')
    const state = searchParams.get('state')

    if (code && state) {
      handleCallback(code, state)
    }
  }, [searchParams])

  const handleLogin = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const redirectUri = `${window.location.origin}/login`
      const response = await fetch('/api/v1/auth/discord/authorize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ redirect_uri: redirectUri }),
      })

      if (!response.ok) {
        throw new Error('Failed to initiate OAuth flow')
      }

      const data = await response.json()
      // Redirect to Discord OAuth URL
      window.location.href = data.authorize_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
      setIsLoading(false)
    }
  }

  const handleCallback = async (code: string, state: string) => {
    setIsLoading(true)
    setError(null)

    try {
      const redirectUri = `${window.location.origin}/login`
      const response = await fetch('/api/v1/auth/discord/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
      })

      if (!response.ok) {
        throw new Error('OAuth callback failed')
      }

      const data = await response.json()
      // Save token to localStorage
      localStorage.setItem('umbrella_token', data.token)
      // Redirect to dashboard home
      router.push('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold">UmbrellaOS</h1>
          <p className="mt-2 text-muted-foreground">Sign in to access the dashboard</p>
        </div>

        <div className="space-y-4">
          <Button
            onClick={handleLogin}
            disabled={isLoading}
            className="w-full"
            size="lg"
          >
            {isLoading ? 'Connecting...' : 'Login with Discord'}
          </Button>

          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center text-sm text-destructive">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
