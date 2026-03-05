export type VerdictType = 'Strong Buy' | 'Buy' | 'Hold' | 'Avoid'

/** Constant used to identify and separate the moat score from investor scores. */
export const MOAT_INVESTOR_NAME = 'Moat Score' as const

/** Verdict labels returned by MoatInvestor (maps to 75/55/40 score thresholds). */
export type MoatStrengthLabel = 'Wide Moat' | 'Narrow Moat' | 'Weak Moat' | 'No Moat'

/** Constant used to identify and separate the red flag score from investor scores. */
export const ANTI_MOAT_INVESTOR_NAME = 'Red Flag Score' as const

/** Danger severity labels returned by AntiMoatInvestor (higher score = safer company). */
export type DangerLabel = 'Clean' | 'Watch' | 'Caution' | 'Danger' | 'Critical'

export interface Rule {
  name: string
  passed: boolean
  value: number | null
  threshold: number
  points_awarded: number
  points_possible: number
  description: string
  source: string
  explanation: string   // plain-language: what this metric measures and why it matters
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

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ConsensusScore {
  ticker: string
  weighted_avg: number
  agreement_level: string
  investor_scores: InvestorScore[]
  overall_narrative: string
}
