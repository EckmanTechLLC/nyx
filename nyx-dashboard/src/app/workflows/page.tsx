'use client'

import { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { nyxAPI } from '@/services/api'
import { useWorkflowStrategies, useInputTypes, useActiveWorkflows } from '@/hooks/useNYX'
import { WorkflowRequest } from '@/types/nyx'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import { 
  Play, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader2,
  Settings,
  FileText,
  Zap,
  Brain
} from 'lucide-react'

interface WorkflowExecution {
  id: string
  input_type: string
  content: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  result?: string
  error?: string
  startTime: Date
  endTime?: Date
}

export default function WorkflowsPage() {
  const [mounted, setMounted] = useState(false)
  const [selectedInputType, setSelectedInputType] = useState('')
  
  useEffect(() => {
    setMounted(true)
  }, [])
  const [workflowContent, setWorkflowContent] = useState('')
  const [priority, setPriority] = useState('normal')
  const [urgency, setUrgency] = useState('normal')
  const [executionHistory, setExecutionHistory] = useState<WorkflowExecution[]>([])
  const [currentExecution, setCurrentExecution] = useState<WorkflowExecution | null>(null)

  const queryClient = useQueryClient()
  const { data: strategies } = useWorkflowStrategies()
  const { data: inputTypes } = useInputTypes()
  const { data: activeWorkflows } = useActiveWorkflows()

  // Set default API key for development
  useEffect(() => {
    nyxAPI.setApiKey('nyx-dev-key-12345')
  }, [])

  const executeWorkflowMutation = useMutation({
    mutationFn: async (request: WorkflowRequest) => {
      const response = await nyxAPI.executeWorkflow(request)
      return response
    },
    onSuccess: (data) => {
      toast.success('Workflow executed successfully!')
      
      // Add to execution history
      const execution: WorkflowExecution = {
        id: data.workflow_id || `exec-${Date.now()}`,
        input_type: selectedInputType,
        content: workflowContent,
        status: 'completed',
        progress: 100,
        result: data.content,
        startTime: currentExecution?.startTime || new Date(),
        endTime: new Date()
      }
      setExecutionHistory(prev => [execution, ...prev.slice(0, 9)]) // Keep last 10
      setCurrentExecution(null)
      
      // Clear form
      setWorkflowContent('')
      setSelectedInputType('')
      
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    },
    onError: (error: Error) => {
      toast.error(`Workflow execution failed: ${error.message}`)
      if (currentExecution) {
        setCurrentExecution({
          ...currentExecution,
          status: 'failed',
          error: error.message,
          endTime: new Date()
        })
      }
    }
  })

  const handleExecuteWorkflow = () => {
    if (!selectedInputType || !workflowContent.trim()) {
      toast.error('Please select input type and enter content')
      return
    }

    // Create execution tracking object with stable ID
    const execution: WorkflowExecution = {
      id: `exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      input_type: selectedInputType,
      content: workflowContent,
      status: 'running',
      progress: 0,
      startTime: new Date()
    }
    setCurrentExecution(execution)

    // Prepare workflow request
    const workflowRequest = {
      input_type: selectedInputType,
      content: { prompt: workflowContent },
      priority,
      urgency,
      execution_context: {
        source: 'web_dashboard',
        user_initiated: true
      }
    }

    executeWorkflowMutation.mutate(workflowRequest)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />
      default:
        return <Clock className="w-4 h-4 text-slate-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-900 text-blue-200 border-blue-700'
      case 'completed': return 'bg-green-900 text-green-200 border-green-700'
      case 'failed': return 'bg-red-900 text-red-200 border-red-700'
      default: return 'bg-slate-900 text-slate-200 border-slate-700'
    }
  }

  if (!mounted) {
    return <div>Loading...</div>
  }
  
  return (
    <DashboardLayout>
      <div className="container mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Workflow Executor</h1>
            <p className="text-slate-400 mt-1">Execute and monitor NYX workflows</p>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="bg-slate-800 border-slate-600">
              {activeWorkflows?.count || 0} Active
            </Badge>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Workflow Executor */}
          <div className="lg:col-span-2 space-y-6">
            {/* Input Form */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  New Workflow
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Configure and execute a NYX workflow
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Input Type Selection */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Input Type
                  </label>
                  <Select onValueChange={setSelectedInputType} value={selectedInputType}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                      <SelectValue placeholder="Select workflow input type" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      {inputTypes && inputTypes.length > 0 ? (
                        inputTypes.map((type) => (
                          <SelectItem key={type} value={type} className="text-white">
                            {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </SelectItem>
                        ))
                      ) : (
                        <SelectItem key="loading" value="loading" disabled className="text-slate-400">
                          Loading input types...
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {/* Content Input */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Workflow Content
                  </label>
                  <Textarea
                    placeholder="Enter your workflow prompt or requirements..."
                    value={workflowContent}
                    onChange={(e) => setWorkflowContent(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 min-h-[120px]"
                  />
                </div>

                {/* Priority and Urgency Controls */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Priority
                    </label>
                    <Select onValueChange={setPriority} value={priority}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Urgency
                    </label>
                    <Select onValueChange={setUrgency} value={urgency}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="urgent">Urgent</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Execute Button */}
                <Button
                  onClick={handleExecuteWorkflow}
                  disabled={executeWorkflowMutation.isPending || !selectedInputType || !workflowContent.trim()}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {executeWorkflowMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Executing...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Execute Workflow
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Current Execution */}
            {currentExecution && (
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    {getStatusIcon(currentExecution.status)}
                    Current Execution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-300">Type</span>
                      <Badge className="bg-slate-700 text-slate-200">
                        {currentExecution.input_type.replace(/_/g, ' ')}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-300">Status</span>
                      <Badge className={getStatusColor(currentExecution.status)}>
                        {currentExecution.status}
                      </Badge>
                    </div>
                    <div className="text-sm text-slate-400">
                      Started: {currentExecution.startTime.toLocaleTimeString()}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Execution Results */}
            {executionHistory.length > 0 && (
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Execution History</CardTitle>
                  <CardDescription className="text-slate-400">
                    Recent workflow executions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {executionHistory.map((execution) => (
                      <div key={execution.id} className="border border-slate-700 rounded-lg p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(execution.status)}
                            <span className="text-slate-300 font-medium">
                              {execution.input_type.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <Badge className={getStatusColor(execution.status)}>
                            {execution.status}
                          </Badge>
                        </div>
                        <div className="text-sm text-slate-400 mb-3">
                          {execution.content.substring(0, 100)}...
                        </div>
                        {execution.result && (
                          <div className="bg-slate-900 p-3 rounded text-sm text-slate-300 mb-2 max-h-96 overflow-y-auto">
                            <pre className="whitespace-pre-wrap">{execution.result}</pre>
                          </div>
                        )}
                        {execution.error && (
                          <Alert className="bg-red-900/20 border-red-700">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription className="text-red-200">
                              {execution.error}
                            </AlertDescription>
                          </Alert>
                        )}
                        <div className="flex justify-between text-xs text-slate-500 mt-2">
                          <span>Started: {execution.startTime.toLocaleTimeString()}</span>
                          {execution.endTime && (
                            <span>Duration: {Math.max(0, Math.round((execution.endTime.getTime() - execution.startTime.getTime()) / 1000))}s</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Active Workflows */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-400" />
                  Active Workflows
                </CardTitle>
              </CardHeader>
              <CardContent>
                {activeWorkflows && activeWorkflows.count > 0 ? (
                  <div className="space-y-3">
                    {activeWorkflows.active_workflows.slice(0, 5).map((workflow) => (
                      <div key={workflow.workflow_id} className="flex items-center gap-3 p-2 bg-slate-900 rounded">
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-slate-300 truncate">
                            {workflow.goal || 'Workflow in progress'}
                          </div>
                          <div className="text-xs text-slate-500">
                            {new Date(workflow.created_at).toLocaleTimeString()}
                          </div>
                        </div>
                        <Badge className="text-xs bg-blue-900 text-blue-200">
                          {workflow.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-slate-400 text-center py-4">
                    No active workflows
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Settings className="w-5 h-5 text-slate-400" />
                  Quick Stats
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Available Types</span>
                  <span className="text-slate-300">{inputTypes?.length || 4}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Strategies</span>
                  <span className="text-slate-300">{strategies?.length || 5}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Active Count</span>
                  <span className="text-slate-300">{activeWorkflows?.count || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">History Count</span>
                  <span className="text-slate-300">{executionHistory.length}</span>
                </div>
              </CardContent>
            </Card>

            {/* Help */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-400" />
                  Workflow Tips
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-slate-400 space-y-2">
                <p>• Be specific in your prompts for better results</p>
                <p>• Higher priority workflows execute first</p>
                <p>• Complex tasks may take longer to process</p>
                <p>• Check execution history for insights</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}