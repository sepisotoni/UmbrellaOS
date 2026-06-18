'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { AppShell } from '@/components/app-shell'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthGuard } from '@/components/auth-guard'
import { AuthProvider } from '@/components/auth-context'
import { usePathname } from 'next/navigation'

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      ),
  )
  const pathname = usePathname()

  // Don't wrap login page with AuthGuard
  const shouldUseAuthGuard = pathname !== '/login'

  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <TooltipProvider delay={200}>
          <AppShell>
            {shouldUseAuthGuard ? <AuthGuard>{children}</AuthGuard> : children}
          </AppShell>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
