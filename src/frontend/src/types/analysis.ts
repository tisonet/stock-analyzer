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

export interface PortfolioStock {
  ticker: string
  result: ConsensusScore | null
  status: 'pending' | 'loading' | 'success' | 'error'
  error?: string
}

export interface RatioYear {
  year: number
  pe: number | null
  ps: number | null
  fcf_yield: number | null
  gross_margin: number | null
  net_margin: number | null
  fcf_per_share: number | null
  eps: number | null
  revenue_per_share: number | null
}

export interface RatiosResponse {
  ticker: string
  years: RatioYear[]
}
