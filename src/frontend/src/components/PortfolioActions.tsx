import type { ConsensusScore } from '../types/analysis'

interface PortfolioActionsProps {
  results: Map<string, ConsensusScore>
  onViewStock: (ticker: string) => void
}

function getVerdict(score: number): string {
  if (score >= 75) return 'Strong Buy'
  if (score >= 55) return 'Buy'
  if (score >= 40) return 'Hold'
  return 'Avoid'
}

function getVerdictColor(score: number): string {
  if (score >= 75) return 'text-green-400'
  if (score >= 55) return 'text-blue-400'
  if (score >= 40) return 'text-yellow-400'
  return 'text-red-400'
}

function getTopInvestor(result: ConsensusScore, mode: 'highest' | 'lowest'): string {
  const investors = result.investor_scores.filter(
    (s) => s.investor !== 'Moat Score' && s.investor !== 'Red Flag Score'
  )
  if (investors.length === 0) return ''
  const sorted = [...investors].sort((a, b) =>
    mode === 'highest' ? b.total_score - a.total_score : a.total_score - b.total_score
  )
  return `${sorted[0].investor} (${Math.round(sorted[0].total_score)})`
}

export default function PortfolioActions({ results, onViewStock }: PortfolioActionsProps) {
  const sorted = Array.from(results.values()).sort((a, b) => b.weighted_avg - a.weighted_avg)

  const topPicks = sorted.filter((s) => s.weighted_avg >= 55).slice(0, 3)
  const sellCandidates = [...sorted]
    .reverse()
    .filter((s) => s.weighted_avg < 40)
    .slice(0, 3)

  if (topPicks.length === 0 && sellCandidates.length === 0) return null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
      {/* Top Picks */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 border-l-4 border-l-green-500">
        <h3 className="text-sm font-semibold text-green-400 uppercase tracking-wider mb-4">
          Top Picks
        </h3>
        {topPicks.length === 0 ? (
          <p className="text-gray-500 text-sm">No stocks scoring Buy or above</p>
        ) : (
          <div className="space-y-3">
            {topPicks.map((stock, i) => (
              <button
                key={stock.ticker}
                onClick={() => onViewStock(stock.ticker)}
                className="w-full text-left flex items-center gap-3 hover:bg-gray-800 rounded-lg p-2 -m-2 transition-colors"
              >
                <span className="text-gray-600 text-sm font-medium w-5">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-100 font-semibold">{stock.ticker}</span>
                    <span className={`text-sm font-medium ${getVerdictColor(stock.weighted_avg)}`}>
                      {Math.round(stock.weighted_avg)}
                    </span>
                    <span className={`text-xs ${getVerdictColor(stock.weighted_avg)}`}>
                      {getVerdict(stock.weighted_avg)}
                    </span>
                  </div>
                  <p className="text-gray-500 text-xs mt-0.5 truncate">
                    {stock.agreement_level} &middot; Top: {getTopInvestor(stock, 'highest')}
                  </p>
                </div>
                <span className="text-gray-600 text-xs">&rsaquo;</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Consider Selling */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 border-l-4 border-l-red-500">
        <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-4">
          Consider Selling
        </h3>
        {sellCandidates.length === 0 ? (
          <p className="text-gray-500 text-sm">No stocks scoring Avoid</p>
        ) : (
          <div className="space-y-3">
            {sellCandidates.map((stock, i) => (
              <button
                key={stock.ticker}
                onClick={() => onViewStock(stock.ticker)}
                className="w-full text-left flex items-center gap-3 hover:bg-gray-800 rounded-lg p-2 -m-2 transition-colors"
              >
                <span className="text-gray-600 text-sm font-medium w-5">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-100 font-semibold">{stock.ticker}</span>
                    <span className={`text-sm font-medium ${getVerdictColor(stock.weighted_avg)}`}>
                      {Math.round(stock.weighted_avg)}
                    </span>
                    <span className={`text-xs ${getVerdictColor(stock.weighted_avg)}`}>
                      {getVerdict(stock.weighted_avg)}
                    </span>
                  </div>
                  <p className="text-gray-500 text-xs mt-0.5 truncate">
                    {stock.agreement_level} &middot; Lowest: {getTopInvestor(stock, 'lowest')}
                  </p>
                </div>
                <span className="text-gray-600 text-xs">&rsaquo;</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
