import type { LightInfo } from '../../hooks/useWebSocket'

interface LightItemProps {
  light: LightInfo
  index: number
  isFirst: boolean
  isLast: boolean
  onMoveUp: () => void
  onMoveDown: () => void
  onIdentify?: () => void  // Flash the physical light to identify it
}

function ChevronUpIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-5 h-5"
    >
      <path d="M18 15l-6-6-6 6" />
    </svg>
  )
}

function ChevronDownIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-5 h-5"
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  )
}

// Groups to show as badges (exclude derived/computed groups)
const DISPLAY_GROUPS = ['strip', 'lamps', 'left', 'right']

function FlashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  )
}

export function LightItem({
  light,
  index,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
  onIdentify,
}: LightItemProps) {
  // Filter to interesting groups
  const displayGroups = light.groups.filter(g => DISPLAY_GROUPS.includes(g))

  return (
    <div className="bg-zinc-900 rounded-lg p-3 flex items-center gap-3">
      {/* Index badge - tappable to identify */}
      <button
        onClick={onIdentify}
        className="w-10 h-10 flex items-center justify-center bg-zinc-800 hover:bg-cyan-600 rounded-lg text-lg font-bold text-cyan-400 hover:text-white shrink-0 transition-colors active:scale-95"
        title="Tap to flash this light"
      >
        {index}
      </button>

      {/* Light info - also tappable to identify */}
      <button
        onClick={onIdentify}
        className="flex-1 min-w-0 text-left hover:bg-zinc-800/50 -my-2 -ml-2 py-2 pl-2 rounded transition-colors"
      >
        <div className="text-white font-medium truncate">{light.name}</div>
        <div className="flex gap-1.5 mt-1 flex-wrap">
          {displayGroups.length > 0 ? (
            displayGroups.map(group => (
              <span
                key={group}
                className="px-2 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded"
              >
                {group}
              </span>
            ))
          ) : (
            <span className="text-zinc-600 text-xs flex items-center gap-1">
              <FlashIcon /> tap to identify
            </span>
          )}
        </div>
      </button>

      {/* Move buttons */}
      <div className="flex flex-col gap-1 shrink-0">
        <button
          onClick={onMoveUp}
          disabled={isFirst}
          className={`p-2 rounded transition-colors ${
            isFirst
              ? 'text-zinc-700 cursor-not-allowed'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800 active:scale-95'
          }`}
          aria-label="Move up"
        >
          <ChevronUpIcon />
        </button>
        <button
          onClick={onMoveDown}
          disabled={isLast}
          className={`p-2 rounded transition-colors ${
            isLast
              ? 'text-zinc-700 cursor-not-allowed'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800 active:scale-95'
          }`}
          aria-label="Move down"
        >
          <ChevronDownIcon />
        </button>
      </div>
    </div>
  )
}
