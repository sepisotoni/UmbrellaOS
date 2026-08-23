import { useState, useEffect } from 'react'
import { Shield, ExternalLink } from 'lucide-react'
import { auth } from '../../lib/api'
import { useAuth } from '../../context/AuthContext'
import { Button, Input, ErrorCard, Spinner } from '../ui'

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const { login } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [oauthPending, setOauthPending] = useState(false)

  // Handle OAuth callback (code + state in URL hash/search)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    if (code && state) {
      const savedState = sessionStorage.getItem('umbrella_oauth_state')
      if (savedState !== state) {
        setError('OAuth state mismatch — possible CSRF. Please try again.')
        window.history.replaceState({}, '', window.location.pathname)
        return
      }
      sessionStorage.removeItem('umbrella_oauth_state')
      setLoading(true)
      setOauthPending(true)
      const redirectUri = `${window.location.origin}${window.location.pathname}`
      auth
        .discordCallback(state, code, redirectUri)
        .then(({ token, user }) => {
          login(token, user)
          window.history.replaceState({}, '', window.location.pathname)
          onLogin()
        })
        .catch((err) => {
          setError(err.message)
          setLoading(false)
          setOauthPending(false)
          window.history.replaceState({}, '', window.location.pathname)
        })
    }
  }, [login, onLogin])

  const handleDiscordLogin = async () => {
    setLoading(true)
    setError(null)
    try {
      const redirectUri = `${window.location.origin}${window.location.pathname}`
      const { authorize_url, state } = await auth.discordAuthorize(redirectUri)
      sessionStorage.setItem('umbrella_oauth_state', state)
      window.location.href = authorize_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start OAuth flow')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#070914] flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-violet-500/10 border border-violet-500/30 mb-4">
            <Shield className="h-7 w-7 text-violet-400" />
          </div>
          <h1 className="text-xl font-bold text-slate-100">UmbrellaOS</h1>
          <p className="text-xs text-slate-500 mt-1">Minecraft Server Network Dashboard</p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6 space-y-4">
          {oauthPending ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <Spinner className="h-6 w-6 text-violet-400" />
              <p className="text-sm text-slate-400">Completing Discord login…</p>
            </div>
          ) : (
            <>
              {error && <ErrorCard message={error} onRetry={() => setError(null)} />}

              <Button
                variant="primary"
                className="w-full justify-center py-2.5"
                loading={loading}
                onClick={handleDiscordLogin}
              >
                <ExternalLink className="h-4 w-4" />
                Sign in with Discord
              </Button>

              <p className="text-center text-[11px] text-slate-500">
                You must be a registered staff member to access this dashboard.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
