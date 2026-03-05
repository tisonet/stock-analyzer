import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ConsensusScore, ChatMessage } from '../types/analysis'
import { chatWithAnalysis } from '../api/client'

interface Props {
  ticker: string
  result: ConsensusScore | null
}

export default function ChatPanel({ ticker, result }: Props) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, open])

  if (!result) return null

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return

    const userMsg: ChatMessage = { role: 'user', content: question }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)

    try {
      const answer = await chatWithAnalysis(ticker, question, messages)
      setMessages([...nextMessages, { role: 'assistant', content: answer }])
    } catch {
      setMessages([
        ...nextMessages,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 hover:bg-blue-500 text-white rounded-full shadow-lg flex items-center justify-center text-2xl z-50 transition-colors"
          title="Ask about this analysis"
        >
          💬
        </button>
      )}

      {/* Side panel */}
      {open && (
        <div className="fixed top-0 right-0 h-full w-96 max-w-full bg-gray-900 border-l border-gray-700 shadow-2xl flex flex-col z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 flex-shrink-0">
            <div>
              <h2 className="text-gray-100 font-semibold text-sm">Ask about {ticker}</h2>
              <p className="text-gray-500 text-xs">Powered by Claude</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-gray-400 hover:text-gray-200 text-xl leading-none"
              title="Close"
            >
              ×
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {messages.length === 0 && (
              <p className="text-gray-500 text-sm text-center mt-8">
                Ask anything about the {ticker} analysis — scores, rules, investor reasoning, or comparisons.
              </p>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white whitespace-pre-wrap'
                      : 'bg-gray-800 text-gray-200 prose prose-invert prose-sm max-w-none'
                  }`}
                >
                  {msg.role === 'user' ? msg.content : (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 rounded-lg px-3 py-2 text-sm text-gray-400 flex items-center gap-2">
                  <span className="inline-block w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                  Thinking…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-4 py-3 border-t border-gray-700 flex-shrink-0">
            <div className="flex gap-2 items-end">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question… (Enter to send)"
                rows={2}
                className="flex-1 bg-gray-800 text-gray-100 text-sm rounded-lg px-3 py-2 resize-none outline-none border border-gray-700 focus:border-blue-500 placeholder-gray-500"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm px-3 py-2 rounded-lg transition-colors flex-shrink-0"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
