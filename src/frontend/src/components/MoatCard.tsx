/**
 * MoatCard — Dedicated display panel for the MoatInvestor score.
 *
 * Renders the economic moat assessment separately from the buy/sell investor grid.
 * The moat score is expressed on a 0–10 scale (total_score / 10 internally).
 * Verdict labels: Wide Moat | Narrow Moat | Weak Moat | No Moat.
 */
import { useState } from 'react'
import type { InvestorScore, MoatStrengthLabel } from '../types/analysis'
import RuleBreakdown from './RuleBreakdown'

type MoatLabel = MoatStrengthLabel

const MOAT_STYLES: Record<MoatLabel, { badge: string; barColor: string }> = {
  'Wide Moat': {
    badge: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40',
    barColor: '#10b981',
  },
  'Narrow Moat': {
    badge: 'bg-blue-500/20 text-blue-400 border border-blue-500/40',
    barColor: '#3b82f6',
  },
  'Weak Moat': {
    badge: 'bg-amber-500/20 text-amber-400 border border-amber-500/40',
    barColor: '#f59e0b',
  },
  'No Moat': {
    badge: 'bg-red-500/20 text-red-400 border border-red-500/40',
    barColor: '#ef4444',
  },
}

interface MoatCardProps {
  score: InvestorScore
}

export default function MoatCard({ score }: MoatCardProps) {
  const [showRules, setShowRules] = useState(false)

  const moatLabel = score.verdict as MoatLabel
  const styles = MOAT_STYLES[moatLabel] ?? MOAT_STYLES['No Moat']
  const displayScore = (score.total_score / 10).toFixed(1)
  const barWidth = `${score.total_score}%`

  const allRules = [
    ...score.rules_passed,
    ...score.rules_failed,
  ].sort((a, b) => b.points_possible - a.points_possible)

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🏰</span>
          <div>
            <span className="font-semibold text-gray-100 text-lg">Economic Moat Analysis</span>
            <p className="text-xs text-gray-500 mt-0.5">
              GuruFocus-inspired · 9 criteria · analytical only
            </p>
          </div>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${styles.badge}`}>
          {moatLabel}
        </span>
      </div>

      {/* Score display */}
      <div className="space-y-2">
        <div className="flex items-end gap-2">
          <span className="text-4xl font-bold text-gray-100">{displayScore}</span>
          <span className="text-gray-500 text-lg mb-1">/ 10</span>
          <span className="text-gray-600 text-sm mb-1.5 ml-1">
            ({score.rules_passed.length}/9 criteria)
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div
            className="h-3 rounded-full transition-all duration-700"
            style={{ width: barWidth, backgroundColor: styles.barColor }}
          />
        </div>

        {/* Scale labels */}
        <div className="flex justify-between text-xs text-gray-600">
          <span>0 — No Moat</span>
          <span>4 — Weak</span>
          <span>6 — Narrow</span>
          <span>10 — Wide Moat</span>
        </div>
      </div>

      {/* Claude moat insight */}
      {score.key_insight && (
        <div className="border-l-2 border-gray-700 pl-3">
          <p className="text-gray-300 text-sm leading-relaxed italic">{score.key_insight}</p>
        </div>
      )}

      {/* Red flags (moat erosion signals) */}
      {score.red_flags.length > 0 && (
        <div className="space-y-1.5">
          {score.red_flags.map((flag, i) => (
            <p key={i} className="text-xs text-amber-400 flex gap-1.5 items-start">
              <span className="flex-shrink-0 mt-0.5">⚠</span>
              <span>{flag}</span>
            </p>
          ))}
        </div>
      )}

      {/* Toggle 9-criterion breakdown */}
      <button
        onClick={() => setShowRules(!showRules)}
        className="text-xs text-gray-500 hover:text-gray-300 transition-colors text-left"
      >
        {showRules ? '▲ Hide moat criteria' : '▼ Show 9 moat criteria breakdown'}
      </button>

      {showRules && <RuleBreakdown rules={allRules} />}
    </div>
  )
}
