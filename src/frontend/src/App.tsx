import { useState, useCallback, useRef } from 'react'
import Analysis from './pages/Analysis'
import Portfolio from './pages/Portfolio'

type AppMode = 'single' | 'portfolio'

function App() {
  const [mode, setMode] = useState<AppMode>('single')
  const [initialTicker, setInitialTicker] = useState<string>('')
  const [fromPortfolio, setFromPortfolio] = useState(false)
  const portfolioHasResults = useRef(false)

  const handleViewStock = useCallback((ticker: string) => {
    setInitialTicker(ticker)
    setFromPortfolio(true)
    setMode('single')
  }, [])

  const handleBackToPortfolio = useCallback(() => {
    setInitialTicker('')
    setFromPortfolio(false)
    setMode('portfolio')
  }, [])

  const handleSwitchToSingle = useCallback(() => {
    setInitialTicker('')
    setFromPortfolio(false)
    setMode('single')
  }, [])

  const handleSwitchToPortfolio = useCallback(() => {
    setInitialTicker('')
    setFromPortfolio(false)
    setMode('portfolio')
  }, [])

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Keep Portfolio mounted so state survives drill-down */}
      <div style={{ display: mode === 'portfolio' ? undefined : 'none' }}>
        <Portfolio
          onViewStock={handleViewStock}
          onSwitchToSingle={handleSwitchToSingle}
          onHasResults={(has: boolean) => { portfolioHasResults.current = has }}
        />
      </div>
      {mode === 'single' && (
        <Analysis
          initialTicker={initialTicker}
          onSwitchToPortfolio={handleSwitchToPortfolio}
          onBackToPortfolio={fromPortfolio ? handleBackToPortfolio : undefined}
        />
      )}
    </div>
  )
}

export default App
