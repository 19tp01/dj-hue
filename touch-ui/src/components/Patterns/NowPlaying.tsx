import { memo } from 'react'
import type { BankName } from '../../types'

interface NowPlayingProps {
  patternName: string
  patternBank: BankName | null
  currentBank: BankName
  onGoToBank: (bank: BankName) => void
}

export const NowPlaying = memo(function NowPlaying({
  patternName,
  patternBank,
  currentBank,
  onGoToBank,
}: NowPlayingProps) {
  // Only show when viewing a different bank than where active pattern lives
  if (!patternBank || patternBank === currentBank) {
    return null
  }

  return (
    <button
      onClick={() => onGoToBank(patternBank)}
      className="
        absolute bottom-3 left-3 right-3
        flex items-center justify-between gap-2
        px-3 py-2 rounded-lg
        transition-all duration-150 active:scale-[0.98]
      "
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--accent-dim)',
        boxShadow: 'var(--shadow-elevated)',
      }}
    >
      <div className="flex items-center gap-2">
        <div
          className="w-2 h-2 rounded-full animate-pulse"
          style={{
            background: 'var(--accent-bright)',
            boxShadow: 'var(--glow-cyan)',
          }}
        />
        <span className="text-xs uppercase tracking-wider"
          style={{ color: 'var(--text-muted)' }}>
          Now Playing
        </span>
      </div>
      <span className="text-sm font-medium truncate max-w-[160px]"
        style={{ color: 'var(--accent-glow)' }}>
        {patternName}
      </span>
      <span className="text-xs px-2 py-0.5 rounded"
        style={{
          background: 'var(--accent-dim)',
          color: 'var(--accent-bright)',
        }}>
        {patternBank}
      </span>
    </button>
  )
})
