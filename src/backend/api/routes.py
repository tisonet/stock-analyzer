"""
FastAPI application with analysis endpoints.
"""
from __future__ import annotations

import asyncio
import logging

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from src.backend.data import cache, fetcher
from src.backend.scoring import engine

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SuperInvestor Stock Analyzer",
    description="Evaluate stocks through the lens of legendary investors",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


def _build_analysis_context(cached: dict) -> str:
    lines = [
        f"Ticker: {cached['ticker']}",
        f"Consensus Score: {cached['weighted_avg']:.1f}/100 ({cached['agreement_level']})",
        f"Overall Narrative: {cached['overall_narrative']}",
        "\n## Individual Investor Assessments:",
    ]
    for s in cached["investor_scores"]:
        lines.append(f"\n{s['investor']}: {s['total_score']:.0f}/100 ({s['verdict']})")
        lines.append(f"Insight: {s['key_insight']}")
        if s["red_flags"]:
            lines.append(f"Red Flags: {', '.join(s['red_flags'])}")
        passed = [r["name"] for r in s["rules_passed"]]
        failed = [r["name"] for r in s["rules_failed"]]
        if passed:
            lines.append(f"Passed: {', '.join(passed)}")
        if failed:
            lines.append(f"Failed: {', '.join(failed)}")
        for r in s["rules_passed"] + s["rules_failed"]:
            if r.get("explanation"):
                lines.append(f"  [{r['name']}] {r['explanation']} (value={r['value']}, threshold={r['threshold']})")
    return "\n".join(lines)


def _call_claude_chat_sync(system_prompt: str, messages: list[dict]) -> str:
    if not ANTHROPIC_API_KEY:
        return "Claude API key not configured."
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
        )
        return msg.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Chat Claude call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {type(e).__name__}")


@app.on_event("startup")
async def startup_event() -> None:
    await cache.init_db()
    logger.info("SuperInvestor API started")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/analyze/{ticker}")
async def analyze(ticker: str) -> dict:
    """
    Run full investor analysis for the given ticker.
    Results are cached for 24 hours (keyed by ticker + date).
    """
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    # Check cache first
    cached = await cache.get(ticker)
    if cached:
        return cached

    # Fetch financial data (synchronous yfinance → thread pool)
    try:
        data = await asyncio.to_thread(fetcher.fetch, ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Data fetch failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to fetch market data: {e}")

    # Run analysis with Claude narrative generation
    try:
        consensus = await engine.analyze_async(data)
    except Exception as e:
        logger.error(f"Analysis failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {e}")

    result = consensus.to_dict()
    await cache.set(ticker, result)
    return result


@app.post("/api/chat/{ticker}")
async def chat(ticker: str, body: ChatRequest) -> dict:
    """Answer questions about a cached stock analysis using Claude."""
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")
    cached = await cache.get(ticker)
    if not cached:
        raise HTTPException(status_code=404, detail=f"No cached analysis for {ticker}. Run analysis first.")
    context = _build_analysis_context(cached)
    system_prompt = (
        f"You are an expert investment analyst assistant helping a user understand "
        f"a stock analysis for {ticker}. The analysis was performed using 14 legendary "
        f"investor frameworks (Buffett, Munger, Graham, Lynch, Klarman, Terry Smith, "
        f"AKO Quality, Kantesaria, Dorsey, Ackman, Dalio, Icahn, plus Moat and Red Flag scores). "
        f"Answer questions specifically and concisely, citing investor names, scores, rules, and values. "
        f"Do not give financial advice — remind the user results are educational only.\n\n"
        f"ANALYSIS:\n{context}"
    )
    messages = list(body.history) + [{"role": "user", "content": body.question}]
    answer = await asyncio.to_thread(_call_claude_chat_sync, system_prompt, messages)
    return {"answer": answer}


@app.get("/api/cache/{ticker}")
async def cache_status(ticker: str) -> dict:
    """Check whether analysis results are cached for a ticker."""
    ticker = ticker.upper().strip()
    cached = await cache.get(ticker)
    return {"ticker": ticker, "cached": cached is not None}


@app.delete("/api/cache/{ticker}")
async def clear_cache(ticker: str) -> dict:
    """Clear cached results for a ticker (force refresh on next request)."""
    ticker = ticker.upper().strip()
    await cache.clear(ticker)
    return {"ticker": ticker, "cleared": True}


# Serve built frontend — must be mounted last so API routes take precedence
import os
if os.path.isdir("src/frontend/dist"):
    app.mount("/", StaticFiles(directory="src/frontend/dist", html=True), name="static")
