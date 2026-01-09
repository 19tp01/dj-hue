interface PatternGridProps {
  patterns: string[]
  currentIndex: number
  onSelect: (index: number) => void
}

export function PatternGrid({ patterns, currentIndex, onSelect }: PatternGridProps) {
  return (
    <section>
      <h2 className="text-zinc-500 text-sm font-medium mb-2 px-1">PATTERNS</h2>
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
        {patterns.map((name, index) => (
          <button
            key={index}
            onClick={() => onSelect(index)}
            className={`
              min-h-[60px] px-3 py-2 rounded-lg font-medium text-sm
              transition-all duration-75 active:scale-95
              ${
                index === currentIndex
                  ? 'bg-cyan-500 text-black shadow-lg shadow-cyan-500/30'
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
