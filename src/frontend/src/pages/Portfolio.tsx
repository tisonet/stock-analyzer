import { useState, useCallback, useRef } from 'react'
import type { ConsensusScore, PortfolioStock } from '../types/analysis'
import { analyzePortfolio } from '../api/client'
import PortfolioInput from '../components/PortfolioInput'
import PortfolioProgress from '../components/PortfolioProgress'
import PortfolioSummary from '../components/PortfolioSummary'
import PortfolioActions from '../components/PortfolioActions'
import PortfolioTable from '../components/PortfolioTable'
import PortfolioHeatmap from '../components/PortfolioHeatmap'

type PageState = 'input' | 'analyzing' | 'results'

interface PortfolioProps {
  onViewStock: (ticker: string) => void
  onSwitchToSingle: () => void
  onHasResults?: (has: boolean) => void
}

export default function Portfolio({ onViewStock, onSwitchToSingle, onHasResults }: PortfolioProps) {
  const [pageState, setPageState] = useState<PageState>('input')
  const [stocks, setStocks] = useState<PortfolioStock[]>([])
  const [results, setResults] = useState<Map<string, ConsensusScore>>(new Map())
  const [lastTickers, setLastTickers] = useState<string[]>([])
  const resultsRef = useRef<Map<string, ConsensusScore>>(new Map())

  const handleAnalyze = useCallback(async (tickers: string[]) => {
    setLastTickers(tickers)
    setPageState('analyzing')
    resultsRef.current = new Map()
    setResults(new Map())

    // Initialize all stocks as loading
    const initial: PortfolioStock[] = tickers.map((t) => ({
      ticker: t,
      result: null,
      status: 'loading',
    }))
    setStocks(initial)

    await analyzePortfolio(tickers, (ticker, result, error) => {
      setStocks((prev) =>
        prev.map((s) =>
          s.ticker === ticker
            ? {
                ...s,
                result,
                status: error ? 'error' : 'success',
                error,
              }
            : s
        )
      )
      if (result) {
        resultsRef.current = new Map(resultsRef.current).set(ticker, result)
        setResults(new Map(resultsRef.current))
      }
    })

    setResults(new Map(resultsRef.current))
    setPageState('results')
    onHasResults?.(resultsRef.current.size > 0)
  }, [onHasResults])

  const handleEdit = useCallback(() => {
    setPageState('input')
  }, [])

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-2xl">📈</span>
            <div>
              <h1 className="text-gray-100 font-bold text-lg leading-tight">SuperInvestor</h1>
              <p className="text-gray-500 text-xs">Stock Analyzer</p>
            </div>
          </div>

          {/* Mode pills */}
          <div className="flex bg-gray-800 rounded-lg p-0.5">
            <button
              onClick={onSwitchToSingle}
              className="px-4 py-1.5 text-sm rounded-md font-medium transition-colors text-gray-500 hover:text-gray-300"
            >
              Single Stock
            </button>
            <button className="px-4 py-1.5 text-sm rounded-md font-medium transition-colors bg-gray-700 text-gray-100">
              Portfolio
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Input phase */}
        {pageState === 'input' && (
          <PortfolioInput
            onAnalyze={handleAnalyze}
            loading={false}
            initialTickers={lastTickers.length > 0 ? lastTickers : undefined}
          />
        )}

        {/* Analyzing phase */}
        {pageState === 'analyzing' && <PortfolioProgress stocks={stocks} />}

        {/* Results phase */}
        {pageState === 'results' && results.size > 0 && (
          <div>
            <PortfolioSummary results={results} onEdit={handleEdit} />
            <PortfolioActions results={results} onViewStock={onViewStock} />
            <PortfolioTable results={results} onViewStock={onViewStock} />
            <PortfolioHeatmap results={results} />
          </div>
        )}

        {/* Results phase but all failed */}
        {pageState === 'results' && results.size === 0 && (
          <div className="text-center py-24 space-y-4">
            <p className="text-4xl">&#10060;</p>
            <p className="text-red-400 text-lg">All analyses failed</p>
            <button
              onClick={handleEdit}
              className="text-blue-400 hover:text-blue-300 text-sm underline"
            >
              Try different tickers
            </button>
          </div>
        )}
      </main>

      <footer className="border-t border-gray-800 mt-16 py-6 text-center text-gray-600 text-xs">
        SuperInvestor Stock Analyzer — Educational purposes only. Not financial advice.
      </footer>
    </div>
  )
}
