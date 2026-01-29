import { memo, useCallback, useState, useRef } from 'react'

interface TransportControlsProps {
  onTapTempo: () => void
  onSync: () => void
  onFadeOut: () => void
  fadeActive: boolean
  queueMode: 0 | 1 | 2
  onQueueModeChange: (mode: 0 | 1 | 2) => void
}

export const TransportControls = memo(function TransportControls({
  onTapTempo,
  onSync,
  onFadeOut,
  fadeActive,
  queueMode,
  onQueueModeChange,
}: TransportControlsProps) {
  const [tapActive, setTapActive] = useState(false)
  const [syncActive, setSyncActive] = useState(false)
  const tapTimeoutRef = useRef<number | null>(null)
  const syncTimeoutRef = useRef<number | null>(null)

  const handleTap = useCallback(() => {
    onTapTempo()
    setTapActive(true)

    if (tapTimeoutRef.current) {
      clearTimeout(tapTimeoutRef.current)
    }
    tapTimeoutRef.current = window.setTimeout(() => {
      setTapActive(false)
    }, 100)
  }, [onTapTempo])

  const handleSync = useCallback(() => {
    onSync()
    setSyncActive(true)

    if (syncTimeoutRef.current) {
      clearTimeout(syncTimeoutRef.current)
    }
    syncTimeoutRef.current = window.setTimeout(() => {
      setSyncActive(false)
    }, 150)
  }, [onSync])

  return (
    <div className="flex flex-col gap-3">
      {/* TAP button */}
      <button
        onClick={handleTap}
        className="flex items-center justify-center rounded-lg font-bold text-lg uppercase tracking-wider transition-all duration-75 active:scale-95"
        style={{
          minHeight: '80px',
          height: '80px',
          flexShrink: 0,
          background: tapActive ? 'var(--bg-hover)' : 'var(--bg-interactive)',
          color: tapActive ? 'var(--text-primary)' : 'var(--text-secondary)',
          boxShadow: 'var(--shadow-button)',
        }}
      >
        TAP
      </button>

      {/* SYNC button */}
      <button
        onClick={handleSync}
        className="flex items-center justify-center rounded-lg font-bold text-lg uppercase tracking-wider transition-all duration-75 active:scale-95"
        style={{
          minHeight: '80px',
          height: '80px',
          flexShrink: 0,
          background: syncActive ? 'var(--sync-blue-hover)' : 'var(--sync-blue)',
          color: 'white',
          boxShadow: syncActive
            ? '0 0 20px rgba(59, 130, 246, 0.5)'
            : 'var(--shadow-button)',
        }}
      >
        SYNC
      </button>

      {/* FADE button */}
      <button
        onClick={onFadeOut}
        className="flex items-center justify-center rounded-lg font-bold text-lg uppercase tracking-wider transition-all duration-75 active:scale-95"
        style={{
          minHeight: '60px',
          height: '60px',
          flexShrink: 0,
          background: fadeActive ? '#b45309' : '#78350f',
          color: fadeActive ? '#fef3c7' : '#fbbf24',
          boxShadow: fadeActive
            ? '0 0 20px rgba(245, 158, 11, 0.4)'
            : 'var(--shadow-button)',
          opacity: fadeActive ? 0.7 : 1,
        }}
      >
        FADE
      </button>

      {/* Queue mode toggle */}
      <div
        className="flex rounded-lg overflow-hidden"
        style={{
          height: '40px',
          flexShrink: 0,
          background: 'var(--bg-surface)',
          border: '1px solid var(--bg-elevated)',
        }}
      >
        <button
          onClick={() => onQueueModeChange(0)}
          className="flex-1 font-bold text-xs uppercase tracking-wide transition-all duration-75"
          style={{
            background: queueMode === 0 ? 'var(--accent-mid)' : 'transparent',
            color: queueMode === 0 ? 'var(--bg-void)' : 'var(--text-muted)',
          }}
        >
          OFF
        </button>
        <button
          onClick={() => onQueueModeChange(1)}
          className="flex-1 font-bold text-xs uppercase tracking-wide transition-all duration-75"
          style={{
            background: queueMode === 1 ? 'var(--accent-mid)' : 'transparent',
            color: queueMode === 1 ? 'var(--bg-void)' : 'var(--text-muted)',
            borderLeft: '1px solid var(--bg-elevated)',
            borderRight: '1px solid var(--bg-elevated)',
          }}
        >
          1 BAR
        </button>
        <button
          onClick={() => onQueueModeChange(2)}
          className="flex-1 font-bold text-xs uppercase tracking-wide transition-all duration-75"
          style={{
            background: queueMode === 2 ? 'var(--accent-mid)' : 'transparent',
            color: queueMode === 2 ? 'var(--bg-void)' : 'var(--text-muted)',
          }}
        >
          2 BAR
        </button>
      </div>
    </div>
  )
})
