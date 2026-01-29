import type { DJHueStatus } from '../hooks/useWebSocket'

interface StatusBarProps {
  status: DJHueStatus | null
  connected: boolean
  error: string | null
  onSettingsClick?: () => void
}

function GearIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-6 h-6"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export function StatusBar({ status, connected, error, onSettingsClick }: StatusBarProps) {
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

        {/* Current info + Settings */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-white font-medium truncate max-w-[120px]">
              {patternName}
            </div>
            <div className="text-zinc-500 text-sm truncate max-w-[120px]">
              {paletteName}
            </div>
          </div>
          {onSettingsClick && (
            <button
              onClick={onSettingsClick}
              className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors active:scale-95"
              aria-label="Settings"
            >
              <GearIcon />
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
