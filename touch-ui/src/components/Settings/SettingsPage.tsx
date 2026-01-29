import { useState, useEffect, useCallback, useMemo } from 'react'
import type { DJHueCommand, LightConfig, LightConfigSaved, LightInfo } from '../../hooks/useWebSocket'
import { LightList } from './LightList'
import { GroupEditor } from './GroupEditor'

interface SettingsPageProps {
  lightConfig: LightConfig | null
  lightConfigSaved: LightConfigSaved | null
  onBack: () => void
  send: (command: DJHueCommand) => void
  clearLightConfigSaved: () => void
}

function BackIcon() {
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
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  )
}

// Split lights into zones based on group membership and zones config
function splitByZone(
  lights: LightInfo[],
  zones: Record<string, string[]>
): { strip: LightInfo[]; lamps: LightInfo[]; ambient: LightInfo[] } {
  const strip: LightInfo[] = []
  const lamps: LightInfo[] = []
  const ambient: LightInfo[] = []

  const ambientNames = new Set(zones.ambient || [])

  for (const light of lights) {
    if (light.groups.includes('strip')) {
      strip.push(light)
    } else if (ambientNames.has(light.name)) {
      ambient.push(light)
    } else {
      // Default to lamps (perimeter) if no zone detected
      lamps.push(light)
    }
  }

  return { strip, lamps, ambient }
}

// Merge zone lists back into a single light order (strip first, then lamps, then ambient)
function mergeZones(strip: LightInfo[], lamps: LightInfo[], ambient: LightInfo[]): LightInfo[] {
  return [...strip, ...lamps, ...ambient].map((light, idx) => ({ ...light, index: idx }))
}

