import { memo } from 'react'

interface PaletteChipProps {
  name: string
  colors?: string[]
  isSelected: boolean
  isDefault?: boolean
  onClick: () => void
}

// Default gradient when no colors are provided
const DEFAULT_GRADIENT = ['var(--accent-dim)', 'var(--accent-mid)', 'var(--accent-bright)']

// Convert snake_case to Title Case (e.g., "flash_cyan" → "Flash Cyan")
function formatPaletteName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

export const PaletteChip = memo(function PaletteChip({
  name,
  colors,
  isSelected,
  isDefault = false,
  onClick,
}: PaletteChipProps) {
  const displayColors = colors && colors.length > 0 ? colors : DEFAULT_GRADIENT
  const gradient = `linear-gradient(90deg, ${displayColors.join(', ')})`
  const displayName = isDefault ? name : formatPaletteName(name)

  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 flex flex-col rounded-md overflow-hidden transition-all duration-75 active:scale-95"
      style={{
        width: '76px',
        height: '62px',
        background: 'var(--bg-interactive)',
        border: isSelected ? '2px solid var(--purple-bright)' : '2px solid transparent',
        boxShadow: isSelected ? 'var(--glow-purple)' : 'none',
      }}
    >
      {/* Color swatch */}
      <div
        className="flex-1 w-full"
        style={{
          background: isDefault
            ? 'linear-gradient(135deg, var(--bg-elevated) 25%, var(--bg-interactive) 75%)'
            : gradient,
        }}
      >
        {isDefault && (
          <div className="h-full flex items-center justify-center">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              ◎
            </span>
          </div>
        )}
      </div>

      {/* Name */}
      <div
        className="px-1 py-0.5 text-center truncate font-medium"
        style={{
          fontSize: '10px',
          color: isSelected ? 'var(--purple-glow)' : 'var(--text-secondary)',
          background: 'var(--bg-surface)',
        }}
      >
        {displayName}
      </div>
    </button>
  )
})
