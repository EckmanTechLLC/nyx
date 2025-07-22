'use client'

import { Inter } from 'next/font/google'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { useState } from 'react'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60, // 1 minute
        gcTime: 1000 * 60 * 5, // 5 minutes (formerly cacheTime)
        retry: 2,
        refetchOnWindowFocus: false,
      },
    },
  }))

  return (
    <html lang="en" className="dark">
      <head>
        <title>NYX Dashboard - Autonomous AI Agent Control</title>
        <meta name="description" content="NYX Autonomous AI Agent Control Interface" />
      </head>
      <body className={`${inter.className} bg-slate-900 text-white min-h-screen`}>
        <QueryClientProvider client={queryClient}>
          {children}
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              className: 'bg-slate-800 text-white border border-slate-700',
              success: {
                className: 'bg-green-900 text-green-100 border border-green-700',
              },
              error: {
                className: 'bg-red-900 text-red-100 border border-red-700',
              },
            }}
          />
        </QueryClientProvider>
      </body>
    </html>
  )
}