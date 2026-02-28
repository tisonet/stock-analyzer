export type VerdictType = 'Strong Buy' | 'Buy' | 'Hold' | 'Avoid'

export interface Rule {
  name: string
  passed: boolean
  value: number | null
  threshold: number
  points_awarded: number
  points_possible: number
  description: string
  source: string
}

export interface InvestorScore {
  investor: string
  total_score: number
  verdict: VerdictType
  rules_passed: Rule[]
  rules_failed: Rule[]
  key_insight: string
  red_flags: string[]
}

export interface ConsensusScore {
  ticker: string
  weighted_avg: number
  agreement_level: string
  investor_scores: InvestorScore[]
  overall_narrative: string
}