export function SettingsPage({
  lightConfig,
  lightConfigSaved,
  onBack,
  send,
  clearLightConfigSaved,
}: SettingsPageProps) {
  // Local state for editing - separated by zone
  const [stripLights, setStripLights] = useState<LightInfo[]>([])
  const [lampLights, setLampLights] = useState<LightInfo[]>([])
  const [ambientLights, setAmbientLights] = useState<LightInfo[]>([])
  const [customGroups, setCustomGroups] = useState<Record<string, string[]>>({})
  const [hasChanges, setHasChanges] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selectedLamp, setSelectedLamp] = useState<string | null>(null)
  const [selectedAmbient, setSelectedAmbient] = useState<string | null>(null)

  // Combined lights for group editor
  const allLights = useMemo(() => mergeZones(stripLights, lampLights, ambientLights), [stripLights, lampLights, ambientLights])

  // Fetch light config on mount
  useEffect(() => {
    send({ type: 'get_light_config' })
  }, [send])

  // Initialize local state from server config
  useEffect(() => {
    if (lightConfig) {
      const { strip, lamps, ambient } = splitByZone(lightConfig.lights, lightConfig.zones || {})
      setStripLights(strip)
      setLampLights(lamps)
      setAmbientLights(ambient)
      setCustomGroups(lightConfig.custom_groups)
      setHasChanges(false)
      setSelectedLamp(null)
      setSelectedAmbient(null)
    }
  }, [lightConfig])

  // Handle save result
  useEffect(() => {
    if (lightConfigSaved) {
      setSaving(false)
      if (lightConfigSaved.success) {
        setHasChanges(false)
      }
    }
  }, [lightConfigSaved])

  const handleStripReorder = useCallback((fromIndex: number, toIndex: number) => {
    setStripLights(prev => {
      const newLights = [...prev]
      const [moved] = newLights.splice(fromIndex, 1)
      newLights.splice(toIndex, 0, moved)
      return newLights
    })
    setHasChanges(true)
    clearLightConfigSaved()
  }, [clearLightConfigSaved])

  const handleLampReorder = useCallback((fromIndex: number, toIndex: number) => {
    setLampLights(prev => {
      const newLights = [...prev]
      const [moved] = newLights.splice(fromIndex, 1)
      newLights.splice(toIndex, 0, moved)
      return newLights
    })
    setHasChanges(true)
    clearLightConfigSaved()
  }, [clearLightConfigSaved])

  const handleAmbientReorder = useCallback((fromIndex: number, toIndex: number) => {
    setAmbientLights(prev => {
      const newLights = [...prev]
      const [moved] = newLights.splice(fromIndex, 1)
      newLights.splice(toIndex, 0, moved)
      return newLights
    })
    setHasChanges(true)
    clearLightConfigSaved()
  }, [clearLightConfigSaved])

  const handleMoveToAmbient = useCallback(() => {
    if (!selectedLamp) return
    const light = lampLights.find(l => l.name === selectedLamp)
    if (!light) return
    setLampLights(prev => prev.filter(l => l.name !== selectedLamp))
    setAmbientLights(prev => [...prev, light])
    setSelectedLamp(null)
    setHasChanges(true)
    clearLightConfigSaved()
  }, [selectedLamp, lampLights, clearLightConfigSaved])

  const handleMoveToPerimeter = useCallback(() => {
    if (!selectedAmbient) return
    const light = ambientLights.find(l => l.name === selectedAmbient)
    if (!light) return
    setAmbientLights(prev => prev.filter(l => l.name !== selectedAmbient))
    setLampLights(prev => [...prev, light])
    setSelectedAmbient(null)
    setHasChanges(true)
    clearLightConfigSaved()
  }, [selectedAmbient, ambientLights, clearLightConfigSaved])

  const handleGroupsChange = useCallback((groups: Record<string, string[]>) => {
    setCustomGroups(groups)
    setHasChanges(true)
    clearLightConfigSaved()
  }, [clearLightConfigSaved])

  const handleSave = useCallback(() => {
    setSaving(true)
    clearLightConfigSaved()
    // Build light_order from current order (strip first, then lamps, then ambient)
    const lightOrder = [...stripLights, ...lampLights, ...ambientLights].map(l => l.name)
    // Build zones config
    const zones: Record<string, string[]> = {}
    if (ambientLights.length > 0) {
      zones.ambient = ambientLights.map(l => l.name)
    }
    send({
      type: 'save_light_config',
      light_order: lightOrder,
      custom_groups: customGroups,
      zones,
    })
  }, [stripLights, lampLights, ambientLights, customGroups, send, clearLightConfigSaved])

  const handleIdentify = useCallback((globalIndex: number) => {
    send({ type: 'identify_light', index: globalIndex })
  }, [send])

  const loading = !lightConfig

  return (
    <div className="h-dvh bg-zinc-950 text-white flex flex-col overflow-hidden">
      {/* Header */}
      <header className="shrink-0 bg-zinc-900 border-b border-zinc-800 px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors active:scale-95"
            aria-label="Back"
          >
            <BackIcon />
          </button>
          <h1 className="text-xl font-semibold">Light Settings</h1>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 min-h-0 overflow-y-auto p-4 space-y-6">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="text-zinc-500">Loading...</div>
          </div>
        ) : (
          <>
            {/* Strip Zone */}
            {stripLights.length > 0 && (
              <section>
                <h2 className="text-lg font-medium text-zinc-300 mb-2">Strip Zone</h2>
                <p className="text-sm text-zinc-500 mb-4">
                  Tap a light to flash it. Reorder with arrows.
                </p>
                <LightList
                  lights={stripLights}
                  onReorder={handleStripReorder}
                  onIdentify={handleIdentify}
                  showZoneIndex
                />
              </section>
            )}

            {/* Perimeter Zone (Lamps) */}
            {lampLights.length > 0 && (
              <section>
                <h2 className="text-lg font-medium text-zinc-300 mb-2">Perimeter Zone</h2>
                <p className="text-sm text-zinc-500 mb-4">
                  Tap to select, then move to Ambient. Reorder with arrows.
                </p>
                <LightList
                  lights={lampLights}
                  onReorder={handleLampReorder}
                  onIdentify={handleIdentify}
                  showZoneIndex
                  selectedName={selectedLamp}
                  onSelect={setSelectedLamp}
                />
                {selectedLamp && (
                  <button
                    onClick={handleMoveToAmbient}
                    className="mt-3 w-full py-3 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-medium transition-colors active:scale-[0.98]"
                  >
                    Move "{selectedLamp}" to Ambient
                  </button>
                )}
              </section>
            )}

            {/* Ambient Zone */}
            <section>
              <h2 className="text-lg font-medium text-zinc-300 mb-2">Ambient Zone</h2>
              <p className="text-sm text-zinc-500 mb-4">
                Lights for other rooms. Controlled by ambient fader.
              </p>
              {ambientLights.length > 0 ? (
                <>
                  <LightList
                    lights={ambientLights}
                    onReorder={handleAmbientReorder}
                    onIdentify={handleIdentify}
                    showZoneIndex
                    selectedName={selectedAmbient}
                    onSelect={setSelectedAmbient}
                  />
                  {selectedAmbient && (
                    <button
                      onClick={handleMoveToPerimeter}
                      className="mt-3 w-full py-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-medium transition-colors active:scale-[0.98]"
                    >
                      Move "{selectedAmbient}" to Perimeter
                    </button>
                  )}
                </>
              ) : (
                <div className="bg-zinc-900 rounded-lg p-6 text-center text-zinc-500">
                  No ambient lights. Select a lamp above to move it here.
                </div>
              )}
            </section>

            {/* Custom Groups Section */}
            <section>
              <h2 className="text-lg font-medium text-zinc-300 mb-2">Custom Groups</h2>
              <p className="text-sm text-zinc-500 mb-4">
                Create named groups to use in patterns (e.g., light("ceiling")).
              </p>
              <GroupEditor
                customGroups={customGroups}
                lights={allLights}
                onChange={handleGroupsChange}
              />
            </section>
          </>
        )}
      </main>

      {/* Footer with Save */}
      <footer className="shrink-0 bg-zinc-900 border-t border-zinc-800 p-4 space-y-3">
        {/* Save result message */}
        {lightConfigSaved && (
          <div
            className={`text-center py-2 px-4 rounded text-sm ${
              lightConfigSaved.success
                ? 'bg-green-900/50 text-green-200'
                : 'bg-red-900/50 text-red-200'
            }`}
          >
            {lightConfigSaved.message}
          </div>
        )}

        {/* Save button */}
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          className={`w-full py-4 rounded-lg font-medium text-lg transition-colors ${
            hasChanges && !saving
              ? 'bg-cyan-600 hover:bg-cyan-500 text-white active:scale-[0.98]'
              : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
          }`}
        >
          {saving ? 'Saving...' : hasChanges ? 'Save Changes' : 'No Changes'}
        </button>
      </footer>
    </div>
  )
}
