import { useState, useEffect, useRef, useCallback } from 'react'

export interface ZoneBrightness {
  ceiling: number
  perimeter: number
  ambient: number
}

// Pattern info can be string (legacy) or object with tags (new format)
export interface PatternInfo {
  name: string
  tags: string[]
  description?: string
}

// Palette info with color previews
export interface PaletteInfo {
  name: string
  colors?: string[]
}

export interface DJHueStatus {
  type: 'status'
  bpm: number
  beat_position: number
  bar: number
  beat_in_bar: number
  pattern_index: number
  pattern_name: string
  palette_name: string | null
  palette_override: boolean
  zone_brightness: ZoneBrightness
  fade_active: boolean
  queue_mode: 0 | 1 | 2
  queued_pattern_index: number | null
  queue_target_bar: number | null
  patterns: (string | PatternInfo)[]  // Supports both formats
  palettes: PaletteInfo[]
}

export interface DJHueError {
  type: 'error'
  message: string
}

// Light configuration types
export interface LightInfo {
  rid: string
  name: string
  index: number
  api_channel: number
  groups: string[]
}

export interface LightConfig {
  type: 'light_config'
  lights: LightInfo[]
  groups: Record<string, number[]>
  light_order: string[]
  custom_groups: Record<string, string[]>
  zones: Record<string, string[]>
}

export interface LightConfigSaved {
  type: 'light_config_saved'
  success: boolean
  message: string
}

// Pattern editing types
export interface PatternListItem {
  filename: string
  name: string
  description: string
  tags: string[]
  palette: string | null
  category: 'Ambient' | 'Buildup' | 'Chill' | 'Upbeat'
}

export interface PatternList {
  type: 'pattern_list'
  patterns: PatternListItem[]
}

export interface PatternSource {
  type: 'pattern_source'
  success: boolean
  error?: string
  filename?: string
  name?: string
  description?: string
  tags?: string[]
  palette?: string | null
  body?: string
}

export interface PatternSaved {
  type: 'pattern_saved'
  success: boolean
  filename?: string
  message?: string
  error?: string
}

export interface PatternDeleted {
  type: 'pattern_deleted'
  success: boolean
  message?: string
  error?: string
}

export interface PatternValidated {
  type: 'pattern_validated'
  valid: boolean
  error?: string
}

export type DJHueMessage = DJHueStatus | DJHueError | LightConfig | LightConfigSaved | PatternList | PatternSource | PatternSaved | PatternDeleted | PatternValidated

export type DJHueCommand =
  | { type: 'set_pattern'; index?: number; name?: string }
  | { type: 'set_palette'; name?: string | null }
  | { type: 'flash'; duration_beats?: number }
  | { type: 'tap_tempo' }
  | { type: 'sync' }
  | { type: 'start' }
  | { type: 'stop' }
  | { type: 'get_status' }
  | { type: 'get_light_config' }
  | { type: 'save_light_config'; light_order: string[]; custom_groups: Record<string, string[]>; zones: Record<string, string[]> }
  | { type: 'identify_light'; index: number }
  | { type: 'set_zone_brightness'; zone: 'ceiling' | 'perimeter' | 'ambient'; value: number }
  | { type: 'fade_out' }
  | { type: 'set_queue_mode'; mode: 0 | 1 | 2 }
  // Pattern CRUD commands
  | { type: 'get_pattern_list' }
  | { type: 'get_pattern_source'; name: string }
  | { type: 'save_pattern'; filename?: string; name: string; description?: string; tags?: string[]; palette?: string | null; category?: 'Ambient' | 'Buildup' | 'Chill' | 'Upbeat'; body?: string }
  | { type: 'delete_pattern'; name: string }
  | { type: 'validate_pattern'; body: string }

interface UseWebSocketReturn {
  status: DJHueStatus | null
  lightConfig: LightConfig | null
  lightConfigSaved: LightConfigSaved | null
  patternList: PatternListItem[] | null
  patternSource: PatternSource | null
  patternSaved: PatternSaved | null
  patternDeleted: PatternDeleted | null
  patternValidated: PatternValidated | null
  error: string | null
  connected: boolean
  send: (command: DJHueCommand) => void
  clearLightConfigSaved: () => void
  clearPatternSource: () => void
  clearPatternSaved: () => void
  clearPatternDeleted: () => void
  clearPatternValidated: () => void
}

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<DJHueStatus | null>(null)
  const [lightConfig, setLightConfig] = useState<LightConfig | null>(null)
  const [lightConfigSaved, setLightConfigSaved] = useState<LightConfigSaved | null>(null)
  const [patternList, setPatternList] = useState<PatternListItem[] | null>(null)
  const [patternSource, setPatternSource] = useState<PatternSource | null>(null)
  const [patternSaved, setPatternSaved] = useState<PatternSaved | null>(null)
  const [patternDeleted, setPatternDeleted] = useState<PatternDeleted | null>(null)
  const [patternValidated, setPatternValidated] = useState<PatternValidated | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  const connect = useCallback(() => {
    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`

    console.log('[WS] Connecting to', wsUrl)
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('[WS] Connected')
      setConnected(true)
      setError(null)
    }

    ws.onclose = () => {
      console.log('[WS] Disconnected')
      setConnected(false)
      wsRef.current = null

      // Reconnect after delay
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      reconnectTimeoutRef.current = window.setTimeout(() => {
        console.log('[WS] Reconnecting...')
        connect()
      }, 1000)
    }

    ws.onerror = (e) => {
      console.error('[WS] Error:', e)
      setError('WebSocket error')
    }

    ws.onmessage = (event) => {
      try {
        const data: DJHueMessage = JSON.parse(event.data)
        if (data.type === 'status') {
          setStatus(data)
          setError(null)
        } else if (data.type === 'error') {
          setError(data.message)
        } else if (data.type === 'light_config') {
          setLightConfig(data)
        } else if (data.type === 'light_config_saved') {
          setLightConfigSaved(data)
        } else if (data.type === 'pattern_list') {
          setPatternList(data.patterns)
        } else if (data.type === 'pattern_source') {
          setPatternSource(data)
        } else if (data.type === 'pattern_saved') {
          setPatternSaved(data)
        } else if (data.type === 'pattern_deleted') {
          setPatternDeleted(data)
        } else if (data.type === 'pattern_validated') {
          setPatternValidated(data)
        }
      } catch (e) {
        console.error('[WS] Parse error:', e)
      }
    }

    wsRef.current = ws
  }, [])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  const send = useCallback((command: DJHueCommand) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(command))
    }
  }, [])

  const clearLightConfigSaved = useCallback(() => {
    setLightConfigSaved(null)
  }, [])

  const clearPatternSource = useCallback(() => {
    setPatternSource(null)
  }, [])

  const clearPatternSaved = useCallback(() => {
    setPatternSaved(null)
  }, [])

  const clearPatternDeleted = useCallback(() => {
    setPatternDeleted(null)
  }, [])

  const clearPatternValidated = useCallback(() => {
    setPatternValidated(null)
  }, [])

  return {
    status,
    lightConfig,
    lightConfigSaved,
    patternList,
    patternSource,
    patternSaved,
    patternDeleted,
    patternValidated,
    error,
    connected,
    send,
    clearLightConfigSaved,
    clearPatternSource,
    clearPatternSaved,
    clearPatternDeleted,
    clearPatternValidated,
  }
}
