import type { LightInfo } from '../../hooks/useWebSocket'
import { LightItem } from './LightItem'

interface LightListProps {
  lights: LightInfo[]
  onReorder: (fromIndex: number, toIndex: number) => void
  onIdentify?: (globalIndex: number) => void  // Flash light by its global index
  showZoneIndex?: boolean  // Show index relative to this list (0, 1, 2...) instead of light.index
  selectedName?: string | null  // Currently selected light name
  onSelect?: (name: string | null) => void  // Selection handler
}

export function LightList({ lights, onReorder, onIdentify, showZoneIndex = false, selectedName, onSelect }: LightListProps) {
  if (lights.length === 0) {
    return (
      <div className="bg-zinc-900 rounded-lg p-6 text-center text-zinc-500">
        No lights found
      </div>
    )
  }

  const handleItemClick = (name: string) => {
    if (!onSelect) return
    // Toggle selection
    onSelect(selectedName === name ? null : name)
  }

  return (
    <div className="space-y-2">
      {lights.map((light, index) => (
        <div
          key={light.rid}
          onClick={onSelect ? () => handleItemClick(light.name) : undefined}
          className={`rounded-lg transition-all ${
            onSelect ? 'cursor-pointer' : ''
          } ${
            selectedName === light.name
              ? 'ring-2 ring-cyan-500 ring-offset-2 ring-offset-zinc-950'
              : ''
          }`}
        >
          <LightItem
            light={light}
            index={showZoneIndex ? index : light.index}
            isFirst={index === 0}
            isLast={index === lights.length - 1}
            onMoveUp={() => onReorder(index, index - 1)}
            onMoveDown={() => onReorder(index, index + 1)}
            onIdentify={onIdentify ? () => onIdentify(light.index) : undefined}
          />
        </div>
      ))}
    </div>
  )
}
