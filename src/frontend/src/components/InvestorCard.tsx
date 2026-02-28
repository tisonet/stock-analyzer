import { useState } from 'react'
import type { InvestorScore, VerdictType } from '../types/analysis'
import ScoreGauge from './ScoreGauge'
import RuleBreakdown from './RuleBreakdown'
import QuotesPanel from './QuotesPanel'

const VERDICT_COLORS: Record<VerdictType, string> = {
  'Strong Buy': 'bg-green-500/20 text-green-400 border border-green-500/40',
  'Buy': 'bg-blue-500/20 text-blue-400 border border-blue-500/40',
  'Hold': 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
  'Avoid': 'bg-red-500/20 text-red-400 border border-red-500/40',
}

const INVESTOR_ICONS: Record<string, string> = {
  Buffett: '🏦',
  Munger: '🧠',
  Graham: '📊',
  Lynch: '🔍',
  Dalio: '⚖️',
  Klarman: '🛡️',
  'Terry Smith': '🎯',
  'Icahn': '⚔️',
  'AKO Quality': '💎',
}

interface InvestorCardProps {
  score: InvestorScore
}

export default function InvestorCard({ score }: InvestorCardProps) {
  const [showRules, setShowRules] = useState(false)
  const allRules = [...score.rules_passed, ...score.rules_failed]
  const icon = INVESTOR_ICONS[score.investor] || '📈'

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-3 hover:border-gray-700 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <span className="font-semibold text-gray-100 text-lg">{score.investor}</span>
        </div>
        <span
          className={`text-xs font-semibold px-2 py-1 rounded-full ${VERDICT_COLORS[score.verdict as VerdictType]}`}
        >
          {score.verdict}
        </span>
      </div>

      {/* Gauge */}
      <ScoreGauge score={score.total_score} size="md" />

      {/* Score bar breakdown */}
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span>{score.rules_passed.length} passed</span>
        <div className="flex-1 bg-gray-700 rounded-full h-1.5">
          <div
            className="bg-green-500 h-1.5 rounded-full"
            style={{
              width: `${(score.rules_passed.length / (score.rules_passed.length + score.rules_failed.length || 1)) * 100}%`,
            }}
          />
        </div>
        <span>{score.rules_failed.length} failed</span>
      </div>

      {/* Key insight */}
      {score.key_insight && (
        <p className="text-gray-300 text-sm leading-relaxed">{score.key_insight}</p>
      )}

      {/* Quote */}
      <QuotesPanel investor={score.investor} verdict={score.verdict as VerdictType} />

      {/* Red flags */}
      {score.red_flags.length > 0 && (
        <div className="space-y-1">
          {score.red_flags
            .filter((f) => !f.startsWith('[Munger Inversion]'))
            .map((flag, i) => (
              <p key={i} className="text-xs text-red-400 flex gap-1.5 items-start">
                <span className="flex-shrink-0 mt-0.5">⚠</span>
                <span>{flag}</span>
              </p>
            ))}
        </div>
      )}

      {/* Toggle rule breakdown */}
      <button
        onClick={() => setShowRules(!showRules)}
        className="text-xs text-gray-500 hover:text-gray-300 transition-colors mt-1 text-left"
      >
        {showRules ? '▲ Hide rule breakdown' : '▼ Show rule breakdown'}
      </button>

      {showRules && <RuleBreakdown rules={allRules} />}
    </div>
  )
}
