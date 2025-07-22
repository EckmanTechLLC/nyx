'use client'

import { useAuth } from '@/hooks/useAuth'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function HomePage() {
  const { isAuthenticated, connectionStatus } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (connectionStatus !== 'connecting') {
      if (isAuthenticated) {
        router.push('/dashboard')
      } else {
        router.push('/login')
      }
    }
  }, [isAuthenticated, connectionStatus, router])

  if (connectionStatus === 'connecting') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">Loading NYX Dashboard...</div>
      </div>
    )
  }

  return null
}
