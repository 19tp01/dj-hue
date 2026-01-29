import { useMemo, useState, useCallback } from 'react'
import type { BankName, PatternInfo, PatternSlot } from '../types'
import { BANK_ORDER } from '../types'

interface UsePatternBanksReturn {
  currentBank: BankName
  setCurrentBank: (bank: BankName) => void
  banks: Record<BankName, PatternSlot[]>
  activePatternBank: BankName | null
  getBankForPattern: (patternIndex: number) => BankName | null
}

export function usePatternBanks(
  patterns: (PatternInfo | string)[],
  activePatternIndex: number
): UsePatternBanksReturn {
  const [currentBank, setCurrentBank] = useState<BankName>('Ambient')

  // Build banks from patterns using category field
  const banks = useMemo(() => {
    const result: Record<BankName, PatternSlot[]> = {
      'Ambient': [],
      'Buildup': [],
      'Chill': [],
      'Upbeat': [],
    }

    patterns.forEach((pattern, index) => {
      const name = typeof pattern === 'string' ? pattern : pattern.name
      const tags = typeof pattern === 'string' ? [] : (pattern.tags || [])

      // Use category directly if available, default to 'Chill'
      let category: BankName = 'Chill'
      if (typeof pattern !== 'string' && pattern.category) {
        category = pattern.category
      }

      // Add to the category bank
      result[category].push({
        patternIndex: index,
        patternName: name,
        tags,
      })
    })

    return result
  }, [patterns])

  // Find which bank contains the active pattern
  const activePatternBank = useMemo((): BankName | null => {
    for (const bank of BANK_ORDER) {
      if (banks[bank].some(slot => slot.patternIndex === activePatternIndex)) {
        return bank
      }
    }
    return null
  }, [banks, activePatternIndex])

  // Helper to get bank for any pattern index
  const getBankForPattern = useCallback((patternIndex: number): BankName | null => {
    for (const bank of BANK_ORDER) {
      if (banks[bank].some(slot => slot.patternIndex === patternIndex)) {
        return bank
      }
    }
    return null
  }, [banks])

  return {
    currentBank,
    setCurrentBank,
    banks,
    activePatternBank,
    getBankForPattern,
  }
}
