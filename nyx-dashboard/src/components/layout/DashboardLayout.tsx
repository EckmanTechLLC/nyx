'use client'

import Navigation from './Navigation'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="flex h-screen bg-slate-950">
      <Navigation />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}