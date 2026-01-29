import { ReactNode } from 'react'

interface AppLayoutProps {
  statusBar: ReactNode
  bankTabs: ReactNode
  patternGrid: ReactNode
  paletteStrip: ReactNode
  zoneFaders: ReactNode
  transport: ReactNode
}

export function AppLayout({
  statusBar,
  bankTabs,
  patternGrid,
  paletteStrip,
  zoneFaders,
  transport,
}: AppLayoutProps) {
  return (
    <div className="app-layout texture-noise relative">
      <header className="area-status">
        {statusBar}
      </header>

      <nav className="area-banks">
        {bankTabs}
      </nav>

      <main className="area-patterns">
        {patternGrid}
      </main>

      <section className="area-palettes">
        {paletteStrip}
      </section>

      <aside className="area-faders">
        <div className="faders-content">
          {zoneFaders}
        </div>
        <div className="transport-content">
          {transport}
        </div>
      </aside>

      <style>{`
        .app-layout {
          display: grid;
          grid-template-columns: 1fr 200px;
          grid-template-rows: 48px 48px 1fr 216px;
          grid-template-areas:
            "status faders"
            "banks faders"
            "patterns faders"
            "palettes faders";
          height: 100dvh;
          width: 100vw;
          overflow: hidden;
          background: var(--bg-void);
        }

        .area-status {
          grid-area: status;
          background: var(--bg-surface);
          border-bottom: 1px solid var(--bg-elevated);
        }

        .area-banks {
          grid-area: banks;
          background: var(--bg-surface);
          border-bottom: 1px solid var(--bg-elevated);
        }

        .area-patterns {
          grid-area: patterns;
          overflow: hidden;
          padding: 12px;
          display: flex;
          align-items: start;
        }

        .area-palettes {
          grid-area: palettes;
          background: var(--bg-surface);
          border-top: 1px solid var(--bg-elevated);
          overflow-x: auto;
          overflow-y: hidden;
        }

        .area-faders {
          grid-area: faders;
          background: var(--bg-surface);
          border-left: 1px solid var(--bg-elevated);
          display: flex;
          flex-direction: column;
        }

        .faders-content {
          flex: 1;
          padding: 16px 12px;
          min-height: 0;
        }

        .transport-content {
          flex-shrink: 0;
          padding: 16px 12px;
          border-top: 1px solid var(--bg-elevated);
        }

        /* Safe area handling for notched devices */
        @supports (padding: env(safe-area-inset-left)) {
          .app-layout {
            padding-left: env(safe-area-inset-left);
            padding-right: env(safe-area-inset-right);
          }
        }

        /* Responsive adjustments for iPad Pro / larger screens */
        @media (min-width: 1024px) {
          .app-layout {
            grid-template-columns: 1fr 240px;
          }
        }

        /* Smaller tablets - reduce fader panel */
        @media (max-width: 768px) {
          .app-layout {
            grid-template-columns: 1fr 180px;
          }
        }
      `}</style>
    </div>
  )
}
