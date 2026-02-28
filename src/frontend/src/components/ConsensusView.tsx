import type { ConsensusScore } from '../types/analysis'
import ScoreGauge from './ScoreGauge'

function getVerdictFromScore(score: number): string {
  if (score >= 75) return 'Strong Buy'
  if (score >= 55) return 'Buy'
  if (score >= 40) return 'Hold'
  return 'Avoid'
}

function getAgreementColor(level: string): string {
  if (level === 'High Conviction') return 'bg-green-500/20 text-green-400 border-green-500/40'
  if (level === 'Mixed') return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40'
  return 'bg-red-500/20 text-red-400 border-red-500/40'
}

interface ConsensusViewProps {
  consensus: ConsensusScore
}

export default function ConsensusView({ consensus }: ConsensusViewProps) {
  const verdict = getVerdictFromScore(consensus.weighted_avg)
  const agreementColor = getAgreementColor(consensus.agreement_level)

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 mb-8">
      <div className="flex flex-col md:flex-row items-center gap-6">
        {/* Big gauge */}
        <div className="flex-shrink-0">
          <ScoreGauge score={consensus.weighted_avg} size="lg" />
          <p className="text-center text-gray-400 text-sm mt-1">Consensus Score</p>
        </div>

        {/* Right side */}
        <div className="flex-1 space-y-4">
          <div>
            <h2 className="text-3xl font-bold text-gray-100">{consensus.ticker}</h2>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-xl font-semibold text-gray-300">{verdict}</span>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full border ${agreementColor}`}
              >
                {consensus.agreement_level}
              </span>
            </div>
          </div>

          {/* Mini score bars for each investor */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {consensus.investor_scores.map((s) => (
              <div key={s.investor} className="flex items-center gap-2">
                <span className="text-gray-400 text-xs w-14">{s.investor}</span>
                <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full transition-all"
                    style={{
                      width: `${s.total_score}%`,
                      backgroundColor:
                        s.total_score >= 75
                          ? '#22c55e'
                          : s.total_score >= 55
                          ? '#3b82f6'
                          : s.total_score >= 40
                          ? '#eab308'
                          : '#ef4444',
                    }}
                  />
                </div>
                <span className="text-gray-400 text-xs w-8 text-right">
                  {Math.round(s.total_score)}
                </span>
              </div>
            ))}
          </div>

          {/* Narrative */}
          {consensus.overall_narrative && (
            <p className="text-gray-300 text-sm leading-relaxed border-t border-gray-700 pt-4">
              {consensus.overall_narrative}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
