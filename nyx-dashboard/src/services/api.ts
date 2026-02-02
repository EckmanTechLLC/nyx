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
  SocialPost,
  SocialComment,
  SocialMetrics,
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
      timeout: 300000, // 5 minutes for long-running workflows
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

  async updateEngineConfig(config: EngineConfig): Promise<{ success: boolean; message?: string }> {
    const response = await this.client.put('/api/v1/motivational/engine/config', config)
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
    return response.data.strategies ? Object.keys(response.data.strategies) : []
  }

  async getInputTypes(): Promise<string[]> {
    const response = await this.client.get('/api/v1/orchestrator/input-types')
    return response.data.input_types ? Object.keys(response.data.input_types) : []
  }

  // Social Monitoring
  async getSocialPosts(limit: number = 50): Promise<{ posts: SocialPost[]; total: number; timestamp: string }> {
    const response = await this.client.get(`/api/v1/social/posts?limit=${limit}`)
    return response.data
  }

  async getSocialComments(limit: number = 100): Promise<{ comments: SocialComment[]; total: number; timestamp: string }> {
    const response = await this.client.get(`/api/v1/social/comments?limit=${limit}`)
    return response.data
  }

  async getSocialMetrics(): Promise<SocialMetrics> {
    const response = await this.client.get<SocialMetrics>('/api/v1/social/metrics')
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