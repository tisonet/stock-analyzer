import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts'

interface ScoreGaugeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
}

function getColor(score: number): string {
  if (score >= 75) return '#22c55e'  // green — Strong Buy
  if (score >= 55) return '#3b82f6'  // blue — Buy
  if (score >= 40) return '#eab308'  // yellow — Hold
  return '#ef4444'                    // red — Avoid
}

const sizeMap = {
  sm: { height: 100, innerRadius: 28, outerRadius: 44, textSize: 'text-lg' },
  md: { height: 140, innerRadius: 40, outerRadius: 60, textSize: 'text-2xl' },
  lg: { height: 200, innerRadius: 60, outerRadius: 88, textSize: 'text-4xl' },
}

export default function ScoreGauge({ score, size = 'md' }: ScoreGaugeProps) {
  const color = getColor(score)
  const { height, innerRadius, outerRadius, textSize } = sizeMap[size]

  const data = [
    { value: score, fill: color },
    { value: 100 - score, fill: '#1f2937' },
  ]

  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          startAngle={220}
          endAngle={-40}
          barSize={12}
          data={data}
        >
          <RadialBar dataKey="value" cornerRadius={6} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div
        className="absolute inset-0 flex items-center justify-center"
        style={{ paddingBottom: '10%' }}
      >
        <span className={`${textSize} font-bold`} style={{ color }}>
          {Math.round(score)}
        </span>
      </div>
    </div>
  )
}
