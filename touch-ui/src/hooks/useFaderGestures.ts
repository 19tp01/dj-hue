import { useCallback, useRef, useEffect } from 'react'

interface UseFaderGesturesOptions {
  onChange: (value: number) => void
  onChangeEnd?: () => void
  min?: number
  max?: number
}

export function useFaderGestures({
  onChange,
  onChangeEnd,
  min = 0,
  max = 1,
}: UseFaderGesturesOptions) {
  const trackRef = useRef<HTMLDivElement>(null)
  const isDragging = useRef(false)

  const calculateValue = useCallback((clientY: number): number => {
    const track = trackRef.current
    if (!track) return min

    const rect = track.getBoundingClientRect()
    // Invert Y axis: top = max, bottom = min
    const relativeY = rect.bottom - clientY
    const percentage = Math.max(0, Math.min(1, relativeY / rect.height))
    return min + percentage * (max - min)
  }, [min, max])

  const handleStart = useCallback((clientY: number) => {
    isDragging.current = true
    const value = calculateValue(clientY)
    onChange(value)
  }, [calculateValue, onChange])

  const handleMove = useCallback((clientY: number) => {
    if (!isDragging.current) return
    const value = calculateValue(clientY)
    onChange(value)
  }, [calculateValue, onChange])

  const handleEnd = useCallback(() => {
    if (isDragging.current) {
      isDragging.current = false
      onChangeEnd?.()
    }
  }, [onChangeEnd])

  // Touch event handlers
  const onTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault()
    const touch = e.touches[0]
    handleStart(touch.clientY)
  }, [handleStart])

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    e.preventDefault()
    const touch = e.touches[0]
    handleMove(touch.clientY)
  }, [handleMove])

  const onTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault()
    handleEnd()
  }, [handleEnd])

  // Mouse event handlers (for testing)
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    handleStart(e.clientY)
  }, [handleStart])

  // Global mouse move/up handlers
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      handleMove(e.clientY)
    }

    const handleMouseUp = () => {
      handleEnd()
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleMove, handleEnd])

  return {
    trackRef,
    trackProps: {
      onTouchStart,
      onTouchMove,
      onTouchEnd,
      onMouseDown,
    },
  }
}
