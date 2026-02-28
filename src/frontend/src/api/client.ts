import axios from 'axios'
import type { ConsensusScore } from '../types/analysis'

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000, // 2 minutes — analysis can be slow (yfinance + Claude)
})

export async function analyzeStock(ticker: string): Promise<ConsensusScore> {
  const response = await api.post<ConsensusScore>(`/analyze/${ticker.toUpperCase()}`)
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
