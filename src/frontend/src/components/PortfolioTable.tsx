import { useState } from 'react'
import type { ConsensusScore } from '../types/analysis'
import { MOAT_INVESTOR_NAME, ANTI_MOAT_INVESTOR_NAME } from '../types/analysis'

interface PortfolioTableProps {
  results: Map<string, ConsensusScore>
  onViewStock: (ticker: string) => void
}

type SortKey = 'score' | 'ticker' | 'agreement' | 'moat' | 'risk'

function getVerdict(score: number): string {
  if (score >= 75) return 'Strong Buy'
  if (score >= 55) return 'Buy'
  if (score >= 40) return 'Hold'
  return 'Avoid'
}

function getVerdictBadge(score: number): string {
  if (score >= 75) return 'bg-green-500/20 text-green-400 border-green-500/40'
  if (score >= 55) return 'bg-blue-500/20 text-blue-400 border-blue-500/40'
  if (score >= 40) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40'
  return 'bg-red-500/20 text-red-400 border-red-500/40'
}

function getAgreementBadge(level: string): string {
  if (level === 'High Conviction') return 'bg-green-500/20 text-green-400 border-green-500/40'
  if (level === 'Mixed') return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40'
  return 'bg-red-500/20 text-red-400 border-red-500/40'
}

function getMoatLabel(result: ConsensusScore): string {
  const moat = result.investor_scores.find((s) => s.investor === MOAT_INVESTOR_NAME)
  if (!moat) return '—'
  if (moat.total_score >= 75) return 'Wide'
  if (moat.total_score >= 55) return 'Narrow'
  if (moat.total_score >= 40) return 'Weak'
  return 'None'
}

function getRiskLabel(result: ConsensusScore): string {
  const rf = result.investor_scores.find((s) => s.investor === ANTI_MOAT_INVESTOR_NAME)
  if (!rf) return '—'
  if (rf.total_score >= 75) return 'Clean'
  if (rf.total_score >= 55) return 'Watch'
  if (rf.total_score >= 40) return 'Caution'
  return 'Danger'
}

function getRiskColor(label: string): string {
  switch (label) {
    case 'Clean':
      return 'text-green-400'
    case 'Watch':
      return 'text-blue-400'
    case 'Caution':
      return 'text-yellow-400'
    case 'Danger':
      return 'text-red-400'
    default:
      return 'text-gray-500'
  }
}

function getMoatColor(label: string): string {
  switch (label) {
    case 'Wide':
      return 'text-emerald-400'
    case 'Narrow':
      return 'text-blue-400'
    case 'Weak':
      return 'text-amber-400'
    case 'None':
      return 'text-red-400'
    default:
      return 'text-gray-500'
  }
}

export default function PortfolioTable({ results, onViewStock }: PortfolioTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('score')
  const [sortAsc, setSortAsc] = useState(false)

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(key === 'ticker')
    }
  }

  const scores = Array.from(results.values())
  const sorted = [...scores].sort((a, b) => {
    let cmp = 0
    switch (sortKey) {
      case 'score':
        cmp = a.weighted_avg - b.weighted_avg
        break
      case 'ticker':
        cmp = a.ticker.localeCompare(b.ticker)
        break
      case 'agreement':
        cmp = a.agreement_level.localeCompare(b.agreement_level)
        break
      case 'moat': {
        const moatA = a.investor_scores.find((s) => s.investor === MOAT_INVESTOR_NAME)
        const moatB = b.investor_scores.find((s) => s.investor === MOAT_INVESTOR_NAME)
        cmp = (moatA?.total_score ?? 0) - (moatB?.total_score ?? 0)
        break
      }
      case 'risk': {
        const rfA = a.investor_scores.find((s) => s.investor === ANTI_MOAT_INVESTOR_NAME)
        const rfB = b.investor_scores.find((s) => s.investor === ANTI_MOAT_INVESTOR_NAME)
        cmp = (rfA?.total_score ?? 0) - (rfB?.total_score ?? 0)
        break
      }
    }
    return sortAsc ? cmp : -cmp
  })

  const arrow = (key: SortKey) =>
    sortKey === key ? (sortAsc ? ' \u2191' : ' \u2193') : ''

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mb-6">
      <div className="px-5 py-4 border-b border-gray-800">
        <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Portfolio Ranking
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-500">
              <th className="px-4 py-3 text-left font-medium w-10">#</th>
              <th
                className="px-4 py-3 text-left font-medium cursor-pointer hover:text-gray-300"
                onClick={() => handleSort('ticker')}
              >
                Ticker{arrow('ticker')}
              </th>
              <th
                className="px-4 py-3 text-left font-medium cursor-pointer hover:text-gray-300"
                onClick={() => handleSort('score')}
              >
                Score{arrow('score')}
              </th>
              <th className="px-4 py-3 text-left font-medium">Verdict</th>
              <th
                className="px-4 py-3 text-left font-medium cursor-pointer hover:text-gray-300"
                onClick={() => handleSort('agreement')}
              >
                Agreement{arrow('agreement')}
              </th>
              <th
                className="px-4 py-3 text-left font-medium cursor-pointer hover:text-gray-300"
                onClick={() => handleSort('moat')}
              >
                Moat{arrow('moat')}
              </th>
              <th
                className="px-4 py-3 text-left font-medium cursor-pointer hover:text-gray-300"
                onClick={() => handleSort('risk')}
              >
                Risk{arrow('risk')}
              </th>
              <th className="px-4 py-3 text-right font-medium w-16"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((stock, i) => {
              const moatLabel = getMoatLabel(stock)
              const riskLabel = getRiskLabel(stock)
              return (
                <tr
                  key={stock.ticker}
                  className="border-b border-gray-800/50 hover:bg-gray-800/50 transition-colors"
                >
                  <td className="px-4 py-3 text-gray-600">{i + 1}</td>
                  <td className="px-4 py-3 text-gray-100 font-semibold">{stock.ticker}</td>
                  <td className="px-4 py-3">
                    <span
                      className="font-bold"
                      style={{
                        color:
                          stock.weighted_avg >= 75
                            ? '#22c55e'
                            : stock.weighted_avg >= 55
                            ? '#3b82f6'
                            : stock.weighted_avg >= 40
                            ? '#eab308'
                            : '#ef4444',
                      }}
                    >
                      {Math.round(stock.weighted_avg)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full border ${getVerdictBadge(stock.weighted_avg)}`}
                    >
                      {getVerdict(stock.weighted_avg)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full border ${getAgreementBadge(stock.agreement_level)}`}
                    >
                      {stock.agreement_level}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-xs font-medium ${getMoatColor(moatLabel)}`}>
                    {moatLabel}
                  </td>
                  <td className={`px-4 py-3 text-xs font-medium ${getRiskColor(riskLabel)}`}>
                    {riskLabel}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => onViewStock(stock.ticker)}
                      className="text-blue-400 hover:text-blue-300 text-xs font-medium"
                    >
                      View
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
