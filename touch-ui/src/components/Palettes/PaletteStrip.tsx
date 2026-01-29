import { memo, useCallback } from 'react'
import type { PaletteInfo } from '../../types'
import { PaletteChip } from './PaletteChip'

interface PaletteStripProps {
  palettes: PaletteInfo[]
  currentPalette: string | null
  hasOverride: boolean
  onSelect: (name: string | null) => void
}

export const PaletteStrip = memo(function PaletteStrip({
  palettes,
  currentPalette,
  hasOverride,
  onSelect,
}: PaletteStripProps) {
  const handleDefaultSelect = useCallback(() => {
    onSelect(null)
  }, [onSelect])

  const handlePaletteSelect = useCallback((name: string) => {
    onSelect(name)
  }, [onSelect])

  // Calculate number of columns needed for 3 rows
  const numRows = 3
  const numCols = Math.ceil((palettes.length + 1) / numRows) // +1 for Default

  return (
    <div className="h-full relative">
      {/* Scrollable grid container */}
      <div className="h-full overflow-x-auto overflow-y-hidden scrollbar-hide">
        <div
          className="h-full grid gap-2 p-3 content-start"
          style={{
            gridTemplateRows: `repeat(${numRows}, 62px)`,
            gridTemplateColumns: `repeat(${numCols}, 76px)`,
            gridAutoFlow: 'column',
          }}
        >
          {/* Default option */}
          <PaletteChip
            name="Default"
            isSelected={!hasOverride}
            isDefault
            onClick={handleDefaultSelect}
          />

          {/* Palette options */}
          {palettes.map((palette) => (
            <PaletteChip
              key={palette.name}
              name={palette.name}
              colors={palette.colors}
              isSelected={hasOverride && currentPalette === palette.name}
              onClick={() => handlePaletteSelect(palette.name)}
            />
          ))}
        </div>
      </div>

      {/* Fade edges to indicate scroll */}
      <div
        className="absolute left-0 top-0 bottom-0 w-4 pointer-events-none"
        style={{
          background: 'linear-gradient(90deg, var(--bg-surface), transparent)',
        }}
      />
      <div
        className="absolute right-0 top-0 bottom-0 w-4 pointer-events-none"
        style={{
          background: 'linear-gradient(-90deg, var(--bg-surface), transparent)',
        }}
      />
    </div>
  )
})
