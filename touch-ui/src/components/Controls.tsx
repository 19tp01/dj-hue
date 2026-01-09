import { useState, useCallback, useRef } from 'react'

interface ControlsProps {
  blackout: boolean
  onTapTempo: () => void
  onSync: () => void
  onStart: () => void
  onStop: () => void
  onBlackout: () => void
  onFlash: () => void
}

export function Controls({
  blackout,
  onTapTempo,
  onSync,
  onStart,
  onStop,
  onBlackout,
  onFlash,
}: ControlsProps) {
  const [isPlaying, setIsPlaying] = useState(true)
  const [flashActive, setFlashActive] = useState(false)
  const flashTimeoutRef = useRef<number | null>(null)

  const handleStartStop = useCallback(() => {
    if (isPlaying) {
      onStop()
    } else {
      onStart()
    }
    setIsPlaying(!isPlaying)
  }, [isPlaying, onStart, onStop])

  const handleFlash = useCallback(() => {
    onFlash()
    setFlashActive(true)
    if (flashTimeoutRef.current) {
      clearTimeout(flashTimeoutRef.current)
    }
    flashTimeoutRef.current = window.setTimeout(() => {
      setFlashActive(false)
    }, 200)
  }, [onFlash])

  return (
    <footer className="bg-zinc-900 border-t border-zinc-800 px-4 py-3">
      <div className="grid grid-cols-5 gap-2">
        {/* TAP */}
        <button
          onClick={onTapTempo}
          className="min-h-[70px] bg-zinc-800 hover:bg-zinc-700 active:bg-zinc-600
                     text-white font-bold rounded-lg transition-all duration-75 active:scale-95"
        >
          TAP
        </button>

        {/* SYNC */}
        <button
          onClick={onSync}
          className="min-h-[70px] bg-blue-600 hover:bg-blue-500 active:bg-blue-400
                     text-white font-bold rounded-lg transition-all duration-75 active:scale-95"
        >
          SYNC
        </button>

        {/* START/STOP */}
        <button
          onClick={handleStartStop}
          className={`
            min-h-[70px] font-bold rounded-lg transition-all duration-75 active:scale-95
            ${
              isPlaying
                ? 'bg-red-600 hover:bg-red-500 active:bg-red-400 text-white'
                : 'bg-green-600 hover:bg-green-500 active:bg-green-400 text-white'
            }
          `}
        >
          {isPlaying ? 'STOP' : 'START'}
        </button>

        {/* BLACKOUT */}
        <button
          onClick={onBlackout}
          className={`
            min-h-[70px] font-bold rounded-lg transition-all duration-75 active:scale-95
            ${
              blackout
                ? 'bg-zinc-900 text-zinc-500 border-2 border-zinc-600'
                : 'bg-zinc-800 hover:bg-zinc-700 active:bg-zinc-600 text-white'
            }
          `}
        >
          {blackout ? 'LIGHTS' : 'BLACK'}
        </button>

        {/* FLASH */}
        <button
          onClick={handleFlash}
          className={`
            min-h-[70px] font-bold rounded-lg transition-all duration-75 active:scale-95
            ${
              flashActive
                ? 'bg-yellow-400 text-black'
                : 'bg-yellow-600 hover:bg-yellow-500 active:bg-yellow-400 text-black'
            }
          `}
        >
          FLASH
        </button>
      </div>
    </footer>
  )
}
