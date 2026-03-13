import { useState } from 'react'
import type { ConsensusScore } from '../types/analysis'

interface PortfolioHeatmapProps {
  results: Map<string, ConsensusScore>
}

// Only show weighted investors (exclude Dalio, Icahn, Moat Score, Red Flag Score)
const HEATMAP_INVESTORS = [
  'Buffett',
  'Munger',
  'Graham',
  'Lynch',
  'Klarman',
  'Terry Smith',
  'AKO Quality',
  'Kantesaria',
  'Dorsey',
  'Ackman',
  'Pabrai',
  'Druckenmiller',
  'Damodaran',
  'Fisher',
]

function getCellBg(score: number): string {
  if (score >= 75) return 'bg-green-500/30'
  if (score >= 55) return 'bg-blue-500/30'
  if (score >= 40) return 'bg-yellow-500/20'
  return 'bg-red-500/25'
}

function getCellText(score: number): string {
  if (score >= 75) return 'text-green-300'
  if (score >= 55) return 'text-blue-300'
  if (score >= 40) return 'text-yellow-300'
  return 'text-red-300'
}

function getVerdict(score: number): string {
  if (score >= 75) return 'Strong Buy'
  if (score >= 55) return 'Buy'
  if (score >= 40) return 'Hold'
  return 'Avoid'
}

// Short labels for column headers
const SHORT_NAMES: Record<string, string> = {
  Buffett: 'Buff',
  Munger: 'Mung',
  Graham: 'Grah',
  Lynch: 'Lync',
  Klarman: 'Klar',
  'Terry Smith': 'TSmi',
  'AKO Quality': 'AKO',
  Kantesaria: 'Kant',
  Dorsey: 'Dors',
  Ackman: 'Ackm',
  Pabrai: 'Pabr',
  Druckenmiller: 'Druc',
  Damodaran: 'Damo',
  Fisher: 'Fish',
}

export default function PortfolioHeatmap({ results }: PortfolioHeatmapProps) {
  const [tooltip, setTooltip] = useState<string | null>(null)

  const stocks = Array.from(results.values()).sort((a, b) => b.weighted_avg - a.weighted_avg)

  if (stocks.length === 0) return null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-800">
        <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Investor Heatmap
        </h3>
        <p className="text-gray-500 text-xs mt-1">Score by investor for each stock. Hover for details.</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="px-4 py-3 text-left text-gray-500 font-medium sticky left-0 bg-gray-900 z-10 min-w-[80px]">
                Ticker
              </th>
              {HEATMAP_INVESTORS.map((inv) => (
                <th
                  key={inv}
                  className="px-2 py-3 text-center text-gray-500 font-medium min-w-[50px]"
                  title={inv}
                >
                  {SHORT_NAMES[inv] || inv}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => (
              <tr key={stock.ticker} className="border-b border-gray-800/50">
                <td className="px-4 py-2 text-gray-200 font-semibold sticky left-0 bg-gray-900 z-10">
                  {stock.ticker}
                </td>
                {HEATMAP_INVESTORS.map((inv) => {
                  const investorScore = stock.investor_scores.find((s) => s.investor === inv)
                  const score = investorScore?.total_score ?? 0
                  const tooltipKey = `${stock.ticker}-${inv}`
                  return (
                    <td
                      key={inv}
                      className={`px-2 py-2 text-center font-bold ${getCellBg(score)} ${getCellText(score)} relative cursor-default`}
                      onMouseEnter={() => setTooltip(tooltipKey)}
                      onMouseLeave={() => setTooltip(null)}
                    >
                      {Math.round(score)}
                      {tooltip === tooltipKey && (
                        <div className="absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg shadow-xl whitespace-nowrap text-xs text-gray-200 font-normal">
                          {inv} scored {stock.ticker} {Math.round(score)}/100 ({getVerdict(score)})
                        </div>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
