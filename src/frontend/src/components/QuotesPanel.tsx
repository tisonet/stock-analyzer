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
  'Dorsey': {
    'Strong Buy': 'The moat is wide, ROIC confirms it, and the reinvestment runway is long. This is exactly the kind of business I built my framework to identify — durable competitive advantage at a price that still rewards patience.',
    'Buy': 'The economic moat is real — I can see it in the ROIC history and the competitive dynamics. The price is reasonable enough to earn a satisfactory return as the moat compounds over time.',
    'Hold': 'There are signs of a moat, but the financial evidence is not yet conclusive. I need to see more consistency in ROIC before committing capital. Moats are easier to lose than to build.',
    'Avoid': 'No moat, no investment. Without a durable competitive advantage confirmed by sustained excess returns, this is just another business competing on price — and that is a race to the bottom.',
  },
  'Ackman': {
    'Strong Buy': 'This passes all eight commandments. Simple, predictable, free-cash-flow generative, dominant position, high barriers, high returns on capital, limited extrinsic risk, strong balance sheet. I would take a large, concentrated position here.',
    'Buy': 'Most of the commandments are met. The business is high quality and the price is attractive. I would build a meaningful position and engage with management if needed to unlock additional value.',
    'Hold': 'The business has quality characteristics but fails key commandments. I would want to see improvements in specific areas before committing capital. Perhaps an activist approach could unlock the potential here.',
    'Avoid': 'Too many commandments fail. After Valeant, I carved these criteria in stone for a reason. The best protection against permanent capital loss is avoiding businesses that don\'t meet the bar.',
  },
  'Pabrai': {
    'Strong Buy': 'Heads I win big, tails I don\'t lose much. This is a classic Dhandho bet — low risk, high uncertainty, and the market is giving it away because it confuses the two. Few bets, big bets, infrequent bets.',
    'Buy': 'The downside is limited and the upside is substantial. Simple business, strong cash flows, reasonable leverage. This is the kind of asymmetric bet the Dhandho framework was built for.',
    'Hold': 'The business is decent but the margin of safety is not wide enough for my taste. I need a bigger discount before I make it one of my few, concentrated bets.',
    'Avoid': 'Too much leverage, too little free cash flow, too much complexity. The Dhandho philosophy demands limited downside — and this one has too many ways to lose.',
  },
  'Druckenmiller': {
    'Strong Buy': 'Earnings are accelerating, the momentum is real, and I can see where this business will be in 18 months. When conviction is high, you go for the jugular. This is that moment.',
    'Buy': 'The rate of change is improving — revenue accelerating, margins expanding, earnings beats ahead. The market hasn\'t fully priced in where this business is headed.',
    'Hold': 'The fundamentals are stable but I don\'t see acceleration. I need to see the rate of change improving before I commit capital. Flat earnings don\'t excite me.',
    'Avoid': 'Decelerating earnings, deteriorating momentum, and no catalyst on the horizon. I preserve capital when conviction is low — there is always a better opportunity elsewhere.',
  },
  'Damodaran': {
    'Strong Buy': 'The ROIC-WACC spread is wide and persistent, growth is creating real value, and the price implies a narrative far less optimistic than the numbers support. The valuation gap is substantial.',
    'Buy': 'Excess returns are real — ROIC meaningfully exceeds cost of capital. Growth is value-accretive at these returns. The current price offers a reasonable margin relative to intrinsic value.',
    'Hold': 'The business creates some value but the ROIC-WACC spread is thin. Growth at these returns barely moves the needle. The price is roughly fair — neither a bargain nor a trap.',
    'Avoid': 'ROIC below cost of capital means growth destroys value. Every dollar reinvested makes shareholders poorer. The market is pricing in a narrative the numbers simply do not support.',
  },
  'Fisher': {
    'Strong Buy': 'This company has everything I look for — sizable sales growth, outstanding R&D commitment, improving margins, and management with a long-range outlook. If the job has been correctly done, the time to sell is almost never.',
    'Buy': 'The growth story is real — revenue is compounding, R&D investment is building future products, and margins are holding. This is the kind of company worth paying a premium for and holding for years.',
    'Hold': 'Some growth characteristics are present but the full picture is incomplete. I would want to see stronger R&D commitment or more consistent revenue growth before building a position through my scuttlebutt method.',
    'Avoid': 'Without sizable sales growth and a commitment to future products through R&D, this fails my 15-point checklist. Outstanding companies drive their own growth — this one is not doing that.',
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
