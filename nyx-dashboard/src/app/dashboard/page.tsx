'use client'

import { useAuth } from '@/hooks/useAuth'
import { useEngineStatus, useMotivationalStates, useRecentTasks } from '@/hooks/useNYX'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { nyxAPI } from '@/services/api'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import { useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { 
  DollarSign, 
  AlertTriangle, 
  Settings2, 
  TrendingUp,
  Brain
} from 'lucide-react'

export default function DashboardPage() {
  const { logout } = useAuth()
  const queryClient = useQueryClient()
  // Cost data will be available when cost tracking API is implemented
  // Alert data will come from real system events when available

  // Set default API key for development
  useEffect(() => {
    nyxAPI.setApiKey('nyx-dev-key-12345')
  }, [])

  // Temporarily disable auth requirement for development
  // useEffect(() => {
  //   if (!isAuthenticated) {
  //     router.push('/login')
  //   }
  // }, [isAuthenticated, router])

  const { data: engineStatus, isLoading: statusLoading, error: statusError } = useEngineStatus()
  const { data: motivationalStates, isLoading: statesLoading } = useMotivationalStates()
  const { data: recentTasks, isLoading: tasksLoading } = useRecentTasks(5)

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

  // Temporarily disable auth check for development
  // if (!isAuthenticated) {
  //   return null
  // }

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
    <DashboardLayout>
      <div className="container mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Dashboard</h1>
            <p className="text-slate-400 mt-1">Autonomous AI Agent Control Interface</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm text-slate-400">
              Last update: {engineStatus?.timestamp ? new Date(engineStatus.timestamp).toLocaleTimeString() : 'N/A'}
            </div>
            <Button onClick={logout} variant="outline" className="bg-slate-800 border-slate-600 hover:bg-slate-700">
              Logout
            </Button>
          </div>
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

        {/* Cost Counter Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-green-400" />
              API Costs
            </CardTitle>
            <CardDescription className="text-slate-400">
              Current session usage
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-300">Est. Total Cost</span>
                <span className="text-green-400 font-mono">
                  ${recentTasks?.recent_tasks ? 
                    (recentTasks.recent_tasks.length * 0.002).toFixed(4) : 
                    '0.0000'
                  }
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-300">Avg per Task</span>
                <span className="text-green-400 font-mono">
                  ${recentTasks?.recent_tasks && recentTasks.recent_tasks.length > 0 ? 
                    '0.0020' : 
                    '0.0000'
                  }
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-300">Success Rate</span>
                <span className={
                  recentTasks?.recent_tasks ? 
                    (recentTasks.recent_tasks.filter(t => t.success).length / recentTasks.recent_tasks.length > 0.8 ? 
                      'text-green-400' : 'text-yellow-400') : 
                    'text-slate-400'
                }>
                  {recentTasks?.recent_tasks ? 
                    Math.round((recentTasks.recent_tasks.filter(t => t.success).length / recentTasks.recent_tasks.length) * 100) + '%' : 
                    'N/A'
                  }
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Settings Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-blue-400" />
              Quick Settings
            </CardTitle>
            <CardDescription className="text-slate-400">
              Engine configuration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300">Evaluation Interval</span>
                <span className="text-slate-400">{engineStatus?.evaluation_interval || 30}s</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300">Max Concurrent</span>
                <span className="text-slate-400">{engineStatus?.max_concurrent_tasks || 5}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300">Safety Mode</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  engineStatus?.safety_enabled ? 'bg-green-900 text-green-200' : 'bg-yellow-900 text-yellow-200'
                }`}>
                  {engineStatus?.safety_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
            <Button size="sm" variant="outline" className="w-full bg-slate-700 border-slate-600 hover:bg-slate-600">
              Configure Engine
            </Button>
          </CardContent>
        </Card>

        {/* Motivational Engine Insights */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              Learning Insights
            </CardTitle>
            <CardDescription className="text-slate-400">
              Motivational engine scoring and adaptation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {motivationalStates && motivationalStates.states && motivationalStates.states.length > 0 ? (
              <>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Active States</span>
                  <span className="text-blue-400 font-semibold">
                    {motivationalStates.states.filter(s => s.is_active).length}/{motivationalStates.states.length}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Avg Urgency</span>
                  <span className="text-yellow-400 font-mono">
                    {(motivationalStates.states.reduce((sum, s) => sum + s.urgency, 0) / motivationalStates.states.length).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Avg Satisfaction</span>
                  <span className="text-green-400 font-mono">
                    {(motivationalStates.states.reduce((sum, s) => sum + s.satisfaction, 0) / motivationalStates.states.length).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Top Arbitration</span>
                  <span className="text-purple-400 font-mono">
                    {Math.max(...motivationalStates.states.map(s => s.arbitration_score)).toFixed(2)}
                  </span>
                </div>
                <div className="pt-2 border-t border-slate-700">
                  <div className="text-xs text-slate-500 mb-2">Top Performing State:</div>
                  <div className="text-sm text-slate-300">
                    {motivationalStates.states.reduce((best, current) => 
                      current.success_rate > best.success_rate ? current : best
                    ).motivation_type.replace(/_/g, ' ')}
                  </div>
                  <div className="text-xs text-green-400">
                    {(motivationalStates.states.reduce((best, current) => 
                      current.success_rate > best.success_rate ? current : best
                    ).success_rate * 100).toFixed(0)}% success rate
                  </div>
                </div>
              </>
            ) : (
              <div className="text-slate-400 text-center py-4">
                No motivational data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Tasks Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              Recent Tasks
            </CardTitle>
            <CardDescription className="text-slate-400">
              Latest autonomous activities
            </CardDescription>
          </CardHeader>
          <CardContent>
            {tasksLoading ? (
              <div className="text-slate-400">Loading tasks...</div>
            ) : recentTasks && recentTasks.recent_tasks.length > 0 ? (
              <div className="space-y-3">
                {recentTasks.recent_tasks.slice(0, 3).map((task, index) => (
                  <div key={index} className="flex items-start gap-3 pb-3 border-b border-slate-700 last:border-b-0">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-slate-300 truncate">
                        {task.generated_prompt?.substring(0, 60)}...
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-slate-500">
                          {task.spawned_at ? new Date(task.spawned_at).toLocaleTimeString() : 'Unknown'}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.status === 'completed' ? 'bg-green-900 text-green-200' :
                          task.status === 'active' ? 'bg-blue-900 text-blue-200' :
                          'bg-slate-700 text-slate-300'
                        }`}>
                          {task.status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-center py-4">No recent tasks</div>
            )}
          </CardContent>
        </Card>

        {/* Alert Panel Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              System Alerts
            </CardTitle>
            <CardDescription className="text-slate-400">
              Important notifications
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recentTasks?.recent_tasks && recentTasks.recent_tasks.length > 0 ? (
              <div className="space-y-2">
                {recentTasks.recent_tasks.slice(0, 2).map((task, index) => (
                  <div key={index} className="text-sm text-slate-300 p-2 bg-slate-900 rounded">
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`w-2 h-2 rounded-full ${
                        task.status === 'completed' && task.success ? 'bg-green-400' :
                        task.status === 'completed' ? 'bg-yellow-400' :
                        task.status === 'active' ? 'bg-blue-400' : 'bg-slate-400'
                      }`}></div>
                      <span className="capitalize">{task.motivation_type.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="text-xs text-slate-400">
                      {task.spawned_at ? new Date(task.spawned_at).toLocaleTimeString() : ''}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-center py-4">No recent activity</div>
            )}
          </CardContent>
        </Card>

        {/* Performance Metrics Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              Performance
            </CardTitle>
            <CardDescription className="text-slate-400">
              System metrics
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Engine Status</span>
              <span className={engineStatus?.running ? 'text-green-400' : 'text-slate-400'}>
                {engineStatus?.running ? 'Running' : 'Stopped'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Last Check</span>
              <span className="text-slate-300">
                {engineStatus?.timestamp ? 
                  new Date(engineStatus.timestamp).toLocaleTimeString() : 
                  'N/A'
                }
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Safety Mode</span>
              <span className={engineStatus?.safety_enabled ? 'text-green-400' : 'text-yellow-400'}>
                {engineStatus?.safety_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Max Tasks</span>
              <span className="text-slate-300">
                {engineStatus?.max_concurrent_tasks || 'N/A'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Recent Activity</CardTitle>
          <CardDescription className="text-slate-400">
            Latest system events and workflow executions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recentTasks && recentTasks.recent_tasks.length > 0 ? (
            <div className="space-y-3">
              {recentTasks.recent_tasks.slice(0, 4).map((task, index) => (
                <div key={task.task_id} className="flex items-center gap-3 text-sm">
                  <div className={`w-2 h-2 rounded-full ${
                    task.success ? 'bg-green-400' : task.success === false ? 'bg-red-400' : 'bg-yellow-400'
                  }`}></div>
                  <div className="flex-1 min-w-0">
                    <div className="text-slate-300 truncate">
                      {task.success ? 'Task completed' : task.success === false ? 'Task failed' : 'Task in progress'}: {task.motivation_type.replace(/_/g, ' ')}
                    </div>
                    <div className="text-xs text-slate-500">
                      {task.completed_at ? new Date(task.completed_at).toLocaleString() : 
                       task.started_at ? new Date(task.started_at).toLocaleString() :
                       new Date(task.spawned_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="text-xs text-slate-500">
                    Score: {(task.outcome_score || 0).toFixed(1)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-slate-400 text-center py-4">
              No recent activity
            </div>
          )}
        </CardContent>
      </Card>
    </div>
    </DashboardLayout>
  )
}