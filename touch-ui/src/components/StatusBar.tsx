import type { DJHueStatus } from '../hooks/useWebSocket'

interface StatusBarProps {
  status: DJHueStatus | null
  connected: boolean
  error: string | null
}

export function StatusBar({ status, connected, error }: StatusBarProps) {
  const bpm = status?.bpm ?? 120
  const beatInBar = status?.beat_in_bar ?? 1
  const patternName = status?.pattern_name ?? '-'
  const paletteName = status?.palette_name ?? 'Default'

  return (
    <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3">
      {/* Connection status */}
      {!connected && (
        <div className="bg-red-900/50 text-red-200 text-center py-2 mb-3 rounded">
          Disconnected - Reconnecting...
        </div>
      )}
      {error && (
        <div className="bg-yellow-900/50 text-yellow-200 text-center py-2 mb-3 rounded text-sm">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between">
        {/* BPM */}
        <div className="text-3xl font-bold text-white tabular-nums">
          {bpm.toFixed(0)}
          <span className="text-lg text-zinc-500 ml-1">BPM</span>
        </div>

        {/* Beat indicator - 4 dots */}
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((beat) => (
            <div
              key={beat}
              className={`w-4 h-4 rounded-full transition-all duration-75 ${
                beat <= beatInBar
                  ? 'bg-cyan-400 shadow-lg shadow-cyan-400/50'
                  : 'bg-zinc-700'
              }`}
            />
          ))}
        </div>

        {/* Current info */}
        <div className="text-right">
          <div className="text-white font-medium truncate max-w-[150px]">
            {patternName}
          </div>
          <div className="text-zinc-500 text-sm truncate max-w-[150px]">
            {paletteName}
          </div>
        </div>
      </div>
    </header>
  )
}
