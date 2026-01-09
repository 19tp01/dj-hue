interface PaletteGridProps {
  palettes: string[]
  currentPalette: string | null
  hasOverride: boolean
  onSelect: (name: string | null) => void
}

export function PaletteGrid({ palettes, currentPalette, hasOverride, onSelect }: PaletteGridProps) {
  return (
    <section>
      <h2 className="text-zinc-500 text-sm font-medium mb-2 px-1">PALETTES</h2>
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
        {/* Default option */}
        <button
          onClick={() => onSelect(null)}
          className={`
            min-h-[60px] px-3 py-2 rounded-lg font-medium text-sm
            transition-all duration-75 active:scale-95
            ${
              !hasOverride
                ? 'bg-purple-500 text-black shadow-lg shadow-purple-500/30'
                : 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700'
            }
          `}
        >
          Default
        </button>

        {/* Palette options */}
        {palettes.map((name) => (
          <button
            key={name}
            onClick={() => onSelect(name)}
            className={`
              min-h-[60px] px-3 py-2 rounded-lg font-medium text-sm
              transition-all duration-75 active:scale-95
              ${
                hasOverride && currentPalette === name
                  ? 'bg-purple-500 text-black shadow-lg shadow-purple-500/30'
                  : 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700'
              }
            `}
          >
            <span className="line-clamp-2">{name}</span>
          </button>
        ))}
      </div>
    </section>
  )
}
