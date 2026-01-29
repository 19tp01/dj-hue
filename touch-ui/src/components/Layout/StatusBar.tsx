import { useEffect, useState } from 'react'
import type { DJHueStatus } from '../../hooks/useWebSocket'

interface StatusBarProps {
  status: DJHueStatus | null
  connected: boolean
  error: string | null
  onSettingsClick?: () => void
  onPatternsClick?: () => void
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
      className="w-5 h-5"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

function EditIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-5 h-5"
    >
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

function BeatMeter({ beatInBar }: { beatInBar: number }) {
  const [pulse, setPulse] = useState(false)

  // Trigger pulse animation on beat 1
  useEffect(() => {
    if (beatInBar === 1) {
      setPulse(true)
      const timer = setTimeout(() => setPulse(false), 150)
      return () => clearTimeout(timer)
    }
  }, [beatInBar])

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4].map((beat) => (
        <div
          key={beat}
          className={`
            h-6 w-3 rounded-sm transition-all duration-75
            ${beat <= beatInBar
              ? beat === 1
                ? `bg-[var(--accent-bright)] ${pulse ? 'animate-beat' : ''}`
                : 'bg-[var(--accent-mid)]'
              : 'bg-[var(--bg-interactive)]'
            }
          `}
          style={{
            boxShadow: beat <= beatInBar ? 'var(--glow-cyan)' : 'none',
          }}
        />
      ))}
    </div>
  )
}

export function StatusBar({ status, connected, error, onSettingsClick, onPatternsClick }: StatusBarProps) {
  const bpm = status?.bpm ?? 120
  const bar = status?.bar ?? 1
  const beatInBar = status?.beat_in_bar ?? 1
  const patternName = status?.pattern_name ?? '-'

  // Disconnected state - full width error bar
  if (!connected) {
    return (
      <header className="h-full flex items-center justify-center px-4"
        style={{ background: 'var(--status-error-bg)' }}>
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-[var(--status-error)] animate-pulse" />
          <span className="text-[var(--status-error)] font-medium text-sm tracking-wide">
            DISCONNECTED — RECONNECTING
          </span>
        </div>
      </header>
    )
  }

  return (
    <header className="h-full flex items-center justify-between px-4">
      {/* Error toast - slides in from top if present */}
      {error && (
        <div className="absolute top-full left-0 right-0 z-50 px-4 py-2"
          style={{ background: 'var(--status-error-bg)' }}>
          <p className="text-[var(--status-error)] text-sm text-center">{error}</p>
        </div>
      )}

      {/* Left: Connection + BPM */}
      <div className="flex items-center gap-4">
        <div className="w-2 h-2 rounded-full bg-emerald-500"
          style={{ boxShadow: '0 0 8px rgba(16, 185, 129, 0.6)' }} />
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-semibold tabular-nums"
            style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
            {bpm.toFixed(0)}
          </span>
          <span className="text-xs uppercase tracking-wider"
            style={{ color: 'var(--text-muted)' }}>
            BPM
          </span>
        </div>
      </div>

      {/* Center: Beat position */}
      <div className="flex items-center gap-4">
        <div className="flex items-baseline gap-1.5">
          <span className="text-sm uppercase tracking-wider"
            style={{ color: 'var(--text-muted)' }}>
            Bar
          </span>
          <span className="text-lg font-medium tabular-nums"
            style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
            {bar}
          </span>
        </div>
        <BeatMeter beatInBar={beatInBar} />
      </div>

      {/* Right: Now Playing + Buttons */}
      <div className="flex items-center gap-2">
        <div className="text-right mr-1">
          <span className="text-sm font-medium truncate block max-w-[120px]"
            style={{ color: 'var(--accent-glow)' }}>
            {patternName}
          </span>
        </div>
        {onPatternsClick && (
          <button
            onClick={onPatternsClick}
            className="p-2 rounded-lg transition-all duration-75 active:scale-95"
            style={{
              color: 'var(--text-muted)',
              background: 'transparent',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--text-primary)'
              e.currentTarget.style.background = 'var(--bg-interactive)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-muted)'
              e.currentTarget.style.background = 'transparent'
            }}
            aria-label="Edit Patterns"
          >
            <EditIcon />
          </button>
        )}
        {onSettingsClick && (
          <button
            onClick={onSettingsClick}
            className="p-2 rounded-lg transition-all duration-75 active:scale-95"
            style={{
              color: 'var(--text-muted)',
              background: 'transparent',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--text-primary)'
              e.currentTarget.style.background = 'var(--bg-interactive)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-muted)'
              e.currentTarget.style.background = 'transparent'
            }}
            aria-label="Settings"
          >
            <GearIcon />
          </button>
        )}
      </div>
    </header>
  )
}
