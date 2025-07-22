/**
 * React Query hooks for NYX API integration
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import nyxAPI from '@/services/api'
import { 
  EngineConfig, 
  MotivationBoostRequest,
  WorkflowRequest 
} from '@/types/nyx'

// Query keys
export const queryKeys = {
  health: ['health'] as const,
  systemStatus: ['system', 'status'] as const,
  systemInfo: ['system', 'info'] as const,
  engineStatus: ['engine', 'status'] as const,
  motivationalStates: ['motivational', 'states'] as const,
  motivationalState: (type: string) => ['motivational', 'states', type] as const,
  recentTasks: (limit: number) => ['motivational', 'tasks', 'recent', limit] as const,
  integrationStatus: ['motivational', 'integration', 'status'] as const,
  activeWorkflows: (limit: number, offset: number) => ['workflows', 'active', limit, offset] as const,
  workflowStatus: (id: string) => ['workflows', 'status', id] as const,
  workflowStrategies: ['workflows', 'strategies'] as const,
  inputTypes: ['workflows', 'input-types'] as const
}

// System hooks
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => nyxAPI.getHealth(),
    refetchInterval: 30000, // 30 seconds
    retry: 2
  })
}

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: () => nyxAPI.getSystemStatus(),
    refetchInterval: 5000, // 5 seconds
    retry: 2
  })
}

export function useSystemInfo() {
  return useQuery({
    queryKey: queryKeys.systemInfo,
    queryFn: () => nyxAPI.getSystemInfo(),
    staleTime: 300000, // 5 minutes
    retry: 2
  })
}

// Engine hooks
export function useEngineStatus() {
  return useQuery({
    queryKey: queryKeys.engineStatus,
    queryFn: () => nyxAPI.getEngineStatus(),
    refetchInterval: 2000, // 2 seconds
    retry: 2
  })
}

export function useStartEngine() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (config?: EngineConfig) => nyxAPI.startEngine(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.engineStatus })
      queryClient.invalidateQueries({ queryKey: queryKeys.integrationStatus })
    }
  })
}

export function useStopEngine() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => nyxAPI.stopEngine(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.engineStatus })
      queryClient.invalidateQueries({ queryKey: queryKeys.integrationStatus })
    }
  })
}

// Motivational system hooks
export function useMotivationalStates() {
  return useQuery({
    queryKey: queryKeys.motivationalStates,
    queryFn: () => nyxAPI.getMotivationalStates(),
    refetchInterval: 3000, // 3 seconds
    retry: 2
  })
}

export function useMotivationalState(motivationType: string) {
  return useQuery({
    queryKey: queryKeys.motivationalState(motivationType),
    queryFn: () => nyxAPI.getMotivationalState(motivationType),
    refetchInterval: 5000,
    retry: 2,
    enabled: !!motivationType
  })
}

export function useBoostMotivation() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ motivationType, request }: { 
      motivationType: string
      request: MotivationBoostRequest 
    }) => nyxAPI.boostMotivation(motivationType, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.motivationalStates })
    }
  })
}

export function useRecentTasks(limit: number = 10) {
  return useQuery({
    queryKey: queryKeys.recentTasks(limit),
    queryFn: () => nyxAPI.getRecentTasks(limit),
    refetchInterval: 2000, // 2 seconds
    retry: 2
  })
}

export function useIntegrationStatus() {
  return useQuery({
    queryKey: queryKeys.integrationStatus,
    queryFn: () => nyxAPI.getIntegrationStatus(),
    refetchInterval: 5000, // 5 seconds
    retry: 2
  })
}

// Workflow hooks
export function useExecuteWorkflow() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (request: WorkflowRequest) => nyxAPI.executeWorkflow(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    }
  })
}

export function useActiveWorkflows(limit: number = 10, offset: number = 0) {
  return useQuery({
    queryKey: queryKeys.activeWorkflows(limit, offset),
    queryFn: () => nyxAPI.getActiveWorkflows(limit, offset),
    refetchInterval: 5000, // 5 seconds
    retry: 2
  })
}

export function useWorkflowStatus(workflowId: string) {
  return useQuery({
    queryKey: queryKeys.workflowStatus(workflowId),
    queryFn: () => nyxAPI.getWorkflowStatus(workflowId),
    refetchInterval: 2000, // 2 seconds
    retry: 2,
    enabled: !!workflowId
  })
}

export function useWorkflowStrategies() {
  return useQuery({
    queryKey: queryKeys.workflowStrategies,
    queryFn: () => nyxAPI.getWorkflowStrategies(),
    staleTime: 300000, // 5 minutes - strategies don't change often
    retry: 2
  })
}

export function useInputTypes() {
  return useQuery({
    queryKey: queryKeys.inputTypes,
    queryFn: () => nyxAPI.getInputTypes(),
    staleTime: 300000, // 5 minutes - input types don't change often
    retry: 2
  })
}