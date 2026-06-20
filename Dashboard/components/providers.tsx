'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { AppShell } from '@/components/app-shell'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/components/auth-context'
import { AuthGuard } from '@/components/auth-guard'
import { usePathname } from 'next/navigation'

function ConditionalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  if (pathname === '/login' || pathname === '/no-access') return <>{children}</>
  return <AppShell>{children}</AppShell>
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 300_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={client}>
      <TooltipProvider delay={200}>
        <AuthProvider>
          <AuthGuard>
            <ConditionalShell>{children}</ConditionalShell>
          </AuthGuard>
        </AuthProvider>
      </TooltipProvider>
    </QueryClientProvider>
  )
}
