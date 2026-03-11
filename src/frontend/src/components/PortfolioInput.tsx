import { useState, useEffect, useRef } from 'react'

const PRESETS: Record<string, string[]> = {
  'Mag 7': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
  'FAANG': ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL'],
  'Berkshire Top 5': ['AAPL', 'AXP', 'BAC', 'KO', 'CVX'],
}

const MAX_TICKERS = 20
const STORAGE_KEY = 'superinvestor_portfolio'

interface PortfolioInputProps {
  onAnalyze: (tickers: string[]) => void
  loading: boolean
  initialTickers?: string[]
}

export default function PortfolioInput({ onAnalyze, loading, initialTickers }: PortfolioInputProps) {
  const [tickers, setTickers] = useState<string[]>(() => {
    if (initialTickers?.length) return initialTickers
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tickers))
  }, [tickers])

  const addTickers = (raw: string) => {
    const newTickers = raw
      .toUpperCase()
      .split(/[\s,;]+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0 && t.length <= 10)
    setTickers((prev) => {
      const combined = [...prev]
      for (const t of newTickers) {
        if (!combined.includes(t) && combined.length < MAX_TICKERS) {
          combined.push(t)
        }
      }
      return combined
    })
    setInput('')
  }

  const removeTicker = (ticker: string) => {
    setTickers((prev) => prev.filter((t) => t !== ticker))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',' || e.key === ' ') {
      e.preventDefault()
      if (input.trim()) addTickers(input)
    }
    if (e.key === 'Backspace' && !input && tickers.length > 0) {
      setTickers((prev) => prev.slice(0, -1))
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text')
    addTickers(pasted)
  }

  const handlePreset = (name: string) => {
    setTickers(PRESETS[name])
    setInput('')
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <p className="text-5xl">📊</p>
        <h2 className="text-2xl font-semibold text-gray-200">Portfolio Analysis</h2>
        <p className="text-gray-500">
          Enter your portfolio tickers to get a comprehensive analysis and ranking.
        </p>
      </div>

      {/* Chip input */}
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl p-3 cursor-text"
        onClick={() => inputRef.current?.focus()}
      >
        <div className="flex flex-wrap gap-2 items-center">
          {tickers.map((t) => (
            <span
              key={t}
              className="inline-flex items-center gap-1 bg-gray-800 text-gray-200 px-3 py-1 rounded-lg text-sm font-medium border border-gray-700"
            >
              {t}
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  removeTicker(t)
                }}
                className="text-gray-500 hover:text-red-400 ml-1"
              >
                &times;
              </button>
            </span>
          ))}
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            onBlur={() => { if (input.trim()) addTickers(input) }}
            placeholder={tickers.length === 0 ? 'Type ticker symbols (e.g. AAPL, MSFT, GOOGL)' : tickers.length >= MAX_TICKERS ? `Max ${MAX_TICKERS} tickers` : 'Add more...'}
            disabled={tickers.length >= MAX_TICKERS}
            className="flex-1 min-w-[120px] bg-transparent text-gray-200 placeholder-gray-600 outline-none text-sm py-1"
          />
        </div>
      </div>

      {/* Presets */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-gray-500 text-xs">Quick portfolios:</span>
        {Object.keys(PRESETS).map((name) => (
          <button
            key={name}
            onClick={() => handlePreset(name)}
            className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 border border-gray-700 transition-colors"
          >
            {name}
          </button>
        ))}
        {tickers.length > 0 && (
          <button
            onClick={() => setTickers([])}
            className="text-xs px-3 py-1.5 rounded-lg text-red-400 hover:text-red-300 hover:bg-gray-800 transition-colors ml-auto"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Analyze button */}
      <button
        onClick={() => onAnalyze(tickers)}
        disabled={tickers.length === 0 || loading}
        className="w-full py-3 rounded-xl font-semibold text-sm transition-colors bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading
          ? 'Analyzing...'
          : tickers.length === 0
          ? 'Add tickers to analyze'
          : `Analyze Portfolio (${tickers.length} stock${tickers.length === 1 ? '' : 's'})`}
      </button>
    </div>
  )
}
