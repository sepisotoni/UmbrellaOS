'use client'
import { useAuth } from '@/components/auth-context'
import { Button } from '@/components/ui/button'
import { API_V1 } from '@/lib/api-config'

export default function NoAccessPage() {
  const { user } = useAuth()

  const handleSignOut = () => {
    localStorage.removeItem('umbrella_token')
    window.location.href = '/login'
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold">Access Denied</h1>
        <p className="text-muted-foreground">You don't have permission to access this dashboard.</p>
        <p className="text-sm text-muted-foreground">Contact a server administrator to get access.</p>
        {user && <p className="text-sm text-muted-foreground">Logged in as <span className="font-semibold">{user.username}</span></p>}
        <Button variant="outline" onClick={handleSignOut}>Sign Out</Button>
      </div>
    </div>
  )
}
