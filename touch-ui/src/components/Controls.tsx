import { useState, useCallback, useRef } from 'react'
import type { ZoneBrightness } from '../hooks/useWebSocket'

interface ControlsProps {
  zoneBrightness: ZoneBrightness
  onTapTempo: () => void
  onSync: () => void
  onStart: () => void
  onStop: () => void
  onFlash: () => void
  onZoneBrightnessChange: (zone: 'ceiling' | 'perimeter', value: number) => void
}

interface ZoneSliderProps {
  label: string
  zone: 'ceiling' | 'perimeter'
  value: number
  onChange: (zone: 'ceiling' | 'perimeter', value: number) => void
}

function ZoneSlider({ label, zone, value, onChange }: ZoneSliderProps) {
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(zone, parseFloat(e.target.value))
  }, [zone, onChange])

  const handleOff = useCallback(() => {
    onChange(zone, 0)
  }, [zone, onChange])

  const isOff = value === 0

  return (
    <div className="flex items-center gap-2">
      <span className="text-zinc-400 text-xs w-16 uppercase tracking-wide">{label}</span>
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        value={value}
        onChange={handleChange}
        className="flex-1 h-8 appearance-none bg-zinc-800 rounded-lg cursor-pointer
                   [&::-webkit-slider-thumb]:appearance-none
                   [&::-webkit-slider-thumb]:w-8
                   [&::-webkit-slider-thumb]:h-8
                   [&::-webkit-slider-thumb]:bg-white
                   [&::-webkit-slider-thumb]:rounded-full
                   [&::-webkit-slider-thumb]:shadow-lg"
      />
      <span className="text-zinc-400 text-sm w-10 text-right">
        {Math.round(value * 100)}%
      </span>
      <button
        onClick={handleOff}
        className={`
          w-14 h-8 text-xs font-bold rounded transition-all duration-75 active:scale-95
          ${isOff
            ? 'bg-red-900 text-red-400 border border-red-700'
            : 'bg-zinc-700 hover:bg-zinc-600 text-zinc-300'
          }
        `}
      >
        OFF
      </button>
    </div>
  )
}

export function Controls({
  zoneBrightness,
  onTapTempo,
  onSync,
  onStart,
  onStop,
  onFlash,
  onZoneBrightnessChange,
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
    <footer className="bg-zinc-900 border-t border-zinc-800 px-4 py-3 space-y-2">
      {/* Zone Brightness Sliders */}
      <ZoneSlider
        label="Ceiling"
        zone="ceiling"
        value={zoneBrightness.ceiling}
        onChange={onZoneBrightnessChange}
      />
      <ZoneSlider
        label="Perimeter"
        zone="perimeter"
        value={zoneBrightness.perimeter}
        onChange={onZoneBrightnessChange}
      />

      {/* Control Buttons */}
      <div className="grid grid-cols-4 gap-2 pt-1">
        {/* TAP */}
        <button
          onClick={onTapTempo}
          className="min-h-[60px] bg-zinc-800 hover:bg-zinc-700 active:bg-zinc-600
                     text-white font-bold rounded-lg transition-all duration-75 active:scale-95"
        >
          TAP
        </button>

        {/* SYNC */}
        <button
          onClick={onSync}
          className="min-h-[60px] bg-blue-600 hover:bg-blue-500 active:bg-blue-400
                     text-white font-bold rounded-lg transition-all duration-75 active:scale-95"
        >
          SYNC
        </button>

        {/* START/STOP */}
        <button
          onClick={handleStartStop}
          className={`
            min-h-[60px] font-bold rounded-lg transition-all duration-75 active:scale-95
            ${
              isPlaying
                ? 'bg-red-600 hover:bg-red-500 active:bg-red-400 text-white'
                : 'bg-green-600 hover:bg-green-500 active:bg-green-400 text-white'
            }
          `}
        >
          {isPlaying ? 'STOP' : 'START'}
        </button>

        {/* FLASH */}
        <button
          onClick={handleFlash}
          className={`
            min-h-[60px] font-bold rounded-lg transition-all duration-75 active:scale-95
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
