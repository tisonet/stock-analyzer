import axios from 'axios'
import type { ConsensusScore, ChatMessage, RatiosResponse } from '../types/analysis'

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000, // 2 minutes — analysis can be slow (yfinance + Claude)
})

export async function analyzeStock(ticker: string): Promise<ConsensusScore> {
  const response = await api.post<ConsensusScore>(`/analyze/${ticker.toUpperCase()}`)
  return response.data
}

export async function chatWithAnalysis(
  ticker: string,
  question: string,
  history: ChatMessage[]
): Promise<string> {
  const res = await api.post<{ answer: string }>(`/chat/${ticker}`, { question, history })
  return res.data.answer
}

export async function analyzePortfolio(
  tickers: string[],
  onProgress: (ticker: string, result: ConsensusScore | null, error?: string) => void
): Promise<void> {
  const promises = tickers.map(async (t) => {
    try {
      const result = await analyzeStock(t)
      onProgress(t, result)
    } catch (err: unknown) {
      let msg = 'Analysis failed'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string }; status?: number } }
        if (axiosErr.response?.status === 404) msg = 'Ticker not found'
        else if (axiosErr.response?.data?.detail) msg = axiosErr.response.data.detail
      }
      onProgress(t, null, msg)
    }
  })
  await Promise.allSettled(promises)
}

export async function fetchRatios(ticker: string): Promise<RatiosResponse> {
  const response = await api.get<RatiosResponse>(`/ratios/${ticker.toUpperCase()}`)
  return response.data
}

export async function checkHealth(): Promise<boolean> {
  try {
    await api.get('/health')
    return true
  } catch {
    return false
  }
}
