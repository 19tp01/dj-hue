import { useCallback, useState, useMemo } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { usePatternBanks } from './hooks/usePatternBanks'
import { AppLayout, StatusBar } from './components/Layout'
import { BankTabs, PatternGrid } from './components/Patterns'
import { PaletteStrip } from './components/Palettes'
import { ZoneFaders } from './components/Faders'
import { TransportControls } from './components/Transport'
import { SettingsPage } from './components/Settings/SettingsPage'
import { PatternEditor } from './components/Settings/PatternEditor'
import type { PatternInfo, BankName, PaletteInfo } from './types'

const EMPTY_PALETTES: PaletteInfo[] = []

function App() {
  const {
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
  } = useWebSocket()
  const [page, setPage] = useState<'main' | 'settings' | 'patterns'>('main')

  // Normalize patterns to PatternInfo format
  const patterns = useMemo((): PatternInfo[] => {
    const rawPatterns = status?.patterns ?? []
    return rawPatterns.map((p): PatternInfo => {
      if (typeof p === 'string') {
        return { name: p, tags: [] }
      }
      return p as PatternInfo
    })
  }, [status?.patterns])

  // Use pattern banks hook
  const {
    currentBank,
    setCurrentBank,
    banks,
    activePatternBank,
  } = usePatternBanks(patterns, status?.pattern_index ?? 0)

  // Get patterns for current bank
  const currentBankPatterns = banks[currentBank]

  // Handlers
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

  const handleFadeOut = useCallback(() => {
    send({ type: 'fade_out' })
  }, [send])

  const handleQueueModeChange = useCallback((mode: 0 | 1 | 2) => {
    send({ type: 'set_queue_mode', mode })
  }, [send])

  const handleZoneBrightnessChange = useCallback((zone: 'ceiling' | 'perimeter' | 'ambient', value: number) => {
    send({ type: 'set_zone_brightness', zone, value })
  }, [send])

  const handleSettingsClick = useCallback(() => {
    setPage('settings')
  }, [])

  const handlePatternsClick = useCallback(() => {
    setPage('patterns')
  }, [])

  const handleBack = useCallback(() => {
    setPage('main')
  }, [])

  const handleBankChange = useCallback((bank: BankName) => {
    setCurrentBank(bank)
  }, [setCurrentBank])


  // Render settings page
  if (page === 'settings') {
    return (
      <SettingsPage
        lightConfig={lightConfig}
        lightConfigSaved={lightConfigSaved}
        onBack={handleBack}
        send={send}
        clearLightConfigSaved={clearLightConfigSaved}
      />
    )
  }

  // Render pattern editor page
  if (page === 'patterns') {
    return (
      <PatternEditor
        patternList={patternList}
        palettes={status?.palettes ?? EMPTY_PALETTES}
        patternSource={patternSource}
        patternSaved={patternSaved}
        patternDeleted={patternDeleted}
        patternValidated={patternValidated}
        onBack={handleBack}
        send={send}
        clearPatternSource={clearPatternSource}
        clearPatternSaved={clearPatternSaved}
        clearPatternDeleted={clearPatternDeleted}
        clearPatternValidated={clearPatternValidated}
      />
    )
  }

  // Render main page with new layout
  return (
    <AppLayout
      statusBar={
        <StatusBar
          status={status}
          connected={connected}
          error={error}
          onSettingsClick={handleSettingsClick}
          onPatternsClick={handlePatternsClick}
        />
      }
      bankTabs={
        <BankTabs
          currentBank={currentBank}
          activePatternBank={activePatternBank}
          onBankChange={handleBankChange}
        />
      }
      patternGrid={
        <PatternGrid
          patterns={currentBankPatterns}
          activePatternIndex={status?.pattern_index ?? -1}
          queuedPatternIndex={status?.queued_pattern_index ?? null}
          onPatternSelect={handlePatternSelect}
        />
      }
      paletteStrip={
        <PaletteStrip
          palettes={status?.palettes ?? EMPTY_PALETTES}
          currentPalette={status?.palette_name ?? null}
          hasOverride={status?.palette_override ?? false}
          onSelect={handlePaletteSelect}
        />
      }
      zoneFaders={
        <ZoneFaders
          zoneBrightness={status?.zone_brightness ?? { ceiling: 1, perimeter: 1, ambient: 1 }}
          onZoneBrightnessChange={handleZoneBrightnessChange}
        />
      }
      transport={
        <TransportControls
          onTapTempo={handleTapTempo}
          onSync={handleSync}
          onFadeOut={handleFadeOut}
          fadeActive={status?.fade_active ?? false}
          queueMode={status?.queue_mode ?? 0}
          onQueueModeChange={handleQueueModeChange}
        />
      }
    />
  )
}

export default App
