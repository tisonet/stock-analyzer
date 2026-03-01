import type { VerdictType } from '../types/analysis'

type InvestorQuotes = Record<VerdictType, string>

const QUOTES: Record<string, InvestorQuotes> = {
  Buffett: {
    'Strong Buy': 'It\'s far better to buy a wonderful company at a fair price than a fair company at a wonderful price.',
    'Buy': 'Whether we\'re talking about socks or stocks, I like buying quality merchandise when it is marked down.',
    'Hold': 'Our favourite holding period is forever — but only for businesses we truly understand.',
    'Avoid': 'Rule #1: Never lose money. Rule #2: Never forget Rule #1.',
  },
  Munger: {
    'Strong Buy': 'Invert, always invert — I have found a business that passes every test of inversion.',
    'Buy': 'All I want to know is where I\'m going to die, so I\'ll never go there. This one I\'d go to.',
    'Hold': 'Show me the incentive and I\'ll show you the outcome. Watch management carefully.',
    'Avoid': 'It\'s not supposed to be easy. Anyone who finds it easy is stupid.',
  },
  Graham: {
    'Strong Buy': 'The margin of safety is always dependent on the price paid. For this one, it is substantial.',
    'Buy': 'Mr. Market is offering you a reasonable price today. The intelligent investor takes it.',
    'Hold': 'The investor\'s chief problem — and even his worst enemy — is likely to be himself.',
    'Avoid': 'Confronted with a challenge to distill the secret of sound investment into three words, we venture the motto: Margin of Safety.',
  },
  Lynch: {
    'Strong Buy': 'Know what you own, and know why you own it. I own this one — it\'s a perfect ten-bagger candidate.',
    'Buy': 'Behind every stock is a company. Find out what it\'s doing. This one\'s doing the right things.',
    'Hold': 'The person who turns over the most rocks wins. Keep watching this one.',
    'Avoid': 'Never invest in any idea you can\'t illustrate with a crayon. This one needs a lawyer.',
  },
  Dalio: {
    'Strong Buy': 'The biggest mistake investors make is to believe that what happened in the recent past is likely to persist. This one is ready for all seasons.',
    'Buy': 'He who lives by the crystal ball will eat shattered glass. But this company can weather most economic environments.',
    'Hold': 'Diversify across economic environments. This stock performs well in some, poorly in others.',
    'Avoid': 'Pain plus reflection equals progress. This company has pain, but reflection is needed before investing.',
  },
  Klarman: {
    'Strong Buy': 'Value investing is at its core the marriage of a contrarian streak and a calculator. The math works here.',
    'Buy': 'The stock market is filled with individuals who know the price of everything, but the value of nothing. This is one the market has underpriced.',
    'Hold': 'Successful value investing requires a great deal of hard work, unusually strict discipline, and a long-term investment horizon.',
    'Avoid': 'The biggest challenge is maintaining the required discipline when so many market participants are getting rich. But not with this one.',
  },
  'Terry Smith': {
    'Strong Buy': 'Buy good companies, don\'t overpay, do nothing. This one ticks all three boxes — high ROCE, strong cash conversion, and a sensible price.',
    'Buy': 'A high-quality business at a fair price. The ROCE and gross margins tell you this is a genuine compounder worth owning for years.',
    'Hold': 'The business quality is there, but the price demands patience. I\'d rather hold than trade — doing nothing is usually the right answer.',
    'Avoid': 'I\'d rather own nothing than a bad business at any price. Low margins and poor capital returns are permanent problems, not temporary ones.',
  },
  'Icahn': {
    'Strong Buy': 'Good assets, bad management — that\'s my sweet spot. I\'m buying a large stake, I\'m calling the board, and we\'re fixing this. The shareholders will thank me.',
    'Buy': 'The assets are cheap and the cash is real. Management just needs a nudge — or a shove. I\'ve done it before and I\'ll do it here.',
    'Hold': 'There\'s value here but the discount isn\'t wide enough yet. I\'d want a bigger margin before I start making phone calls to the CEO.',
    'Avoid': 'I need two things: cheap assets and something to fix. This has neither. I\'m not in the business of fighting well-run companies at full prices.',
  },
  'AKO Quality': {
    'Strong Buy': 'This is the virtuous circle at its finest — cash generated, reinvested at high returns, generating more cash. The market sees a premium multiple; we see a decade of compounding in plain sight.',
    'Buy': 'Quality at a fair price. Sustained ROIC, real cash conversion, and consistent growth tell us this business has already won in its industry. We hold for the long term.',
    'Hold': 'The quality characteristics are present, but one or more pillars need more consistency. Quality companies are worth waiting for — patience is part of the process.',
    'Avoid': 'The three pillars must all hold — strong cash generation, sustained high ROIC, and attractive reinvestment. One or two is not enough. We will wait for a genuine quality compounder.',
  },
  'Kantesaria': {
    'Strong Buy': 'This is the compounding machine I look for — 20%+ ROIC every year, capital-light, recurring revenue, wide moat. The multiple looks high until you model ten years of compounding at these rates. Then it looks cheap.',
    'Buy': 'A genuine compounder at a fair price. ROIC above 20%, predictable cash flows, and a clear moat. I am comfortable holding this for a decade and letting the compounding do the work.',
    'Hold': 'The business quality is real, but one or two metrics need more runway before I build a full position. Compounders reward patience — I would rather wait for confirmation than overpay for potential.',
    'Avoid': 'Without high and stable ROIC, the compounding thesis collapses. A premium multiple on a mediocre business is the most dangerous trade in investing — the multiple compresses as growth slows, and the damage is permanent.',
  },
}

interface QuotesPanelProps {
  investor: string
  verdict: VerdictType
}

export default function QuotesPanel({ investor, verdict }: QuotesPanelProps) {
  const investorQuotes = QUOTES[investor]
  if (!investorQuotes) return null
  const quote = investorQuotes[verdict]
  return (
    <blockquote className="mt-3 border-l-2 border-gray-600 pl-3">
      <p className="text-gray-400 text-xs italic leading-relaxed">"{quote}"</p>
    </blockquote>
  )
}
