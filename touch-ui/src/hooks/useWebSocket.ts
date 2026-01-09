import { useState, useEffect, useRef, useCallback } from 'react'

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
  blackout: boolean
  patterns: string[]
  palettes: string[]
}

export interface DJHueError {
  type: 'error'
  message: string
}

export type DJHueMessage = DJHueStatus | DJHueError

export interface DJHueCommand {
  type: 'set_pattern' | 'set_palette' | 'toggle_blackout' | 'flash' | 'tap_tempo' | 'sync' | 'start' | 'stop' | 'get_status'
  index?: number
  name?: string | null
  duration_beats?: number
}

interface UseWebSocketReturn {
  status: DJHueStatus | null
  error: string | null
  connected: boolean
  send: (command: DJHueCommand) => void
}

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<DJHueStatus | null>(null)
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

  return { status, error, connected, send }
}
