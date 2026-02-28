import type { InvestorScore } from '../types/analysis'

interface ScenarioTabProps {
  investor_scores: InvestorScore[]
}

const INVESTOR_ICONS: Record<string, string> = {
  Buffett: '🏦',
  Munger: '🧠',
  Graham: '📊',
  Lynch: '🔍',
  Dalio: '⚖️',
  Klarman: '🛡️',
}

export default function ScenarioTab({ investor_scores }: ScenarioTabProps) {
  const withFlags = investor_scores.filter((s) => s.red_flags.length > 0)

  if (withFlags.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mt-4">
        <h3 className="text-gray-100 font-semibold text-lg mb-2">Scenario Analysis</h3>
        <p className="text-gray-400 text-sm">
          No major red flags identified across all investors.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mt-4">
      <h3 className="text-gray-100 font-semibold text-lg mb-1">Scenario Analysis</h3>
      <p className="text-gray-500 text-sm mb-4">
        What would need to change for each investor to approve this stock?
      </p>
      <div className="space-y-4">
        {withFlags.map((score) => (
          <div key={score.investor}>
            <div className="flex items-center gap-2 mb-2">
              <span>{INVESTOR_ICONS[score.investor] || '📈'}</span>
              <span className="font-medium text-gray-200">{score.investor}</span>
              <span className="text-gray-500 text-xs">
                ({score.total_score.toFixed(0)}/100 — {score.verdict})
              </span>
            </div>
            <ul className="space-y-1.5 ml-6">
              {score.red_flags.map((flag, i) => (
                <li key={i} className="text-sm text-gray-400 flex gap-2 items-start">
                  <span className="text-yellow-500 flex-shrink-0 mt-0.5">→</span>
                  <span>{flag.replace('[Munger Inversion] ', '')}</span>
                </li>
              ))}
              {score.rules_failed.slice(0, 3).map((rule) => (
                <li key={rule.name} className="text-sm text-gray-500 flex gap-2 items-start">
                  <span className="text-gray-600 flex-shrink-0 mt-0.5">→</span>
                  <span>
                    Fix <span className="text-gray-400">{rule.name}</span>
                    {rule.value !== null && (
                      <span className="text-gray-500">
                        {' '}(currently {rule.value.toFixed(2)}, needs {rule.threshold})
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
