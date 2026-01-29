import { memo, useCallback, useRef, useState, useEffect } from 'react'
import type { ZoneBrightness } from '../../types'
import { VerticalFader } from './VerticalFader'

interface ZoneFadersProps {
  zoneBrightness: ZoneBrightness
  onZoneBrightnessChange: (zone: 'ceiling' | 'perimeter' | 'ambient', value: number) => void
}

export const ZoneFaders = memo(function ZoneFaders({
  zoneBrightness,
  onZoneBrightnessChange,
}: ZoneFadersProps) {
  // Track the "reference" values for proportional master control
  const referenceValues = useRef({
    ceiling: zoneBrightness.ceiling,
    perimeter: zoneBrightness.perimeter,
    ambient: zoneBrightness.ambient,
    master: Math.max(zoneBrightness.ceiling, zoneBrightness.perimeter, zoneBrightness.ambient),
  })

  // Track whether master is being dragged (to avoid useEffect overwriting references)
  const isDraggingMaster = useRef(false)

  // Local master value for smooth UI
  const [masterValue, setMasterValue] = useState(
    Math.max(zoneBrightness.ceiling, zoneBrightness.perimeter, zoneBrightness.ambient)
  )

  // Sync reference values when zone brightness changes from external source
  // Skip if we're dragging master (we'll update references when drag ends)
  useEffect(() => {
    if (isDraggingMaster.current) return

    const maxValue = Math.max(zoneBrightness.ceiling, zoneBrightness.perimeter, zoneBrightness.ambient)
    referenceValues.current = {
      ceiling: zoneBrightness.ceiling,
      perimeter: zoneBrightness.perimeter,
      ambient: zoneBrightness.ambient,
      master: maxValue || 1, // Avoid division by zero
    }
    setMasterValue(maxValue)
  }, [zoneBrightness.ceiling, zoneBrightness.perimeter, zoneBrightness.ambient])

  // Handle individual zone change
  const handleCeilingChange = useCallback((value: number) => {
    onZoneBrightnessChange('ceiling', value)
  }, [onZoneBrightnessChange])

  const handlePerimeterChange = useCallback((value: number) => {
    onZoneBrightnessChange('perimeter', value)
  }, [onZoneBrightnessChange])

  const handleAmbientChange = useCallback((value: number) => {
    onZoneBrightnessChange('ambient', value)
  }, [onZoneBrightnessChange])

  // Handle master change - proportionally scale all zones
  const handleMasterChange = useCallback((newMaster: number) => {
    // Mark that we're dragging master (prevents useEffect from overwriting references)
    isDraggingMaster.current = true

    setMasterValue(newMaster)

    const ref = referenceValues.current
    const oldMaster = ref.master

    if (oldMaster === 0 || newMaster === 0) {
      // Special case: going to/from zero
      if (newMaster === 0) {
        onZoneBrightnessChange('ceiling', 0)
        onZoneBrightnessChange('perimeter', 0)
        onZoneBrightnessChange('ambient', 0)
      }
      return
    }

    const ratio = newMaster / oldMaster

    // Calculate new values proportionally
    // If a zone ref is 0, use master as fallback so it scales with master
    const refCeiling = ref.ceiling || oldMaster
    const refPerimeter = ref.perimeter || oldMaster
    const refAmbient = ref.ambient || oldMaster
    const newCeiling = Math.min(1, Math.max(0, refCeiling * ratio))
    const newPerimeter = Math.min(1, Math.max(0, refPerimeter * ratio))
    const newAmbient = Math.min(1, Math.max(0, refAmbient * ratio))

    onZoneBrightnessChange('ceiling', newCeiling)
    onZoneBrightnessChange('perimeter', newPerimeter)
    onZoneBrightnessChange('ambient', newAmbient)
  }, [onZoneBrightnessChange])

  // When master drag ends, update reference values
  const handleMasterChangeEnd = useCallback(() => {
    isDraggingMaster.current = false
    referenceValues.current = {
      ceiling: zoneBrightness.ceiling,
      perimeter: zoneBrightness.perimeter,
      ambient: zoneBrightness.ambient,
      master: masterValue || 1,
    }
  }, [zoneBrightness.ceiling, zoneBrightness.perimeter, zoneBrightness.ambient, masterValue])

  // When individual fader drag ends, update master reference
  const handleZoneChangeEnd = useCallback(() => {
    const maxValue = Math.max(zoneBrightness.ceiling, zoneBrightness.perimeter, zoneBrightness.ambient)
    referenceValues.current = {
      ceiling: zoneBrightness.ceiling,
      perimeter: zoneBrightness.perimeter,
      ambient: zoneBrightness.ambient,
      master: maxValue || 1,
    }
    setMasterValue(maxValue)
  }, [zoneBrightness.ceiling, zoneBrightness.perimeter, zoneBrightness.ambient])

  return (
    <div className="h-full flex gap-2">
      <VerticalFader
        label="C"
        value={zoneBrightness.ceiling}
        onChange={handleCeilingChange}
        onChangeEnd={handleZoneChangeEnd}
      />
      <VerticalFader
        label="P"
        value={zoneBrightness.perimeter}
        onChange={handlePerimeterChange}
        onChangeEnd={handleZoneChangeEnd}
      />
      <VerticalFader
        label="A"
        value={zoneBrightness.ambient}
        onChange={handleAmbientChange}
        onChangeEnd={handleZoneChangeEnd}
      />
      <VerticalFader
        label="M"
        value={masterValue}
        onChange={handleMasterChange}
        onChangeEnd={handleMasterChangeEnd}
        isMaster
      />
    </div>
  )
})
