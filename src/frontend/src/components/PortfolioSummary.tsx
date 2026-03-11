import type { ConsensusScore } from '../types/analysis'
import ScoreGauge from './ScoreGauge'

interface PortfolioSummaryProps {
  results: Map<string, ConsensusScore>
  onEdit: () => void
}

function getVerdictBadge(verdict: string): string {
  switch (verdict) {
    case 'Strong Buy':
      return 'bg-green-500/20 text-green-400 border-green-500/40'
    case 'Buy':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/40'
    case 'Hold':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40'
    default:
      return 'bg-red-500/20 text-red-400 border-red-500/40'
  }
}

function getVerdict(score: number): string {
  if (score >= 75) return 'Strong Buy'
  if (score >= 55) return 'Buy'
  if (score >= 40) return 'Hold'
  return 'Avoid'
}

export default function PortfolioSummary({ results, onEdit }: PortfolioSummaryProps) {
  const scores = Array.from(results.values())
  const avgScore = scores.reduce((sum, s) => sum + s.weighted_avg, 0) / scores.length

  const verdictCounts: Record<string, number> = {
    'Strong Buy': 0,
    Buy: 0,
    Hold: 0,
    Avoid: 0,
  }
  const agreementCounts: Record<string, number> = { 'High Conviction': 0, Mixed: 0, Divided: 0 }

  for (const s of scores) {
    const v = getVerdict(s.weighted_avg)
    verdictCounts[v] = (verdictCounts[v] || 0) + 1
    agreementCounts[s.agreement_level] = (agreementCounts[s.agreement_level] || 0) + 1
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 mb-6">
      <div className="flex flex-col md:flex-row items-center gap-6">
        {/* Big gauge */}
        <div className="flex-shrink-0">
          <ScoreGauge score={avgScore} size="lg" />
          <p className="text-center text-gray-400 text-sm mt-1">Portfolio Avg</p>
        </div>

        {/* Right side */}
        <div className="flex-1 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-100">Portfolio Overview</h2>
              <p className="text-gray-500 text-sm mt-1">
                {scores.length} stock{scores.length === 1 ? '' : 's'} analyzed
                {agreementCounts['High Conviction'] > 0 &&
                  ` \u00b7 ${agreementCounts['High Conviction']} High Conviction`}
              </p>
            </div>
            <button
              onClick={onEdit}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-gray-100 transition-colors"
            >
              Edit Portfolio
            </button>
          </div>

          {/* Verdict distribution */}
          <div className="flex flex-wrap gap-2">
            {Object.entries(verdictCounts).map(
              ([verdict, count]) =>
                count > 0 && (
                  <span
                    key={verdict}
                    className={`text-xs font-medium px-3 py-1.5 rounded-full border ${getVerdictBadge(verdict)}`}
                  >
                    {count} {verdict}
                  </span>
                )
            )}
          </div>

          {/* Mini score bars */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {scores
              .sort((a, b) => b.weighted_avg - a.weighted_avg)
              .map((s) => (
                <div key={s.ticker} className="flex items-center gap-2">
                  <span className="text-gray-400 text-xs w-12 font-medium">{s.ticker}</span>
                  <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full transition-all"
                      style={{
                        width: `${s.weighted_avg}%`,
                        backgroundColor:
                          s.weighted_avg >= 75
                            ? '#22c55e'
                            : s.weighted_avg >= 55
                            ? '#3b82f6'
                            : s.weighted_avg >= 40
                            ? '#eab308'
                            : '#ef4444',
                      }}
                    />
                  </div>
                  <span className="text-gray-400 text-xs w-8 text-right">
                    {Math.round(s.weighted_avg)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  )
}
