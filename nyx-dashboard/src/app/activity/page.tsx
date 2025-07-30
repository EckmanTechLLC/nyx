'use client'

import { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { nyxAPI } from '@/services/api'
import { useRecentTasks } from '@/hooks/useNYX'
import { 
  Activity, 
  Brain, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertCircle,
  Filter,
  Download,
  Search,
  RefreshCw,
  ArrowRight,
  Play,
  Pause
} from 'lucide-react'

interface ActivityEvent {
  id: string
  type: 'task_generated' | 'workflow_executed' | 'engine_started' | 'engine_stopped' | 'error' | 'system_status'
  title: string
  description: string
  timestamp: Date
  status: 'success' | 'error' | 'warning' | 'info'
  metadata?: Record<string, unknown>
}

export default function ActivityPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [eventTypeFilter, setEventTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [isAutoRefresh, setIsAutoRefresh] = useState(true)
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([])

  const { data: recentTasks, refetch: refetchTasks } = useRecentTasks(20)

  // Set default API key for development
  useEffect(() => {
    nyxAPI.setApiKey('nyx-dev-key-12345')
  }, [])

  // Convert recent tasks to activity events (real data only)
  useEffect(() => {
    if (recentTasks?.recent_tasks) {
      const taskEvents = recentTasks.recent_tasks.map((task, index) => ({
        id: `task-${task.task_id || index}`,
        type: 'task_generated' as const,
        title: 'Autonomous Task Generated',
        description: task.generated_prompt?.substring(0, 120) + '...' || 'Autonomous task generated',
        timestamp: new Date(task.spawned_at || Date.now() - (index + 1) * 5 * 60 * 1000),
        status: task.status === 'completed' ? 'success' as const : 
                task.status === 'active' ? 'info' as const : 'warning' as const,
        metadata: { 
          motivation_type: task.motivation_type,
          priority: task.task_priority,
          arbitration_score: task.arbitration_score
        }
      }))
      
      setActivityEvents(taskEvents.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()))
    } else {
      setActivityEvents([])
    }
  }, [recentTasks])

  // Auto-refresh
  useEffect(() => {
    if (isAutoRefresh) {
      const interval = setInterval(() => {
        refetchTasks()
      }, 30000) // 30 seconds to match the hook's polling
      return () => clearInterval(interval)
    }
  }, [isAutoRefresh, refetchTasks])

  const getEventIcon = (type: string, status: string) => {
    switch (type) {
      case 'task_generated':
        return <Brain className="w-4 h-4 text-purple-400" />
      case 'workflow_executed':
        return status === 'success' ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />
      case 'engine_started':
        return <Play className="w-4 h-4 text-green-400" />
      case 'engine_stopped':
        return <Pause className="w-4 h-4 text-yellow-400" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />
      default:
        return <Activity className="w-4 h-4 text-blue-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'bg-green-900 text-green-200 border-green-700'
      case 'error': return 'bg-red-900 text-red-200 border-red-700'
      case 'warning': return 'bg-yellow-900 text-yellow-200 border-yellow-700'
      default: return 'bg-blue-900 text-blue-200 border-blue-700'
    }
  }

  const filteredEvents = activityEvents.filter(event => {
    const matchesSearch = event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         event.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = eventTypeFilter === 'all' || event.type === eventTypeFilter
    const matchesStatus = statusFilter === 'all' || event.status === statusFilter
    
    return matchesSearch && matchesType && matchesStatus
  })

  const exportActivity = () => {
    const csvContent = [
      ['Timestamp', 'Type', 'Title', 'Description', 'Status'].join(','),
      ...filteredEvents.map(event => [
        event.timestamp.toISOString(),
        event.type,
        `"${event.title}"`,
        `"${event.description.replace(/"/g, '""')}"`,
        event.status
      ].join(','))
    ].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `nyx-activity-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Activity Feed</h1>
            <p className="text-slate-400 mt-1">Real-time system events and operations</p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAutoRefresh(!isAutoRefresh)}
              className={`${isAutoRefresh ? 'bg-green-900 border-green-700 text-green-200' : 'bg-slate-800 border-slate-600'}`}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isAutoRefresh ? 'animate-spin' : ''}`} />
              {isAutoRefresh ? 'Auto' : 'Manual'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={exportActivity}
              className="bg-slate-800 border-slate-600 hover:bg-slate-700"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-4">
          {/* Filters */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Filter className="w-5 h-5 text-blue-400" />
                Filters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Search
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    placeholder="Search events..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-white pl-10"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Event Type
                </label>
                <Select onValueChange={setEventTypeFilter} value={eventTypeFilter}>
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="task_generated">Task Generated</SelectItem>
                    <SelectItem value="workflow_executed">Workflow Executed</SelectItem>
                    <SelectItem value="engine_started">Engine Started</SelectItem>
                    <SelectItem value="engine_stopped">Engine Stopped</SelectItem>
                    <SelectItem value="error">Errors</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Status
                </label>
                <Select onValueChange={setStatusFilter} value={statusFilter}>
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="pt-2 border-t border-slate-700 text-sm text-slate-400">
                <div className="flex justify-between mb-1">
                  <span>Total Events</span>
                  <span>{activityEvents.length}</span>
                </div>
                <div className="flex justify-between">
                  <span>Filtered</span>
                  <span>{filteredEvents.length}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Activity Stream */}
          <div className="lg:col-span-3">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-green-400" />
                  Event Stream
                  <Badge className="ml-2 bg-slate-700 text-slate-200">
                    Live
                  </Badge>
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Real-time activity from all NYX systems
                </CardDescription>
              </CardHeader>
              <CardContent>
                {filteredEvents.length > 0 ? (
                  <div className="space-y-4 max-h-[600px] overflow-y-auto">
                    {filteredEvents.map((event, index) => (
                      <div key={event.id} className="flex items-start gap-4 pb-4 border-b border-slate-700 last:border-b-0">
                        <div className="flex-shrink-0 mt-1">
                          {getEventIcon(event.type, event.status)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <h3 className="text-slate-200 font-medium">
                                {event.title}
                              </h3>
                              <p className="text-sm text-slate-400 mt-1">
                                {event.description}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 ml-4">
                              <Badge className={`text-xs ${getStatusColor(event.status)}`}>
                                {event.status}
                              </Badge>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-4 text-xs text-slate-500">
                            <div className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {event.timestamp.toLocaleTimeString()}
                            </div>
                            <div className="capitalize">
                              {event.type.replace(/_/g, ' ')}
                            </div>
                            {event.metadata && Object.keys(event.metadata).length > 0 && (
                              <div className="flex items-center gap-1 text-slate-400">
                                <ArrowRight className="w-3 h-3" />
                                {event.metadata.motivation_type && `${event.metadata.motivation_type}`}
                                {event.metadata.duration && `${event.metadata.duration}ms`}
                                {event.metadata.cost && `$${event.metadata.cost}`}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <Activity className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-400 mb-2">No events found</h3>
                    <p className="text-slate-500">
                      {searchQuery || eventTypeFilter !== 'all' || statusFilter !== 'all'
                        ? 'Try adjusting your filters'
                        : 'Activity events will appear here as they occur'
                      }
                    </p>
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