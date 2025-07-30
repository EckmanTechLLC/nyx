'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  Workflow, 
  Activity, 
  Monitor, 
  Settings, 
  Zap,
  ChevronLeft,
  Menu
} from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Workflows', href: '/workflows', icon: Workflow },
  { name: 'Activity', href: '/activity', icon: Activity },
  { name: 'Monitor', href: '/monitor', icon: Monitor },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Navigation() {
  const pathname = usePathname()
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className={`bg-slate-900 border-r border-slate-700 transition-all duration-300 ${
      isCollapsed ? 'w-16' : 'w-64'
    }`}>
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4">
          <div className={`flex items-center gap-3 ${isCollapsed ? 'justify-center' : ''}`}>
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 rounded-lg">
              <Zap className="w-5 h-5 text-white" />
            </div>
            {!isCollapsed && (
              <div>
                <h1 className="text-lg font-bold text-white">NYX</h1>
                <p className="text-xs text-slate-400">Autonomous AI</p>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="text-slate-400 hover:text-white hover:bg-slate-800"
          >
            {isCollapsed ? <Menu className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </Button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-2 pb-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-blue-900 text-blue-100'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                } ${isCollapsed ? 'justify-center' : ''}`}
              >
                <item.icon
                  className={`flex-shrink-0 w-5 h-5 ${
                    isActive ? 'text-blue-300' : 'text-slate-400 group-hover:text-slate-300'
                  } ${isCollapsed ? '' : 'mr-3'}`}
                />
                {!isCollapsed && item.name}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700">
          <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}>
            <div className={`w-2 h-2 bg-green-500 rounded-full ${isCollapsed ? '' : 'flex-shrink-0'}`}></div>
            {!isCollapsed && (
              <div className="text-xs text-slate-400">
                <div>System Online</div>
                <div>API Connected</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}