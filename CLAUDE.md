# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install all dependencies
make install

# Backend (from project root)
make backend
# or: python3 -m uvicorn src.backend.api.routes:app --reload --port 8000

# Frontend
make frontend
# or: cd src/frontend && npm run dev

# Run both concurrently
make dev

# All tests
make test
# or: python3 -m pytest tests/ -v

# Single test file
python3 -m pytest tests/test_buffett.py -v

# Single test by name
python3 -m pytest tests/test_buffett.py -v -k "test_high_quality"

# Cache management
make cache-clear TICKER=AAPL   # clear one ticker
make cache-clear               # clear all
make cache-list                # list cached tickers
```

## Environment

Requires `.env` with:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Without `ANTHROPIC_API_KEY`, scoring still works but Claude narratives return placeholder text. Other configurable env vars: `CACHE_TTL_HOURS` (default 24), `CACHE_DB_PATH` (default `cache.db`), `CLAUDE_MODEL` (default `claude-haiku-4-5`).

## Architecture

### Request flow

```
POST /api/analyze/{ticker}
  → cache.get()                          # SQLite, 24h TTL, keyed TICKER_YYYY-MM-DD
  → fetcher.fetch(ticker)                # yfinance → FinancialData dataclass
  → engine.analyze_async(data)
      → investor.score(data)             # 14 modules run sequentially in thread pool
      → asyncio.gather(claude insights)  # all investor insights fired concurrently
      → aggregator.build_consensus()     # weighted average + agreement level
      → claude consensus narrative       # single concurrent call
  → cache.set()
  → return ConsensusScore.to_dict()
```

### Key files

| File | Purpose |
|---|---|
| `src/backend/api/routes.py` | FastAPI app, 4 endpoints |
| `src/backend/data/fetcher.py` | `fetch()` → `FinancialData` dataclass with computed properties |
| `src/backend/data/cache.py` | aiosqlite async cache |
| `src/backend/investors/base_investor.py` | `Rule`, `InvestorScore`, `ConsensusScore`, `BaseInvestor` |
| `src/backend/scoring/engine.py` | Async orchestrator; `INVESTORS` list; `INVESTOR_VOICES` prompts |
| `src/backend/scoring/aggregator.py` | `WEIGHTS` dict; `build_consensus()` |
| `src/backend/config.py` | All constants and env vars |
| `tests/conftest.py` | Shared pytest fixtures (`high_quality_data`, `low_quality_data`, `net_net_data`, `icahn_target_data`, `empty_data`) |

### Investor modules

14 modules in `src/backend/investors/`:
- **Weight 1.0 (in consensus):** Buffett, Munger, Graham, Lynch, Klarman, Terry Smith, AKO Quality, Kantesaria, Dorsey, Ackman
- **Weight 0.0 (analytical only):** Dalio, Icahn, Moat Score (`moat.py`), Red Flag Score (`anti_moat.py`)

### Adding a new investor module

1. Create `src/backend/investors/<name>.py` extending `BaseInvestor`
2. Implement `name` property and `score(data: FinancialData) -> InvestorScore`
3. Use `self._make_rule()` to build each `Rule`, `self._build_result()` to produce `InvestorScore`
4. Register in `engine.py` (`INVESTORS` list + `INVESTOR_VOICES` dict)
5. Set weight in `aggregator.py` (`WEIGHTS` dict)
6. Add tests in `tests/test_<name>.py` using fixtures from `conftest.py`

## Data model patterns

**`FinancialData`** wraps raw yfinance DataFrames. Key access patterns:
- `_latest(df, *keys)` → most recent non-null value
- `_series(df, *keys)` → list oldest→newest (yfinance columns are newest→oldest; `_series` reverses automatically)
- All `*_series` properties return `list[float]`; all point-in-time values return `Optional[float]`

**`FinancialData.info`** is the yfinance `.info` dict — use for `pe_ratio`, `pb_ratio`, `market_cap`, `peg_ratio`, etc.

**ROIC formula**: `NOPAT / Average IC` where `NOPAT = OperatingIncome × (1 − per-year tax rate)` and `Average IC = (IC_beginning + IC_ending) / 2`, `IC = Equity + max(0, TotalDebt − Cash)` — cash deduction is capped at total debt to avoid inflated ROIC for net-cash companies (e.g. ASML). Per-year effective tax rates are used where available, falling back to the most recent rate or 25% default.

## Python compatibility

All backend files must start with `from __future__ import annotations` for Python 3.9 compatibility (PEP 563 postponed evaluation of annotations).

## Tests

Tests use `pytest-asyncio` with `asyncio_mode = auto`. Fixtures in `conftest.py` provide realistic synthetic `FinancialData` objects — no yfinance calls in unit tests. Every investor module should test both a "strong" case (high score expected) and a "weak" case (low score expected), plus crash safety with `empty_data`.
