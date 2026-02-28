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

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-2.5 bg-gray-800 hover:bg-gray-750 text-left"
        onClick={() => setOpen(!open)}
      >
        <span className="text-lg flex-shrink-0">
          {rule.value === null ? '⚪' : rule.passed ? '✅' : '❌'}
        </span>
        <span className="flex-1 text-sm font-medium text-gray-200 truncate">
          {rule.name}
        </span>
        <span className="text-xs text-gray-400 flex-shrink-0">
          {rule.points_awarded.toFixed(0)}/{rule.points_possible.toFixed(0)} pts
        </span>
        <div className="w-20 bg-gray-700 rounded-full h-1.5 flex-shrink-0">
          <div
            className="h-1.5 rounded-full transition-all"
            style={{
              width: `${ptsFraction * 100}%`,
              backgroundColor: rule.passed ? '#22c55e' : rule.value === null ? '#6b7280' : '#ef4444',
            }}
          />
        </div>
        <span className="text-gray-500 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-4 py-3 bg-gray-900 text-sm space-y-1.5">
          <div className="flex gap-6 text-gray-300">
            <span>
              <span className="text-gray-500">Value: </span>
              {rule.value !== null ? rule.value.toFixed(2) : 'N/A'}
            </span>
            <span>
              <span className="text-gray-500">Threshold: </span>
              {rule.threshold}
            </span>
          </div>
          <p className="text-gray-300">{rule.description}</p>
          <p className="text-gray-500 text-xs italic">Source: {rule.source}</p>
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
