/**
 * Authentication hook for NYX dashboard
 */

import { useState, useCallback, useEffect } from 'react'
import { AuthState } from '@/types/nyx'
import nyxAPI from '@/services/api'
import Cookies from 'js-cookie'

const AUTH_COOKIE_KEY = 'nyx_api_key'

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    apiKey: null,
    isAuthenticated: false,
    connectionStatus: 'disconnected'
  })

  // Load API key from cookies on mount
  useEffect(() => {
    const savedApiKey = Cookies.get(AUTH_COOKIE_KEY)
    if (savedApiKey) {
      setAuthState(prev => ({
        ...prev,
        apiKey: savedApiKey,
        connectionStatus: 'connecting'
      }))
      nyxAPI.setApiKey(savedApiKey)
      
      // Test the connection
      testConnection(savedApiKey)
    }
  }, [])

  const testConnection = useCallback(async (apiKey: string) => {
    try {
      setAuthState(prev => ({ ...prev, connectionStatus: 'connecting' }))
      
      nyxAPI.setApiKey(apiKey)
      const isConnected = await nyxAPI.testConnection()
      
      if (isConnected) {
        setAuthState({
          apiKey,
          isAuthenticated: true,
          connectionStatus: 'connected'
        })
        return true
      } else {
        setAuthState({
          apiKey: null,
          isAuthenticated: false,
          connectionStatus: 'disconnected'
        })
        nyxAPI.setApiKey(null)
        Cookies.remove(AUTH_COOKIE_KEY)
        return false
      }
    } catch {
      setAuthState({
        apiKey: null,
        isAuthenticated: false,
        connectionStatus: 'disconnected'
      })
      nyxAPI.setApiKey(null)
      Cookies.remove(AUTH_COOKIE_KEY)
      return false
    }
  }, [])

  const login = useCallback(async (apiKey: string): Promise<boolean> => {
    const success = await testConnection(apiKey)
    if (success) {
      // Store API key in secure cookie (7 days)
      Cookies.set(AUTH_COOKIE_KEY, apiKey, { 
        expires: 7, 
        secure: true, 
        sameSite: 'strict' 
      })
    }
    return success
  }, [testConnection])

  const logout = useCallback(() => {
    setAuthState({
      apiKey: null,
      isAuthenticated: false,
      connectionStatus: 'disconnected'
    })
    nyxAPI.setApiKey(null)
    Cookies.remove(AUTH_COOKIE_KEY)
  }, [])

  const refreshConnection = useCallback(async () => {
    if (authState.apiKey) {
      return await testConnection(authState.apiKey)
    }
    return false
  }, [authState.apiKey, testConnection])

  return {
    ...authState,
    login,
    logout,
    refreshConnection,
    testConnection
  }
}