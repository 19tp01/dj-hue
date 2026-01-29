import { memo, useCallback, useRef } from 'react'
import { useFaderGestures } from '../../hooks/useFaderGestures'

interface VerticalFaderProps {
  label: string
  value: number
  onChange: (value: number) => void
  onChangeEnd?: () => void
  isMaster?: boolean
}

export const VerticalFader = memo(function VerticalFader({
  label,
  value,
  onChange,
  onChangeEnd,
  isMaster = false,
}: VerticalFaderProps) {
  const { trackRef, trackProps } = useFaderGestures({
    onChange,
    onChangeEnd,
  })

  // Track saved value for on/off toggle
  const savedValueRef = useRef<number>(1)

  const handleToggle = useCallback(() => {
    if (value > 0) {
      // Currently on - save value and turn off
      savedValueRef.current = value
      onChange(0)
    } else {
      // Currently off - restore saved value (or max if saved was 0)
      const restoreValue = savedValueRef.current > 0 ? savedValueRef.current : 1
      onChange(restoreValue)
    }
    onChangeEnd?.()
  }, [value, onChange, onChangeEnd])

  const percentage = Math.round(value * 100)
  const isOff = value === 0

  return (
    <div className="flex flex-col items-center gap-2 h-full">
      {/* Value display */}
      <div
        className="text-xs font-medium tabular-nums h-4"
        style={{
          fontFamily: 'var(--font-mono)',
          color: isOff ? 'var(--text-dim)' : 'var(--text-secondary)',
        }}
      >
        {percentage}%
      </div>

      {/* Fader track */}
      <div
        ref={trackRef}
        {...trackProps}
        className="relative flex-1 w-10 rounded-lg cursor-pointer touch-none"
        style={{
          background: 'var(--bg-interactive)',
          boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.3)',
        }}
      >
        {/* Fill */}
        <div
          className="absolute bottom-0 left-0 right-0 rounded-lg fader-fill"
          style={{
            height: `${percentage}%`,
            background: isMaster
              ? 'linear-gradient(to top, var(--accent-dim), var(--accent-bright))'
              : 'linear-gradient(to top, var(--accent-dim), var(--accent-mid))',
            boxShadow: value > 0.1 ? 'var(--glow-cyan)' : 'none',
          }}
        />

        {/* Thumb */}
        <div
          className="absolute left-1/2 -translate-x-1/2 w-8 h-3 rounded-full transition-all duration-50"
          style={{
            bottom: `calc(${percentage}% - 6px)`,
            background: 'white',
            boxShadow: 'var(--shadow-button)',
          }}
        />

        {/* Glass overlay effect */}
        <div
          className="absolute inset-0 rounded-lg pointer-events-none"
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, transparent 50%)',
          }}
        />
      </div>

      {/* Label */}
      <div
        className="text-sm uppercase tracking-wider font-semibold"
        style={{
          color: isMaster ? 'var(--accent-bright)' : 'var(--text-secondary)',
        }}
      >
        {label}
      </div>

      {/* On/Off toggle button */}
      <button
        onClick={handleToggle}
        className="w-full py-2 rounded text-xs font-bold uppercase tracking-wide transition-all duration-75 active:scale-95"
        style={{
          background: isOff ? 'var(--status-error-bg)' : 'var(--bg-interactive)',
          color: isOff ? 'var(--status-error)' : 'var(--text-muted)',
          border: isOff ? '1px solid var(--status-error)' : '1px solid transparent',
        }}
      >
        {isOff ? 'OFF' : 'ON'}
      </button>
    </div>
  )
})
