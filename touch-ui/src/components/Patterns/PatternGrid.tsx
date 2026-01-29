import { memo, useCallback } from 'react'
import type { PatternSlot } from '../../types'
import { PatternButton } from './PatternButton'

interface PatternGridProps {
  patterns: PatternSlot[]
  activePatternIndex: number
  queuedPatternIndex: number | null
  onPatternSelect: (index: number) => void
}

export const PatternGrid = memo(function PatternGrid({
  patterns,
  activePatternIndex,
  queuedPatternIndex,
  onPatternSelect,
}: PatternGridProps) {
  const handleSelect = useCallback((patternIndex: number) => {
    onPatternSelect(patternIndex)
  }, [onPatternSelect])

  return (
    <div className="w-full h-full overflow-y-auto">
      <div className="grid grid-cols-4 gap-3 content-start">
        {patterns.map((slot) => (
          <PatternButton
            key={slot.patternIndex}
            name={slot.patternName}
            isActive={slot.patternIndex === activePatternIndex}
            isQueued={slot.patternIndex === queuedPatternIndex}
            onClick={() => handleSelect(slot.patternIndex)}
          />
        ))}
      </div>
    </div>
  )
})
