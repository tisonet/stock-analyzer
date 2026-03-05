import { useState } from 'react'
import type { ConsensusScore } from '../types/analysis'
import { MOAT_INVESTOR_NAME, ANTI_MOAT_INVESTOR_NAME } from '../types/analysis'
import { analyzeStock } from '../api/client'
import SearchBar from '../components/SearchBar'
import ConsensusView from '../components/ConsensusView'
import InvestorCard from '../components/InvestorCard'
import MoatCard from '../components/MoatCard'
import RedFlagCard from '../components/RedFlagCard'
import ScenarioTab from '../components/ScenarioTab'
import ChatPanel from '../components/ChatPanel'

type AppState = 'idle' | 'loading' | 'success' | 'error'

export default function Analysis() {
  const [state, setState] = useState<AppState>('idle')
  const [result, setResult] = useState<ConsensusScore | null>(null)
  const [ticker, setTicker] = useState<string>('')
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'investors' | 'scenario'>('investors')

  const handleSearch = async (sym: string) => {
    setState('loading')
    setResult(null)
    setTicker(sym.toUpperCase())
    setErrorMsg('')
    try {
      const data = await analyzeStock(sym)
      setResult(data)
      setState('success')
      setActiveTab('investors')
    } catch (err: unknown) {
      let msg = 'Analysis failed. Please check the ticker and try again.'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string }; status?: number } }
        if (axiosErr.response?.status === 404) {
          msg = 'Ticker not found. Please verify the symbol.'
        } else if (axiosErr.response?.data?.detail) {
          msg = axiosErr.response.data.detail
        }
      }
      setErrorMsg(msg)
      setState('error')
    }
  }

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-2xl">📈</span>
            <div>
              <h1 className="text-gray-100 font-bold text-lg leading-tight">
                SuperInvestor
              </h1>
              <p className="text-gray-500 text-xs">Stock Analyzer</p>
            </div>
          </div>
          <div className="flex-1 max-w-md">
            <SearchBar onSearch={handleSearch} loading={state === 'loading'} />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Idle state */}
        {state === 'idle' && (
          <div className="text-center py-24 space-y-4">
            <p className="text-6xl">🧠</p>
            <h2 className="text-2xl font-semibold text-gray-200">
              Evaluate any stock like the legends
            </h2>
            <p className="text-gray-500 max-w-md mx-auto">
              Enter a ticker symbol above to get a comprehensive analysis from 12 legendary
              investors plus a dedicated economic moat assessment and red flag detector.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 max-w-lg mx-auto mt-8 text-left">
              {[
                { icon: '🏦', name: 'Warren Buffett', style: 'Quality moat + fair price' },
                { icon: '🧠', name: 'Charlie Munger', style: 'Simplicity + skin in the game' },
                { icon: '📊', name: 'Benjamin Graham', style: 'Margin of safety + value' },
                { icon: '🔍', name: 'Peter Lynch', style: 'GARP + PEG ratio' },
                { icon: '⚖️', name: 'Ray Dalio', style: 'All-weather + macro' },
                { icon: '🛡️', name: 'Seth Klarman', style: 'Deep value + downside first' },
                { icon: '🎯', name: 'Terry Smith', style: 'Quality compounder + ROCE' },
                { icon: '⚔️', name: 'Carl Icahn', style: 'Activist + undervalued assets' },
                { icon: '💎', name: 'AKO Quality', style: 'Virtuous circle + ROIC' },
                { icon: '🔢', name: 'Dev Kantesaria', style: 'Compounding machines + ROIC' },
                { icon: '🏛️', name: 'Pat Dorsey', style: 'Economic moats + ROIC confirmation' },
                { icon: '🎪', name: 'Bill Ackman', style: '8 commandments + activist value' },
                { icon: '🏰', name: 'Moat Score', style: '9-criteria moat analysis (0–10)' },
                { icon: '🚨', name: 'Red Flag Score', style: '12 forensic distress metrics' },
              ].map((inv) => (
                <div
                  key={inv.name}
                  className="bg-gray-900 border border-gray-800 rounded-lg p-3"
                >
                  <div className="text-xl mb-1">{inv.icon}</div>
                  <div className="text-sm font-medium text-gray-200">{inv.name}</div>
                  <div className="text-xs text-gray-500">{inv.style}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Loading state */}
        {state === 'loading' && (
          <div className="text-center py-24 space-y-4">
            <div className="inline-block w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-300 text-lg">Analyzing…</p>
            <p className="text-gray-500 text-sm">
              Fetching financial data and generating investor insights.
              <br />
              This may take up to 30 seconds.
            </p>
          </div>
        )}

        {/* Error state */}
        {state === 'error' && (
          <div className="text-center py-24 space-y-4">
            <p className="text-4xl">❌</p>
            <p className="text-red-400 text-lg">{errorMsg}</p>
            <button
              onClick={() => setState('idle')}
              className="text-blue-400 hover:text-blue-300 text-sm underline"
            >
              Try another ticker
            </button>
          </div>
        )}

        {/* Success state */}
        {state === 'success' && result && (() => {
          const moatScore = result.investor_scores.find(
            (s) => s.investor === MOAT_INVESTOR_NAME
          )
          const redFlagScore = result.investor_scores.find(
            (s) => s.investor === ANTI_MOAT_INVESTOR_NAME
          )
          const investorScores = result.investor_scores.filter(
            (s) => s.investor !== MOAT_INVESTOR_NAME && s.investor !== ANTI_MOAT_INVESTOR_NAME
          )
          return (
            <div>
              {/* Consensus */}
              <ConsensusView consensus={result} />

              {/* Moat Score panel — analytical, below consensus */}
              {moatScore && <MoatCard score={moatScore} />}

              {/* Red Flag Score panel — analytical, mirrors moat */}
              {redFlagScore && <RedFlagCard score={redFlagScore} />}

              {/* Tabs */}
              <div className="flex gap-1 mb-6">
                <button
                  onClick={() => setActiveTab('investors')}
                  className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
                    activeTab === 'investors'
                      ? 'bg-gray-700 text-gray-100'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Investor Breakdown
                </button>
                <button
                  onClick={() => setActiveTab('scenario')}
                  className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
                    activeTab === 'scenario'
                      ? 'bg-gray-700 text-gray-100'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Scenario Analysis
                </button>
              </div>

              {/* Investor cards (moat excluded — shown separately above) */}
              {activeTab === 'investors' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {investorScores.map((score) => (
                    <InvestorCard key={score.investor} score={score} />
                  ))}
                </div>
              )}

              {/* Scenario tab */}
              {activeTab === 'scenario' && (
                <ScenarioTab investor_scores={investorScores} />
              )}
            </div>
          )
        })()}
      </main>

      <footer className="border-t border-gray-800 mt-16 py-6 text-center text-gray-600 text-xs">
        SuperInvestor Stock Analyzer — Educational purposes only. Not financial advice.
      </footer>

      <ChatPanel ticker={ticker} result={result} />
    </div>
  )
}
