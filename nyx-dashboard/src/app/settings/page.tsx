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
import { useEngineStatus } from '@/hooks/useNYX'
import { toast } from 'react-hot-toast'
import { 
  Zap, 
  Shield,
  Download,
  Upload,
  Save,
  RotateCcw,
  AlertTriangle,
  CheckCircle
} from 'lucide-react'

interface EngineSettings {
  evaluation_interval: number
  max_concurrent_tasks: number
  min_arbitration_threshold: number
  safety_enabled: boolean
}

export default function SettingsPage() {
  const [hasChanges, setHasChanges] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  
  // Load real engine status
  const { data: engineStatus } = useEngineStatus()

  const [engineSettings, setEngineSettings] = useState<EngineSettings>({
    evaluation_interval: 30,
    max_concurrent_tasks: 5,
    min_arbitration_threshold: 0.1,
    safety_enabled: true
  })

  // Set default API key
  useEffect(() => {
    nyxAPI.setApiKey('nyx-dev-key-12345')
  }, [])

  // Load real engine configuration when engineStatus is available
  useEffect(() => {
    if (engineStatus) {
      setEngineSettings({
        evaluation_interval: engineStatus.evaluation_interval,
        max_concurrent_tasks: engineStatus.max_concurrent_tasks,
        min_arbitration_threshold: engineStatus.min_arbitration_threshold,
        safety_enabled: engineStatus.safety_enabled
      })
    }
  }, [engineStatus])

  const handleSaveSettings = async () => {
    setIsSaving(true)
    try {
      // Check if engine is running before trying to update config
      if (!engineStatus?.running) {
        toast.error('Engine must be running to update configuration. Please start the engine first.')
        return
      }

      // Save engine settings to the real backend
      await nyxAPI.updateEngineConfig({
        evaluation_interval: engineSettings.evaluation_interval,
        max_concurrent_tasks: engineSettings.max_concurrent_tasks,
        min_arbitration_threshold: engineSettings.min_arbitration_threshold,
        safety_enabled: engineSettings.safety_enabled
      })
      
      setHasChanges(false)
      toast.success('Engine configuration updated successfully!')
    } catch (error) {
      console.error('Settings save error:', error)
      
      // Provide specific error messages for common issues
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      if (errorMessage.includes('Engine not initialized') || errorMessage.includes('Engine not running')) {
        toast.error('Engine must be running to update configuration. Please start the engine first.')
      } else {
        toast.error(`Failed to update engine configuration: ${errorMessage}`)
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleResetToDefaults = () => {
    setEngineSettings({
      evaluation_interval: 30,
      max_concurrent_tasks: 5,
      min_arbitration_threshold: 0.3,
      safety_enabled: true
    })
    setHasChanges(true)
  }

  const exportSettings = () => {
    const settings = {
      engine: engineSettings,
      exportedAt: new Date().toISOString()
    }
    
    const dataStr = JSON.stringify(settings, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `nyx-engine-config-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const importSettings = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const settings = JSON.parse(e.target?.result as string)
        if (settings.engine) {
          setEngineSettings(settings.engine)
          setHasChanges(true)
          toast.success('Engine configuration imported successfully!')
        } else {
          toast.error('Invalid configuration file')
        }
      } catch (error) {
        toast.error('Invalid configuration file')
      }
    }
    reader.readAsText(file)
  }

  const markChanged = () => setHasChanges(true)

  return (
    <DashboardLayout>
      <div className="container mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Settings</h1>
            <p className="text-slate-400 mt-1">Configure NYX system preferences</p>
          </div>
          <div className="flex items-center gap-3">
            {hasChanges && (
              <Badge className="bg-yellow-900 text-yellow-200 border-yellow-700">
                Unsaved changes
              </Badge>
            )}
            <Button
              onClick={handleSaveSettings}
              disabled={!hasChanges || isSaving || !engineStatus?.running}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <Save className="w-4 h-4 mr-2" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>

        <div className="max-w-2xl mx-auto">
          {!engineStatus?.running && (
            <Card className="bg-yellow-900/20 border-yellow-700 mb-6">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-400" />
                  <div>
                    <p className="text-yellow-200 font-medium">Engine Not Running</p>
                    <p className="text-yellow-300/80 text-sm">
                      The NYX engine must be running to update configuration. Start the engine from the Dashboard.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                Engine Configuration
              </CardTitle>
              <CardDescription className="text-slate-400">
                Configure autonomous engine parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Evaluation Interval (seconds)
                  </label>
                  <Input
                    type="number"
                    value={engineSettings.evaluation_interval}
                    onChange={(e) => {
                      setEngineSettings(prev => ({...prev, evaluation_interval: parseInt(e.target.value)}))
                      markChanged()
                    }}
                    className="bg-slate-700 border-slate-600 text-white"
                  />
                  <p className="text-xs text-slate-400 mt-1">How often the engine evaluates motivational states</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Max Concurrent Tasks
                  </label>
                  <Input
                    type="number"
                    value={engineSettings.max_concurrent_tasks}
                    onChange={(e) => {
                      setEngineSettings(prev => ({...prev, max_concurrent_tasks: parseInt(e.target.value)}))
                      markChanged()
                    }}
                    className="bg-slate-700 border-slate-600 text-white"
                  />
                  <p className="text-xs text-slate-400 mt-1">Maximum number of tasks to run simultaneously</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Arbitration Threshold
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    value={engineSettings.min_arbitration_threshold}
                    onChange={(e) => {
                      setEngineSettings(prev => ({...prev, min_arbitration_threshold: parseFloat(e.target.value)}))
                      markChanged()
                    }}
                    className="bg-slate-700 border-slate-600 text-white"
                  />
                  <p className="text-xs text-slate-400 mt-1">Minimum threshold for task generation</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Safety Mode
                  </label>
                  <Select
                    value={engineSettings.safety_enabled ? 'enabled' : 'disabled'}
                    onValueChange={(value) => {
                      setEngineSettings(prev => ({...prev, safety_enabled: value === 'enabled'}))
                      markChanged()
                    }}
                  >
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="enabled">
                        <div className="flex items-center gap-2">
                          <Shield className="w-4 h-4 text-green-400" />
                          Enabled
                        </div>
                      </SelectItem>
                      <SelectItem value="disabled">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-yellow-400" />
                          Disabled
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-400 mt-1">Enable safety constraints for tool execution and task validation</p>
                </div>
              </div>
              
              <div className="flex gap-3 pt-4 border-t border-slate-700">
                <Button
                  variant="outline"
                  onClick={exportSettings}
                  className="bg-slate-700 border-slate-600 hover:bg-slate-600"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export Config
                </Button>
                <div className="relative">
                  <input
                    type="file"
                    accept=".json"
                    onChange={importSettings}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Button
                    variant="outline"
                    className="bg-slate-700 border-slate-600 hover:bg-slate-600"
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    Import Config
                  </Button>
                </div>
                <Button
                  variant="outline"
                  onClick={handleResetToDefaults}
                  className="bg-slate-700 border-slate-600 hover:bg-slate-600"
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Reset to Defaults
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}