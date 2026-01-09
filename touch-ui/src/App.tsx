import { useCallback } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { StatusBar } from './components/StatusBar'
import { PatternGrid } from './components/PatternGrid'
import { PaletteGrid } from './components/PaletteGrid'
import { Controls } from './components/Controls'

function App() {
  const { status, error, connected, send } = useWebSocket()

  const handlePatternSelect = useCallback((index: number) => {
    send({ type: 'set_pattern', index })
  }, [send])

  const handlePaletteSelect = useCallback((name: string | null) => {
    send({ type: 'set_palette', name })
  }, [send])

  const handleTapTempo = useCallback(() => {
    send({ type: 'tap_tempo' })
  }, [send])

  const handleSync = useCallback(() => {
    send({ type: 'sync' })
  }, [send])

  const handleStart = useCallback(() => {
    send({ type: 'start' })
  }, [send])

  const handleStop = useCallback(() => {
    send({ type: 'stop' })
  }, [send])

  const handleBlackout = useCallback(() => {
    send({ type: 'toggle_blackout' })
  }, [send])

  const handleFlash = useCallback(() => {
    send({ type: 'flash', duration_beats: 0.5 })
  }, [send])

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex flex-col">
      <StatusBar status={status} connected={connected} error={error} />

      <main className="flex-1 overflow-y-auto p-4 space-y-6">
        <PatternGrid
          patterns={status?.patterns ?? []}
          currentIndex={status?.pattern_index ?? 0}
          onSelect={handlePatternSelect}
        />

        <PaletteGrid
          palettes={status?.palettes ?? []}
          currentPalette={status?.palette_name ?? null}
          hasOverride={status?.palette_override ?? false}
          onSelect={handlePaletteSelect}
        />
      </main>

      <Controls
        blackout={status?.blackout ?? false}
        onTapTempo={handleTapTempo}
        onSync={handleSync}
        onStart={handleStart}
        onStop={handleStop}
        onBlackout={handleBlackout}
        onFlash={handleFlash}
      />
    </div>
  )
}

export default App
