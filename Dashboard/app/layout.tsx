import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Providers } from '@/components/providers'
import { Toaster } from '@/components/ui/sonner'
import './globals.css'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'UmbrellaOS — Minecraft Network Operations',
  description:
    'Centralized operating system for Minecraft networks. Manage servers, moderation, punishments, players, plugins, and network intelligence from one panel.',
  generator: 'v0.app',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0c0e14',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const isDemoMode = !process.env.NEXT_PUBLIC_UMBRELLA_API_URL
  
  return (
    <html
      lang="en"
      className={`dark ${geistSans.variable} ${geistMono.variable} bg-background`}
    >
      <body className="font-sans antialiased">
        {isDemoMode && (
          <div className="bg-destructive/10 border-b border-destructive/20 py-2 px-4 text-center">
            <p className="text-sm text-destructive">
              Set NEXT_PUBLIC_UMBRELLA_API_URL in .env.local — mock data has been removed
            </p>
          </div>
        )}
        <Providers>{children}</Providers>
        <Toaster />
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
