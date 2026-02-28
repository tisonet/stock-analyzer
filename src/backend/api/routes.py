"""
FastAPI application with analysis endpoints.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
