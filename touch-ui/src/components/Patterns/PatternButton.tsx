import { memo } from 'react'

interface PatternButtonProps {
  name: string
  isActive: boolean
  isQueued?: boolean
  onClick: () => void
  isEmpty?: boolean
}

export const PatternButton = memo(function PatternButton({
  name,
  isActive,
  isQueued = false,
  onClick,
  isEmpty = false,
}: PatternButtonProps) {
  if (isEmpty) {
    return (
      <div
        className="rounded-lg border-2 border-dashed"
        style={{
          borderColor: 'var(--bg-interactive)',
          height: '52px',
        }}
      />
    )
  }

  return (
    <button
      onClick={onClick}
      className={`
        w-full rounded-lg font-medium text-sm
        transition-all duration-75 active:scale-95
        flex items-center justify-center text-center
        px-3 py-2
        ${isActive ? 'animate-glow-pulse' : ''}
        ${isQueued ? 'animate-queue-pulse' : ''}
      `}
      style={{
        height: '52px',
        background: isActive ? 'var(--accent-bright)' : isQueued ? '#78350f' : 'var(--bg-interactive)',
        color: isActive ? 'var(--bg-void)' : isQueued ? '#fbbf24' : 'var(--text-primary)',
        boxShadow: isActive ? 'var(--glow-cyan)' : isQueued ? '0 0 12px rgba(245, 158, 11, 0.3)' : 'var(--shadow-button)',
        border: isQueued ? '2px solid #f59e0b' : '2px solid transparent',
      }}
    >
      <span className="line-clamp-1 leading-tight">{name}</span>
    </button>
  )
})
