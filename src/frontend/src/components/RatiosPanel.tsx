import { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { RatioYear, RatiosResponse } from '../types/analysis'
import { fetchRatios } from '../api/client'

interface RatiosPanelProps {
  ticker: string
}

interface SeriesConfig {
  key: keyof RatioYear
  label: string
  color: string
  format: (v: number | null) => string
}

const VALUATION_SERIES: SeriesConfig[] = [
  { key: 'pe', label: 'P/E', color: '#3b82f6', format: (v) => v != null ? v.toFixed(1) + 'x' : '—' },
  { key: 'ps', label: 'P/S', color: '#8b5cf6', format: (v) => v != null ? v.toFixed(1) + 'x' : '—' },
  { key: 'fcf_yield', label: 'FCF Yield', color: '#06b6d4', format: (v) => v != null ? (v * 100).toFixed(1) + '%' : '—' },
]

const PROFITABILITY_SERIES: SeriesConfig[] = [
  { key: 'gross_margin', label: 'Gross Margin', color: '#22c55e', format: (v) => v != null ? (v * 100).toFixed(1) + '%' : '—' },
  { key: 'net_margin', label: 'Net Margin', color: '#f59e0b', format: (v) => v != null ? (v * 100).toFixed(1) + '%' : '—' },
]

const ALL_SERIES = [...VALUATION_SERIES, ...PROFITABILITY_SERIES]

function SkeletonLoader() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4 mb-6 animate-pulse">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-gray-700 rounded" />
        <div className="h-5 w-48 bg-gray-700 rounded" />
      </div>
      <div className="h-64 bg-gray-800 rounded-lg" />
      <div className="space-y-2">
        <div className="h-4 w-full bg-gray-800 rounded" />
        <div className="h-4 w-full bg-gray-800 rounded" />
        <div className="h-4 w-3/4 bg-gray-800 rounded" />
      </div>
    </div>
  )
}

export default function RatiosPanel({ ticker }: RatiosPanelProps) {
  const [data, setData] = useState<RatiosResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [enabled, setEnabled] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    for (const s of ALL_SERIES) init[s.key] = true
    return init
  })

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setData(null)

    fetchRatios(ticker)
      .then((res) => {
        if (!cancelled) {
          setData(res)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load historical ratios')
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [ticker])

  if (loading) return <SkeletonLoader />
  if (error) return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
      <p className="text-gray-500 text-sm">{error}</p>
    </div>
  )
  if (!data || data.years.length === 0) return null

  const toggle = (key: string) =>
    setEnabled((prev) => ({ ...prev, [key]: !prev[key] }))

  // Check which groups have any enabled series
  const hasValuation = VALUATION_SERIES.some((s) => enabled[s.key])
  const hasProfitability = PROFITABILITY_SERIES.some((s) => enabled[s.key])

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4 mb-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">📊</span>
        <div>
          <span className="font-semibold text-gray-100 text-lg">Historical Ratios</span>
          <p className="text-xs text-gray-500 mt-0.5">
            Year-by-year valuation &amp; profitability metrics
          </p>
        </div>
      </div>

      {/* Toggle buttons */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-gray-500 mr-1">Valuation:</span>
          {VALUATION_SERIES.map((s) => (
            <button
              key={s.key}
              onClick={() => toggle(s.key)}
              className={`text-xs px-2.5 py-1 rounded-full border font-medium transition-colors ${
                enabled[s.key]
                  ? 'border-transparent text-white'
                  : 'border-gray-700 text-gray-600'
              }`}
              style={enabled[s.key] ? { backgroundColor: s.color + '33', color: s.color, borderColor: s.color + '66' } : undefined}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-gray-500 mr-1">Profitability:</span>
          {PROFITABILITY_SERIES.map((s) => (
            <button
              key={s.key}
              onClick={() => toggle(s.key)}
              className={`text-xs px-2.5 py-1 rounded-full border font-medium transition-colors ${
                enabled[s.key]
                  ? 'border-transparent text-white'
                  : 'border-gray-700 text-gray-600'
              }`}
              style={enabled[s.key] ? { backgroundColor: s.color + '33', color: s.color, borderColor: s.color + '66' } : undefined}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Charts — side by side when both groups active */}
      <div className={`grid gap-4 ${hasValuation && hasProfitability ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
        {hasValuation && (
          <div>
            <p className="text-xs text-gray-500 mb-2 font-medium">Valuation</p>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.years} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
                  <XAxis dataKey="year" tick={{ fill: '#9ca3af', fontSize: 12 }} stroke="#374151" />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} stroke="#374151" width={48} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    labelStyle={{ color: '#d1d5db' }}
                    itemStyle={{ color: '#d1d5db' }}
                    formatter={(value: number, name: string) => {
                      const cfg = VALUATION_SERIES.find((s) => s.label === name)
                      return cfg ? [cfg.format(value), name] : [value, name]
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {VALUATION_SERIES.filter((s) => enabled[s.key]).map((s) => (
                    <Line
                      key={s.key}
                      type="monotone"
                      dataKey={s.key}
                      name={s.label}
                      stroke={s.color}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {hasProfitability && (
          <div>
            <p className="text-xs text-gray-500 mb-2 font-medium">Profitability</p>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.years} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
                  <XAxis dataKey="year" tick={{ fill: '#9ca3af', fontSize: 12 }} stroke="#374151" />
                  <YAxis
                    tick={{ fill: '#9ca3af', fontSize: 12 }}
                    stroke="#374151"
                    width={48}
                    tickFormatter={(v: number) => (v * 100).toFixed(0) + '%'}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    labelStyle={{ color: '#d1d5db' }}
                    itemStyle={{ color: '#d1d5db' }}
                    formatter={(value: number, name: string) => {
                      const cfg = PROFITABILITY_SERIES.find((s) => s.label === name)
                      return cfg ? [cfg.format(value), name] : [value, name]
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {PROFITABILITY_SERIES.filter((s) => enabled[s.key]).map((s) => (
                    <Line
                      key={s.key}
                      type="monotone"
                      dataKey={s.key}
                      name={s.label}
                      stroke={s.color}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* Compact data table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-gray-400">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-1.5 pr-3 text-gray-500 font-medium">Year</th>
              {ALL_SERIES.map((s) => (
                <th key={s.key} className="text-right py-1.5 px-2 font-medium" style={{ color: s.color }}>
                  {s.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.years.map((row) => (
              <tr key={row.year} className="border-b border-gray-800/50">
                <td className="py-1.5 pr-3 text-gray-300 font-medium">{row.year}</td>
                {ALL_SERIES.map((s) => (
                  <td key={s.key} className="text-right py-1.5 px-2">
                    {s.format(row[s.key] as number | null)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
