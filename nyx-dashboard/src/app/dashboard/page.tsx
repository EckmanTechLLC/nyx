'use client'

import { useAuth } from '@/hooks/useAuth'
import { useEngineStatus, useMotivationalStates } from '@/hooks/useNYX'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { nyxAPI } from '@/services/api'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const { isAuthenticated, logout } = useAuth()
  const router = useRouter()
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  const { data: engineStatus, isLoading: statusLoading, error: statusError } = useEngineStatus()
  const { data: motivationalStates, isLoading: statesLoading } = useMotivationalStates()

  const startEngineMutation = useMutation({
    mutationFn: () => nyxAPI.startEngine(),
    onSuccess: () => {
      toast.success('NYX Engine started successfully')
      queryClient.invalidateQueries({ queryKey: ['engine'] })
    },
    onError: (error: Error) => {
      toast.error(`Failed to start engine: ${error.message}`)
    }
  })

  const stopEngineMutation = useMutation({
    mutationFn: () => nyxAPI.stopEngine(),
    onSuccess: () => {
      toast.success('NYX Engine stopped')
      queryClient.invalidateQueries({ queryKey: ['engine'] })
    },
    onError: (error: Error) => {
      toast.error(`Failed to stop engine: ${error.message}`)
    }
  })

  if (!isAuthenticated) {
    return null
  }

  if (statusError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert className="max-w-2xl mx-auto bg-red-900/20 border-red-700">
          <AlertDescription>
            Failed to connect to NYX API. Please check your connection and API key.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-white">NYX Dashboard</h1>
          <p className="text-slate-400 mt-2">Autonomous AI Agent Control Interface</p>
        </div>
        <Button onClick={logout} variant="outline" className="bg-slate-800 border-slate-600 hover:bg-slate-700">
          Logout
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-8">
        {/* Engine Status Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${statusLoading ? 'bg-yellow-500' : engineStatus?.running ? 'bg-green-500' : 'bg-red-500'}`}></div>
              Engine Status
            </CardTitle>
            <CardDescription className="text-slate-400">
              {statusLoading ? 'Loading...' : engineStatus?.running ? 'Running' : 'Stopped'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!statusLoading && engineStatus && (
              <div className="space-y-2 text-sm text-slate-300">
                <div>Interval: {engineStatus.evaluation_interval}s</div>
                <div>Max Tasks: {engineStatus.max_concurrent_tasks}</div>
                <div>Safety: {engineStatus.safety_enabled ? 'Enabled' : 'Disabled'}</div>
              </div>
            )}
            <div className="flex gap-2">
              <Button 
                onClick={() => startEngineMutation.mutate()}
                disabled={statusLoading || engineStatus?.running || startEngineMutation.isPending}
                className="bg-green-600 hover:bg-green-700 text-white"
                size="sm"
              >
                {startEngineMutation.isPending ? 'Starting...' : 'Start'}
              </Button>
              <Button 
                onClick={() => stopEngineMutation.mutate()}
                disabled={statusLoading || !engineStatus?.running || stopEngineMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white"
                size="sm"
              >
                {stopEngineMutation.isPending ? 'Stopping...' : 'Stop'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Motivational States Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Motivational States</CardTitle>
            <CardDescription className="text-slate-400">
              Current autonomous motivations
            </CardDescription>
          </CardHeader>
          <CardContent>
            {statesLoading ? (
              <div className="text-slate-400">Loading states...</div>
            ) : motivationalStates && motivationalStates.states.length > 0 ? (
              <div className="space-y-2">
                {motivationalStates.states.slice(0, 3).map((state, index) => (
                  <div key={index} className="flex justify-between items-center text-sm">
                    <span className="text-slate-300 capitalize">{state.motivation_type}</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      state.is_active ? 'bg-green-900 text-green-200' :
                      state.satisfaction > 0.8 ? 'bg-blue-900 text-blue-200' :
                      'bg-slate-700 text-slate-300'
                    }`}>
                      {state.is_active ? 'Active' : state.satisfaction > 0.8 ? 'Satisfied' : 'Idle'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-400">No active motivations</div>
            )}
          </CardContent>
        </Card>

        {/* System Monitor Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">System Monitor</CardTitle>
            <CardDescription className="text-slate-400">
              Real-time system status
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">API Status</span>
              <span className="text-green-400">Connected</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Last Update</span>
              <span className="text-slate-300">
                {engineStatus?.timestamp ? new Date(engineStatus.timestamp).toLocaleTimeString() : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Safety Mode</span>
              <span className={engineStatus?.safety_enabled ? 'text-green-400' : 'text-yellow-400'}>
                {engineStatus?.safety_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity Placeholder */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Recent Activity</CardTitle>
          <CardDescription className="text-slate-400">
            Latest autonomous tasks and decisions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-slate-400 text-center py-8">
            Activity monitoring will be implemented in Phase 2
          </div>
        </CardContent>
      </Card>
    </div>
  )
}