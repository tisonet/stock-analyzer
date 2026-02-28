import { useState, type FormEvent } from 'react'

interface SearchBarProps {
  onSearch: (ticker: string) => void
  loading: boolean
}

const POPULAR = ['AAPL', 'MSFT', 'GOOGL', 'BRK.B', 'JPM', 'NVDA', 'META', 'AMZN']

export default function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const ticker = value.trim().toUpperCase()
    if (ticker) onSearch(ticker)
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          placeholder="Enter ticker symbol (e.g. AAPL)"
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 text-lg font-mono"
          disabled={loading}
          autoFocus
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-6 py-3 rounded-lg transition-colors"
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </form>
      <div className="flex flex-wrap gap-2 mt-3 justify-center">
        {POPULAR.map((t) => (
          <button
            key={t}
            onClick={() => { setValue(t); onSearch(t) }}
            disabled={loading}
            className="text-xs text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded-full border border-gray-700 transition-colors font-mono disabled:opacity-40"
          >
            {t}
          </button>
        ))}
      </div>
    </div>
  )
}
