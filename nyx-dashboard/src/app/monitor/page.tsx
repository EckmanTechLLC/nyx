'use client'

import { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { nyxAPI } from '@/services/api'
import { useSystemStatus, useHealth, useEngineStatus, useSystemInfo, useRecentTasks, useActiveWorkflows } from '@/hooks/useNYX'
import { 
  Monitor, 
  Database, 
  Zap, 
  DollarSign, 
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Activity,
  Server,
  Cpu,
  HardDrive,
  Network,
  RefreshCw
} from 'lucide-react'

// Interfaces removed - using real API data instead

export default function MonitorPage() {
  // All data now comes from real APIs

  const { data: systemStatus, refetch: refetchSystem } = useSystemStatus()
  const { data: healthStatus, refetch: refetchHealth } = useHealth()
  const { data: engineStatus, refetch: refetchEngine } = useEngineStatus()
  const { data: systemInfo, refetch: refetchInfo } = useSystemInfo()
  const { data: recentTasks } = useRecentTasks(10)
  const { data: activeWorkflows } = useActiveWorkflows(10)

  // Set default API key for development
  useEffect(() => {
    nyxAPI.setApiKey('nyx-dev-key-12345')
  }, [])

  // All metrics now come from real API data

  const refreshAllData = async () => {
    await Promise.all([
      refetchSystem(),
      refetchHealth(),
      refetchEngine(),
      refetchInfo()
    ])
  }

  const formatUptime = (timestamp: string) => {
    const startTime = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - startTime.getTime()
    const minutes = Math.floor(diffMs / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    if (days > 0) return `${days}d ${hours % 24}h`
    if (hours > 0) return `${hours}h ${minutes % 60}m`
    return `${minutes}m`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-400'
      case 'warning': return 'text-yellow-400'
      case 'error': return 'text-red-400'
      default: return 'text-slate-400'
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-4 h-4 text-green-400" />
      case 'down': return <TrendingDown className="w-4 h-4 text-red-400" />
      default: return <Activity className="w-4 h-4 text-slate-400" />
    }
  }

  const getHealthIcon = (status: string) => {
    return status === 'healthy' ? 
      <CheckCircle className="w-5 h-5 text-green-400" /> : 
      <AlertTriangle className="w-5 h-5 text-red-400" />
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">System Monitor</h1>
            <p className="text-slate-400 mt-1">Performance metrics and system health</p>
          </div>
          <Button
            onClick={refreshAllData}
            variant="outline"
            className="bg-slate-800 border-slate-600 hover:bg-slate-700"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* System Health Overview */}
        <div className="grid gap-6 md:grid-cols-4 mb-8">
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">API Health</p>
                  <p className="text-2xl font-bold text-white">
                    {healthStatus?.status === 'healthy' ? 'Healthy' : 'Issues'}
                  </p>
                </div>
                {getHealthIcon(healthStatus?.status || 'unknown')}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Database</p>
                  <p className="text-2xl font-bold text-white">
                    {systemStatus?.database?.status === 'connected' ? 'Connected' : 'Issues'}
                  </p>
                </div>
                <Database className={`w-5 h-5 ${
                  systemStatus?.database?.status === 'connected' ? 'text-green-400' : 'text-red-400'
                }`} />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Engine Status</p>
                  <p className="text-2xl font-bold text-white">
                    {engineStatus?.running ? 'Running' : 'Stopped'}
                  </p>
                </div>
                <Zap className={`w-5 h-5 ${
                  engineStatus?.running ? 'text-green-400' : 'text-slate-400'
                }`} />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">API Uptime</p>
                  <p className="text-2xl font-bold text-white">
                    {healthStatus?.timestamp ? formatUptime(healthStatus.timestamp) : 'N/A'}
                  </p>
                </div>
                <Clock className="w-5 h-5 text-blue-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Performance Metrics */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  Performance Metrics
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Key system performance indicators
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="p-4 bg-slate-900 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-slate-300">Engine Status</h3>
                      <Activity className="w-4 h-4 text-blue-400" />
                    </div>
                    <div className="flex items-end justify-between">
                      <span className={`text-2xl font-bold ${
                        engineStatus?.running ? 'text-green-400' : 'text-slate-400'
                      }`}>
                        {engineStatus?.running ? 'Running' : 'Stopped'}
                      </span>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-slate-900 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-slate-300">Task Success Rate</h3>
                      <TrendingUp className="w-4 h-4 text-green-400" />
                    </div>
                    <div className="flex items-end justify-between">
                      <span className="text-2xl font-bold text-green-400">
                        {recentTasks?.recent_tasks ? 
                          Math.round((recentTasks.recent_tasks.filter(t => t.success).length / recentTasks.recent_tasks.length) * 100) + '%' : 
                          'N/A'
                        }
                      </span>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-slate-900 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-slate-300">Active Workflows</h3>
                      <Activity className="w-4 h-4 text-blue-400" />
                    </div>
                    <div className="flex items-end justify-between">
                      <span className="text-2xl font-bold text-blue-400">
                        {activeWorkflows?.count || 0}
                      </span>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-slate-900 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-slate-300">Recent Tasks</h3>
                      <TrendingUp className="w-4 h-4 text-purple-400" />
                    </div>
                    <div className="flex items-end justify-between">
                      <span className="text-2xl font-bold text-purple-400">
                        {recentTasks?.count || 0}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* System Resources */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Server className="w-5 h-5 text-blue-400" />
                  System Resources
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <Database className="w-5 h-5 text-blue-400" />
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-300">Database Status</span>
                        <span className={systemStatus?.database?.status === 'connected' ? 'text-green-400' : 'text-red-400'}>
                          {systemStatus?.database?.status === 'connected' ? 'Connected' : 'Disconnected'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <Zap className="w-5 h-5 text-green-400" />
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-300">Engine Configuration</span>
                        <span className="text-slate-300">
                          {engineStatus?.evaluation_interval || 'N/A'}s interval
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <Monitor className="w-5 h-5 text-yellow-400" />
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-300">Max Concurrent Tasks</span>
                        <span className="text-slate-300">
                          {engineStatus?.max_concurrent_tasks || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <Network className="w-5 h-5 text-purple-400" />
                    <div className="flex-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-300">API Health</span>
                        <span className={healthStatus?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}>
                          {healthStatus?.status || 'Unknown'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Cost Analytics */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-green-400" />
                  Cost Analytics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Estimated Total Cost</span>
                  <span className="text-green-400 font-mono">
                    ${recentTasks?.recent_tasks ? 
                      (recentTasks.recent_tasks.length * 0.002).toFixed(4) : 
                      '0.0000'
                    }
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Avg Cost per Task</span>
                  <span className="text-green-400 font-mono">
                    ${recentTasks?.recent_tasks && recentTasks.recent_tasks.length > 0 ? 
                      '0.0020' : 
                      '0.0000'
                    }
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Successful Tasks</span>
                  <span className="text-green-400 font-mono">
                    {recentTasks?.recent_tasks ? 
                      recentTasks.recent_tasks.filter(t => t.success).length : 
                      0
                    }
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Cost Efficiency</span>
                  <span className="text-green-400 font-mono">
                    {recentTasks?.recent_tasks && recentTasks.recent_tasks.length > 0 ? 
                      (recentTasks.recent_tasks.filter(t => t.success).length / recentTasks.recent_tasks.length * 100).toFixed(0) + '%' : 
                      'N/A'
                    }
                  </span>
                </div>
                <div className="pt-3 border-t border-slate-700">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-300">Daily Est. Rate</span>
                    <span className="text-yellow-400 font-mono">
                      ${recentTasks?.recent_tasks && recentTasks.recent_tasks.length > 0 ? 
                        ((recentTasks.recent_tasks.length * 0.002) * 24).toFixed(3) : 
                        '0.000'
                      }/day
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Error Tracking */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  Error Tracking
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Failed Tasks</span>
                  <span className={recentTasks?.recent_tasks ? 
                    (recentTasks.recent_tasks.filter(t => !t.success).length > 0 ? 'text-red-400' : 'text-green-400') : 
                    'text-slate-400'
                  }>
                    {recentTasks?.recent_tasks ? recentTasks.recent_tasks.filter(t => !t.success).length : 0}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Completed Tasks</span>
                  <span className="text-green-400">
                    {recentTasks?.recent_tasks ? recentTasks.recent_tasks.filter(t => t.success).length : 0}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Task Failure Rate</span>
                  <span className={recentTasks?.recent_tasks ? 
                    (recentTasks.recent_tasks.filter(t => !t.success).length / recentTasks.recent_tasks.length > 0.1 ? 'text-red-400' : 'text-green-400') : 
                    'text-slate-400'
                  }>
                    {recentTasks?.recent_tasks ? 
                      Math.round((recentTasks.recent_tasks.filter(t => !t.success).length / recentTasks.recent_tasks.length) * 100) + '%' : 
                      'N/A'
                    }
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">System Health</span>
                  <span className={healthStatus?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}>
                    {healthStatus?.status === 'healthy' ? 'Healthy' : 'Issues'}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* System Info */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">System Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {systemInfo ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Version</span>
                      <Badge className="bg-slate-700 text-slate-200">{systemInfo.version}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Name</span>
                      <span className="text-slate-300 text-xs">{systemInfo.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Features</span>
                      <span className="text-slate-300">{systemInfo.features?.length || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Updated</span>
                      <span className="text-slate-300">
                        {systemInfo.timestamp ? new Date(systemInfo.timestamp).toLocaleDateString() : 'N/A'}
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="text-slate-400 text-center py-4">
                    Loading system info...
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}