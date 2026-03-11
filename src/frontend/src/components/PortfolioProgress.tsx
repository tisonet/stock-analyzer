import type { PortfolioStock } from '../types/analysis'

interface PortfolioProgressProps {
  stocks: PortfolioStock[]
}

function getVerdictColor(score: number): string {
  if (score >= 75) return 'text-green-400'
  if (score >= 55) return 'text-blue-400'
  if (score >= 40) return 'text-yellow-400'
  return 'text-red-400'
}

function getVerdict(score: number): string {
  if (score >= 75) return 'Strong Buy'
  if (score >= 55) return 'Buy'
  if (score >= 40) return 'Hold'
  return 'Avoid'
}

export default function PortfolioProgress({ stocks }: PortfolioProgressProps) {
  const done = stocks.filter((s) => s.status === 'success' || s.status === 'error').length
  const total = stocks.length
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-gray-200">
          Analyzing portfolio... {done}/{total} complete
        </h2>
      </div>

      {/* Progress bar */}
      <div className="bg-gray-800 rounded-full h-2 overflow-hidden">
        <div
          className="h-2 rounded-full bg-blue-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Per-ticker status */}
      <div className="space-y-2">
        {stocks.map((stock) => (
          <div
            key={stock.ticker}
            className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg px-4 py-2.5"
          >
            {/* Status icon */}
            <div className="w-5 flex-shrink-0">
              {stock.status === 'success' && (
                <span className="text-green-400">&#10003;</span>
              )}
              {stock.status === 'error' && (
                <span className="text-red-400">&#10007;</span>
              )}
              {stock.status === 'loading' && (
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              )}
              {stock.status === 'pending' && (
                <span className="block w-2 h-2 bg-gray-600 rounded-full mx-auto" />
              )}
            </div>

            {/* Ticker */}
            <span className="text-gray-200 font-medium text-sm w-16">{stock.ticker}</span>

            {/* Result or status text */}
            <div className="flex-1 text-sm">
              {stock.status === 'success' && stock.result && (
                <span className={getVerdictColor(stock.result.weighted_avg)}>
                  {Math.round(stock.result.weighted_avg)} — {getVerdict(stock.result.weighted_avg)}
                </span>
              )}
              {stock.status === 'error' && (
                <span className="text-red-400">{stock.error || 'Failed'}</span>
              )}
              {stock.status === 'loading' && (
                <span className="text-gray-500">Analyzing...</span>
              )}
              {stock.status === 'pending' && (
                <span className="text-gray-600">Queued</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
