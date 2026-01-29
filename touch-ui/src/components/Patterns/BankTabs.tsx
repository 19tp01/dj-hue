import { memo } from 'react'
import type { BankName } from '../../types'
import { BANK_ORDER } from '../../types'

interface BankTabsProps {
  currentBank: BankName
  activePatternBank: BankName | null
  onBankChange: (bank: BankName) => void
}

const BANK_ICONS: Record<BankName, string> = {
  'Ambient': '◐',    // Half moon - calm, ambient
  'Buildup': '△',    // Triangle up - energy rising
  'Chill': '○',      // Circle - smooth, relaxed
  'Upbeat': '◇',     // Diamond - dynamic, energetic
}

export const BankTabs = memo(function BankTabs({
  currentBank,
  activePatternBank,
  onBankChange,
}: BankTabsProps) {
  return (
    <nav className="h-full flex">
      {BANK_ORDER.map((bank) => {
        const isActive = bank === currentBank
        const hasActivePattern = bank === activePatternBank

        return (
          <button
            key={bank}
            onClick={() => onBankChange(bank)}
            className={`
              flex-1 flex items-center justify-center gap-2
              font-medium text-sm uppercase tracking-wider
              transition-all duration-75 active:scale-[0.98]
              relative
            `}
            style={{
              background: isActive ? 'var(--bg-elevated)' : 'transparent',
              color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
              borderBottom: isActive ? '2px solid var(--accent-bright)' : '2px solid transparent',
            }}
          >
            <span className="text-base">{BANK_ICONS[bank]}</span>
            <span>{bank}</span>

            {/* Indicator dot for bank containing active pattern */}
            {hasActivePattern && !isActive && (
              <span
                className="absolute top-2 right-2 w-2 h-2 rounded-full"
                style={{
                  background: 'var(--accent-bright)',
                  boxShadow: 'var(--glow-cyan)',
                }}
              />
            )}
          </button>
        )
      })}
    </nav>
  )
})
