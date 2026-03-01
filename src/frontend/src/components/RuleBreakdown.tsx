import { useState } from 'react'
import type { Rule } from '../types/analysis'

interface RuleBreakdownProps {
  rules: Rule[]
}

function RuleItem({ rule }: { rule: Rule }) {
  const [open, setOpen] = useState(false)

  const ptsFraction = rule.points_possible > 0
    ? rule.points_awarded / rule.points_possible
    : 0

  const noData  = rule.value === null
  const barColor = rule.passed ? '#22c55e' : noData ? '#6b7280' : '#ef4444'

  const statusLabel = noData ? 'No data' : rule.passed ? 'Pass' : 'Fail'
  const statusClass = noData
    ? 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
    : rule.passed
    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
    : 'bg-red-500/20 text-red-400 border border-red-500/30'

  const delta = rule.value !== null ? rule.value - rule.threshold : null

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      {/* ── Collapsed row ── */}
      <button
        className="w-full flex items-start gap-3 px-4 py-2.5 bg-gray-800 hover:bg-gray-750 text-left"
        onClick={() => setOpen(!open)}
      >
        {/* Status icon */}
        <span className="text-lg flex-shrink-0 mt-0.5">
          {noData ? '⚪' : rule.passed ? '✅' : '❌'}
        </span>

        {/* Name + pts bar (stacked, name wraps freely) */}
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-gray-200 leading-snug">
            {rule.name}
          </span>
          <div className="flex items-center gap-2 mt-1.5">
            <div className="w-20 bg-gray-700 rounded-full h-1.5 flex-shrink-0">
              <div
                className="h-1.5 rounded-full transition-all"
                style={{ width: `${ptsFraction * 100}%`, backgroundColor: barColor }}
              />
            </div>
            <span className="text-xs text-gray-500">
              {rule.points_awarded.toFixed(0)}/{rule.points_possible.toFixed(0)} pts
            </span>
          </div>
        </div>

        {/* Toggle arrow */}
        <span className="text-gray-500 text-xs mt-1 flex-shrink-0">
          {open ? '▲' : '▼'}
        </span>
      </button>

      {/* ── Expanded panel ── */}
      {open && (
        <div className="px-4 py-3 bg-gray-900 text-sm space-y-3 border-t border-gray-700">

          {/* Pass/Fail badge + value vs threshold */}
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${statusClass}`}>
              {statusLabel}
            </span>
            {rule.value !== null && (
              <div className="flex items-center gap-3 text-xs text-gray-300 flex-wrap">
                <span>
                  <span className="text-gray-500">Value </span>
                  <span className="font-mono font-medium">{rule.value.toFixed(2)}</span>
                </span>
                <span className="text-gray-600">·</span>
                <span>
                  <span className="text-gray-500">Threshold </span>
                  <span className="font-mono font-medium">{rule.threshold}</span>
                </span>
                {delta !== null && (
                  <>
                    <span className="text-gray-600">·</span>
                    <span className={delta >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {delta >= 0 ? '+' : ''}{delta.toFixed(2)}
                    </span>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Explanation — plain-language metric definition */}
          {rule.explanation && (
            <div className="bg-gray-800/60 rounded-md px-3 py-2 border border-gray-700/50">
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">
                What this measures
              </p>
              <p className="text-gray-300 text-xs leading-relaxed">{rule.explanation}</p>
            </div>
          )}

          {/* Computed result */}
          <p className="text-gray-400 text-xs leading-relaxed">{rule.description}</p>

          {/* Source */}
          <p className="text-gray-500 text-xs italic">📚 {rule.source}</p>
        </div>
      )}
    </div>
  )
}

export default function RuleBreakdown({ rules }: RuleBreakdownProps) {
  const sorted = [...rules].sort((a, b) => b.points_possible - a.points_possible)
  return (
    <div className="space-y-1.5">
      {sorted.map((rule) => (
        <RuleItem key={rule.name} rule={rule} />
      ))}
    </div>
  )
}
