/**
 * NYX API Client for frontend integration
 */

import axios, { AxiosInstance } from 'axios'
import {
  SystemStatus,
  HealthStatus,
  EngineConfig,
  EngineStatus,
  MotivationalStates,
  MotivationalState,
  MotivationBoostRequest,
  MotivationalTask,
  WorkflowRequest,
  WorkflowResponse,
  WorkflowStatus,
  WorkflowSummary,
  APIError
} from '@/types/nyx'

class NYXAPIClient {
  private client: AxiosInstance
  private apiKey: string | null = null

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    console.log('NYX API Client initialized with baseURL:', baseURL)
    console.log('NEXT_PUBLIC_API_URL env var:', process.env.NEXT_PUBLIC_API_URL)
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // Request interceptor to add API key
    this.client.interceptors.request.use((config) => {
      if (this.apiKey) {
        config.headers['X-API-Key'] = this.apiKey
      }
      return config
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized - clear API key
          this.setApiKey(null)
        }
        throw error
      }
    )
  }

  setApiKey(apiKey: string | null) {
    this.apiKey = apiKey
  }

  getApiKey(): string | null {
    return this.apiKey
  }

  // System Management
  async getHealth(): Promise<HealthStatus> {
    const response = await this.client.get<HealthStatus>('/health')
    return response.data
  }

  async getSystemStatus(): Promise<SystemStatus> {
    const response = await this.client.get<SystemStatus>('/api/v1/system/status')
    return response.data
  }

  async getSystemInfo(): Promise<SystemStatus> {
    const response = await this.client.get('/api/v1/system/info')
    return response.data
  }

  // Engine Control
  async startEngine(config?: EngineConfig): Promise<{ success: boolean; message?: string }> {
    const response = await this.client.post('/api/v1/motivational/engine/start', config)
    return response.data
  }

  async stopEngine(): Promise<{ success: boolean; message?: string }> {
    const response = await this.client.post('/api/v1/motivational/engine/stop')
    return response.data
  }

  async getEngineStatus(): Promise<EngineStatus> {
    const response = await this.client.get<EngineStatus>('/api/v1/motivational/engine/status')
    return response.data
  }

  // Motivational System
  async getMotivationalStates(): Promise<MotivationalStates> {
    const response = await this.client.get<MotivationalStates>('/api/v1/motivational/states')
    return response.data
  }

  async getMotivationalState(motivationType: string): Promise<MotivationalState> {
    const response = await this.client.get<MotivationalState>(`/api/v1/motivational/states/${motivationType}`)
    return response.data
  }

  async boostMotivation(motivationType: string, request: MotivationBoostRequest): Promise<MotivationalState> {
    const response = await this.client.post(`/api/v1/motivational/states/${motivationType}/boost`, request)
    return response.data
  }

  async getRecentTasks(limit: number = 10): Promise<{ recent_tasks: MotivationalTask[], count: number }> {
    const response = await this.client.get(`/api/v1/motivational/tasks/recent?limit=${limit}`)
    return response.data
  }

  async getIntegrationStatus(): Promise<Record<string, unknown>> {
    const response = await this.client.get('/api/v1/motivational/integration/status')
    return response.data
  }

  // Workflow Management
  async executeWorkflow(request: WorkflowRequest): Promise<WorkflowResponse> {
    const response = await this.client.post<WorkflowResponse>('/api/v1/orchestrator/workflows/execute', request)
    return response.data
  }

  async getWorkflowStatus(workflowId: string): Promise<WorkflowStatus> {
    const response = await this.client.get<WorkflowStatus>(`/api/v1/orchestrator/workflows/${workflowId}/status`)
    return response.data
  }

  async getActiveWorkflows(limit: number = 10, offset: number = 0): Promise<{ active_workflows: WorkflowSummary[], count: number }> {
    const response = await this.client.get(`/api/v1/orchestrator/workflows/active?limit=${limit}&offset=${offset}`)
    return response.data
  }

  async getWorkflowStrategies(): Promise<string[]> {
    const response = await this.client.get('/api/v1/orchestrator/strategies')
    return response.data
  }

  async getInputTypes(): Promise<string[]> {
    const response = await this.client.get('/api/v1/orchestrator/input-types')
    return response.data
  }

  // Connection Testing
  async testConnection(): Promise<boolean> {
    try {
      await this.getHealth()
      return true
    } catch {
      return false
    }
  }
}

// Create singleton instance
const nyxAPI = new NYXAPIClient()

export default nyxAPI
export { NYXAPIClient, nyxAPI }
export type { APIError }