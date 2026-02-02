/**
 * TypeScript interfaces for NYX API integration
 */

// System Status Types
export interface SystemStatus {
  timestamp: string
  uptime: string
  version: string
  environment: string
  database: {
    status: string
    connection_pool: string
    last_check: string
  }
  components: {
    fastapi: {
      status: string
      version: string
    }
  }
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  version: string
  service: string
  components: {
    database: {
      status: string
      connection: string
    }
    system: {
      status: string
      response_time_ms: number
    }
  }
}

// Engine Types
export interface EngineConfig {
  evaluation_interval?: number
  max_concurrent_tasks?: number
  min_arbitration_threshold?: number
  safety_enabled?: boolean
  test_mode?: boolean
}

export interface EngineStatus {
  running: boolean
  evaluation_interval: number
  max_concurrent_tasks: number
  min_arbitration_threshold: number
  safety_enabled: boolean
  timestamp: string
}

// Motivational System Types
export interface MotivationalState {
  motivation_type: string
  urgency: number
  satisfaction: number
  arbitration_score: number
  success_rate: number
  total_attempts: number
  success_count: number
  failure_count: number
  is_active: boolean
  last_triggered: string | null
  last_satisfied: string | null
  decay_rate: number
  boost_factor: number
  max_urgency: number
  timestamp: string
}

export interface MotivationalStates {
  total_active_states: number
  states: MotivationalState[]
  timestamp: string
  engine_running: boolean
}

export interface MotivationBoostRequest {
  boost_amount: number
  reason?: string
  metadata?: Record<string, unknown>
}

export interface MotivationalTask {
  task_id: string
  motivation_type: string
  generated_prompt: string
  status: string
  task_priority: number
  arbitration_score: number
  spawned_at: string
  started_at: string | null
  completed_at: string | null
  success: boolean | null
  outcome_score: number | null
}

// Workflow Types
export interface WorkflowRequest {
  input_type: string
  content: Record<string, unknown>
  execution_context?: Record<string, unknown>
  domain_context?: Record<string, unknown>
  user_context?: Record<string, unknown>
  historical_context?: Record<string, unknown>
  priority?: string
  urgency?: string
}

export interface WorkflowResponse {
  success: boolean
  content: string
  metadata: Record<string, unknown>
  execution_time_ms: number
  cost_usd: number
  workflow_id: string | null
  timestamp: string
}

export interface WorkflowStatus {
  workflow_id: string
  status: string
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}

export interface WorkflowSummary {
  workflow_id: string
  status: string
  goal: string
  created_at: string
  updated_at: string
  depth: number
  importance_level: string
}

// API Response Types
export interface APIResponse<T> {
  data: T
  error?: string
  timestamp?: string
}

export interface APIError {
  error: boolean
  error_code: string
  detail: string
  metadata?: Record<string, unknown>
  timestamp: string
  path: string
}

// Authentication Types
export interface AuthState {
  apiKey: string | null
  isAuthenticated: boolean
  connectionStatus: 'connected' | 'disconnected' | 'connecting'
}

// UI State Types
export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
}

export interface UserSettings {
  refreshInterval: number
  showNotifications: boolean
  theme: 'light' | 'dark'
  dashboardLayout: string[]
}

// Social Types
export interface SocialPost {
  id: string
  title: string
  content: string
  url: string
  created_at: string
  engagement: {
    upvotes: number
    downvotes: number
    comments: number
  }
}

export interface SocialComment {
  id: string
  content: string
  post_url: string
  created_at: string
  context: string
  type: 'comment' | 'reply'
}

export interface SocialMetrics {
  cycles_since_last_post: number
  claims_corrected_since_last_post: number
  posts_this_hour: number
  max_posts_per_hour: number
  last_post_time: string | null
  total_posts: number
  total_comments: number
  timestamp: string
}