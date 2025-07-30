/**
 * Authentication hook for NYX dashboard
 */

import { useState, useCallback, useEffect, useRef } from 'react'
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
  const initializedRef = useRef(false)

  // Load API key from cookies on mount
  useEffect(() => {
    const initializeAuth = async () => {
      if (initializedRef.current) {
        console.log('useEffect: Already initialized, skipping')
        return
      }
      initializedRef.current = true
      
      const savedApiKey = Cookies.get(AUTH_COOKIE_KEY)
      console.log('useEffect: Checking for saved API key:', savedApiKey)
      if (savedApiKey) {
        setAuthState(prev => ({
          ...prev,
          apiKey: savedApiKey,
          connectionStatus: 'connecting'
        }))
        nyxAPI.setApiKey(savedApiKey)
        
        // Test the connection
        await testConnection(savedApiKey)
      }
    }
    
    initializeAuth()
  }, []) // Keep empty dependency array for initialization

  const testConnection = useCallback(async (apiKey: string) => {
    try {
      console.log('Testing connection with API key:', apiKey)
      setAuthState(prev => ({ ...prev, connectionStatus: 'connecting' }))
      
      nyxAPI.setApiKey(apiKey)
      const isConnected = await nyxAPI.testConnection()
      console.log('API test connection result:', isConnected)
      
      if (isConnected) {
        const newState = {
          apiKey,
          isAuthenticated: true,
          connectionStatus: 'connected' as const
        }
        console.log('Setting auth state to connected:', newState)
        setAuthState(newState)
        return true
      } else {
        console.log('Connection failed, clearing auth state')
        setAuthState({
          apiKey: null,
          isAuthenticated: false,
          connectionStatus: 'disconnected'
        })
        nyxAPI.setApiKey(null)
        Cookies.remove(AUTH_COOKIE_KEY)
        return false
      }
    } catch (error) {
      console.log('Connection test threw error:', error)
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
    console.log('Login attempt with API key:', apiKey)
    const success = await testConnection(apiKey)
    console.log('Connection test result:', success)
    if (success) {
      // Store API key in cookie (7 days) - disable secure for development
      Cookies.set(AUTH_COOKIE_KEY, apiKey, { 
        expires: 7, 
        secure: false, // Set to true in production with HTTPS
        sameSite: 'lax' 
      })
      console.log('Cookie stored, auth state:', {
        apiKey,
        isAuthenticated: true,
        connectionStatus: 'connected'
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