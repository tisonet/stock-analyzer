# SuperInvestor Stock Analyzer

A full-stack application that evaluates any publicly traded stock through the lens of 11 legendary investors, generates an economic moat score, runs a forensic red-flag analysis, and produces a weighted consensus verdict — all enriched with AI-generated narrative from Claude.

---

## How It Works

1. Enter a ticker symbol (e.g. `AAPL`, `ASML`, `NVDA`)
2. The backend fetches 10 years of financial data from Yahoo Finance
3. 13 scoring modules run in parallel, each applying their investor's criteria
4. Claude generates a personalised 2-sentence insight in each investor's voice
5. A weighted consensus score and narrative paragraph are produced
6. Results are cached for 24 hours per ticker

---

## Investors & Modules

| Investor | Style | Weight |
|---|---|---|
| Warren Buffett | Quality moat + DCF intrinsic value | 1.0 |
| Charlie Munger | Simplicity + skin in the game | 1.0 |
| Benjamin Graham | Margin of safety + statistical value | 1.0 |
| Peter Lynch | GARP + PEG ratio + business classification | 1.0 |
| Seth Klarman | Deep value + downside-first | 1.0 |
| Terry Smith | Quality compounder + ROCE + asset-light | 1.0 |
| AKO Quality | Virtuous circle + 12 quality patterns | 1.0 |
| Dev Kantesaria | Compounding machines + ROIC > 20% | 1.0 |
| Pat Dorsey | Economic moats + ROIC fingerprint | 1.0 |
| Ray Dalio | All-weather macro + debt cycles | 0.0 |
| Carl Icahn | Activist + undervalued assets | 0.0 |
| **Moat Score** | 9-criteria moat assessment (analytical) | 0.0 |
| **Red Flag Score** | 12 forensic distress metrics (analytical) | 0.0 |

Dalio and Icahn are macro/activist-focused and excluded from the consensus buy/sell score. Moat Score and Red Flag Score are analytical-only panels displayed separately.

### Verdict thresholds

| Score | Verdict |
|---|---|
| ≥ 75 | Strong Buy |
| ≥ 55 | Buy |
| ≥ 40 | Hold |
| < 40 | Avoid |

### Agreement levels (standard deviation of investor scores)

| Std Dev | Level |
|---|---|
| < 12 | High Conviction |
| < 22 | Mixed |
| ≥ 22 | Divided |

---

## Tech Stack

**Backend**
- Python 3.9 + FastAPI + Uvicorn
- yfinance 1.2 (curl_cffi TLS — no 429 rate-limit errors)
- Anthropic SDK (`claude-haiku-4-5`) for narrative generation
- aiosqlite — SQLite cache with 24 h TTL
- pandas, numpy

**Frontend**
- React 18 + TypeScript + Vite
- Tailwind CSS 3
- Recharts 2
- axios

---

## Project Structure

```
stock-analyzer/
├── src/
│   ├── backend/
│   │   ├── api/
│   │   │   └── routes.py          # FastAPI app + 4 endpoints
│   │   ├── data/
│   │   │   ├── fetcher.py         # yfinance → FinancialData dataclass
│   │   │   └── cache.py           # SQLite async cache
│   │   ├── investors/
│   │   │   ├── base_investor.py   # Rule, InvestorScore, ConsensusScore
│   │   │   ├── buffett.py
│   │   │   ├── munger.py
│   │   │   ├── graham.py
│   │   │   ├── lynch.py
│   │   │   ├── dalio.py
│   │   │   ├── klarman.py
│   │   │   ├── terry_smith.py
│   │   │   ├── icahn.py
│   │   │   ├── ako_quality.py
│   │   │   ├── kantesaria.py
│   │   │   ├── dorsey.py
│   │   │   ├── moat.py            # Moat Score (9 criteria)
│   │   │   └── anti_moat.py      # Red Flag Score (12 forensic criteria)
│   │   ├── scoring/
│   │   │   ├── engine.py          # Async orchestrator + Claude calls
│   │   │   └── aggregator.py      # Weighted consensus builder
│   │   └── config.py
│   └── frontend/
│       └── src/
│           ├── pages/
│           │   └── Analysis.tsx   # Main page state machine
│           ├── components/
│           │   ├── ConsensusView.tsx
│           │   ├── InvestorCard.tsx
│           │   ├── MoatCard.tsx
│           │   ├── RedFlagCard.tsx
│           │   ├── ScoreGauge.tsx
│           │   ├── RuleBreakdown.tsx
│           │   ├── ScenarioTab.tsx
│           │   └── SearchBar.tsx
│           ├── api/client.ts
│           └── types/analysis.ts
└── tests/                         # 106 unit tests
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/) (optional — omitting it disables AI narratives but scoring still works)

### 1. Clone & configure

```bash
git clone <repo-url>
cd stock-analyzer
cp .env.example .env          # then add your key:
# ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the backend

```bash
python3 -m uvicorn src.backend.api.routes:app --reload --port 8000
```

### 4. Install & start the frontend

```bash
cd src/frontend
npm install
npm run dev -- --host
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze/{ticker}` | Run full analysis (returns cached result if available) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/cache/{ticker}` | Check cache status for a ticker |
| `DELETE` | `/api/cache/{ticker}` | Invalidate cached result |

### Example

```bash
curl -X POST http://localhost:8000/api/analyze/AAPL
```

Response shape (abbreviated):

```json
{
  "ticker": "AAPL",
  "weighted_avg": 52.3,
  "agreement_level": "Mixed",
  "overall_narrative": "...",
  "investor_scores": [
    {
      "investor": "Buffett",
      "total_score": 50,
      "verdict": "Hold",
      "key_insight": "...",
      "rules_passed": [...],
      "rules_failed": [...]
    }
  ]
}
```

---

## Running Tests

```bash
python3 -m pytest tests/ -v
```

106 tests covering all investor modules, the scoring engine, aggregator, and data fetcher.

---

## Key Design Decisions

**ROIC formula** — `NOPAT / (Equity + max(0, TotalDebt − Cash))`.
Cash deduction is capped at total debt so net-cash companies (Cash > Debt, e.g. ASML) don't produce artificially small invested-capital and inflated ROIC. For debt-financed companies the formula is identical to the standard GuruFocus definition.

**Concurrent Claude calls** — `asyncio.gather()` fires all investor insight requests and the consensus narrative in parallel, keeping total latency close to one round-trip rather than N+1.

**Analytical-only modules** — Moat Score and Red Flag Score are weighted 0 in the consensus but displayed as dedicated panels. This keeps the buy/sell signal clean while surfacing qualitative intelligence.

**24 h SQLite cache** — Keyed by `TICKER_YYYY-MM-DD`. Avoids repeated Yahoo Finance fetches and Claude API costs for the same ticker on the same day.
