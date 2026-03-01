/**
 * RedFlagCard — Dedicated display panel for the AntiMoatInvestor (Red Flag Score).
 *
 * The mirror image of MoatCard: detects distress signals and competitive decay
 * rather than confirming competitive strengths.
 *
 * Score semantics (intentionally inverted):
 *   total_score 0–100: higher = safer/cleaner company
 *   danger_score = (100 - total_score) / 10  displayed as X.X / 10
 *   verdict: "Clean" | "Watch" | "Caution" | "Danger" | "Critical"
 *
 * Verdict is derived from total_score:
 *   >= 80 -> "Clean"    (danger 0.0–2.0)
 *   >= 60 -> "Watch"    (danger 2.0–4.0)
 *   >= 40 -> "Caution"  (danger 4.0–6.0)
 *   >= 20 -> "Danger"   (danger 6.0–8.0)
 *    < 20 -> "Critical" (danger 8.0–10.0)
 */
import { useState } from 'react'
import type { InvestorScore, DangerLabel } from '../types/analysis'
import RuleBreakdown from './RuleBreakdown'

const DANGER_STYLES: Record<DangerLabel, { badge: string; barColor: string }> = {
  Clean: {
    badge: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40',
    barColor: '#10b981',
  },
  Watch: {
    badge: 'bg-blue-500/20 text-blue-400 border border-blue-500/40',
    barColor: '#3b82f6',
  },
  Caution: {
    badge: 'bg-amber-500/20 text-amber-400 border border-amber-500/40',
    barColor: '#f59e0b',
  },
  Danger: {
    badge: 'bg-orange-500/20 text-orange-400 border border-orange-500/40',
    barColor: '#f97316',
  },
  Critical: {
    badge: 'bg-red-500/20 text-red-400 border border-red-500/40',
    barColor: '#ef4444',
  },
}

interface RedFlagCardProps {
  score: InvestorScore
}

export default function RedFlagCard({ score }: RedFlagCardProps) {
  const [showRules, setShowRules] = useState(false)

  const dangerLabel = score.verdict as DangerLabel
  const styles = DANGER_STYLES[dangerLabel] ?? DANGER_STYLES['Critical']

  // Danger is the inverse of the safety score
  const dangerScore = (100 - score.total_score) / 10
  const displayScore = dangerScore.toFixed(1)

  // Progress bar fills based on danger (not safety)
  const barWidth = `${100 - score.total_score}%`

  const flagCount = score.rules_failed.length
  const totalRules = score.rules_passed.length + score.rules_failed.length

  const allRules = [
    ...score.rules_passed,
    ...score.rules_failed,
  ].sort((a, b) => b.points_possible - a.points_possible)

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🚨</span>
          <div>
            <span className="font-semibold text-gray-100 text-lg">Red Flag Analysis</span>
            <p className="text-xs text-gray-500 mt-0.5">
              12 forensic metrics · analytical only
            </p>
          </div>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${styles.badge}`}>
          {dangerLabel}
        </span>
      </div>

      {/* Score display */}
      <div className="space-y-2">
        <div className="flex items-end gap-2">
          <span className="text-4xl font-bold text-gray-100">{displayScore}</span>
          <span className="text-gray-500 text-lg mb-1">/ 10</span>
          <span className="text-gray-600 text-sm mb-1.5 ml-1">
            ({flagCount} flag{flagCount !== 1 ? 's' : ''} triggered / {totalRules} criteria)
          </span>
        </div>

        {/* Danger progress bar (fills left→right with danger) */}
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div
            className="h-3 rounded-full transition-all duration-700"
            style={{ width: barWidth, backgroundColor: styles.barColor }}
          />
        </div>

        {/* Scale labels */}
        <div className="flex justify-between text-xs text-gray-600">
          <span>0 — Clean</span>
          <span>3 — Watch</span>
          <span>5 — Caution</span>
          <span>7 — Danger</span>
          <span>10 — Critical</span>
        </div>
      </div>

      {/* Claude red flag insight */}
      {score.key_insight && (
        <div className="border-l-2 border-gray-700 pl-3">
          <p className="text-gray-300 text-sm leading-relaxed italic">{score.key_insight}</p>
        </div>
      )}

      {/* Triggered red flags */}
      {score.red_flags.length > 0 && (
        <div className="space-y-1.5">
          {score.red_flags.map((flag, i) => (
            <p key={i} className="text-xs text-red-400 flex gap-1.5 items-start">
              <span className="flex-shrink-0 mt-0.5">🚨</span>
              <span>{flag}</span>
            </p>
          ))}
        </div>
      )}

      {score.red_flags.length === 0 && (
        <p className="text-xs text-emerald-400 flex gap-1.5 items-center">
          <span>✅</span>
          <span>No significant red flags detected across all 12 forensic criteria.</span>
        </p>
      )}

      {/* Toggle criteria breakdown */}
      <button
        onClick={() => setShowRules(!showRules)}
        className="text-xs text-gray-500 hover:text-gray-300 transition-colors text-left"
      >
        {showRules ? '▲ Hide criteria breakdown' : '▼ Show 12 red flag criteria breakdown'}
      </button>

      {showRules && <RuleBreakdown rules={allRules} />}
    </div>
  )
}
