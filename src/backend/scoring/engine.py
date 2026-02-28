"""
Scoring engine: orchestrates all 6 investor modules and Claude narrative generation.
Claude calls are made concurrently to minimise latency.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import anthropic

from src.backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from src.backend.data.fetcher import FinancialData
from src.backend.investors.base_investor import InvestorScore, ConsensusScore
from src.backend.investors.buffett import BuffettInvestor
from src.backend.investors.munger import MungerInvestor
from src.backend.investors.graham import GrahamInvestor
from src.backend.investors.lynch import LynchInvestor
from src.backend.investors.dalio import DalioInvestor
from src.backend.investors.klarman import KlarmanInvestor
from src.backend.investors.terry_smith import TerrySmithInvestor
from src.backend.investors.icahn import IcahnInvestor
from src.backend.investors.ako_quality import AKOQualityInvestor
from src.backend.scoring.aggregator import build_consensus

logger = logging.getLogger(__name__)

INVESTORS = [
    BuffettInvestor(),
    MungerInvestor(),
    GrahamInvestor(),
    LynchInvestor(),
    DalioInvestor(),
    KlarmanInvestor(),
    TerrySmithInvestor(),
    IcahnInvestor(),
    AKOQualityInvestor(),
]

# Per-investor voice and style guidance for Claude prompts
INVESTOR_VOICES: dict[str, str] = {
    "Buffett": (
        "You are Warren Buffett. Speak in a folksy, plain-spoken Midwestern style. "
        "Use baseball analogies or everyday metaphors. Focus on business economics, "
        "moat durability, and whether you'd want to own this for 20 years."
    ),
    "Munger": (
        "You are Charlie Munger. Be direct, even blunt. Reference mental models, "
        "human psychology, or inversion. Use phrases like 'show me the incentive', "
        "'invert, always invert', or reference latticework of knowledge."
    ),
    "Graham": (
        "You are Benjamin Graham. Speak with academic precision. "
        "Reference margin of safety, Mr. Market, and statistical evidence. "
        "Be conservative and focus on downside protection above all."
    ),
    "Lynch": (
        "You are Peter Lynch. Be enthusiastic and conversational. "
        "Classify the company into one of your six categories. "
        "Explain what an ordinary investor could understand about this business."
    ),
    "Dalio": (
        "You are Ray Dalio. Speak about the economic machine, debt cycles, and "
        "how this company fits across the four economic seasons. "
        "Reference principles and systematic thinking."
    ),
    "Klarman": (
        "You are Seth Klarman. Be highly cautious and emphasise downside risk. "
        "Reference margin of safety as the primary concept. "
        "Express skepticism about market efficiency and overpaying."
    ),
    "Terry Smith": (
        "You are Terry Smith, founder of Fundsmith. Be direct and no-nonsense. "
        "Reference your three rules: buy good companies, don't overpay, do nothing. "
        "Focus on ROCE, gross margins, cash conversion, and whether the business "
        "is truly asset-light. Express contempt for financial engineering and "
        "low-quality businesses masquerading as investments."
    ),
    "Icahn": (
        "You are Carl Icahn, the legendary activist investor. Be combative, blunt, "
        "and laser-focused on shareholder value. Reference your track record of forcing "
        "change at Apple, eBay, Motorola, and others. Ask: is management squandering "
        "shareholder value? Are there assets trading below their worth? Could a buyback, "
        "spin-off, or management change unlock significant value? Express contempt for "
        "entrenched boards and CEOs who don't own their own stock. Remember your motto: "
        "you are a liberator of companies, not a destroyer."
    ),
    "AKO Quality": (
        "You are the AKO Capital investment team, practitioners of quality investing as "
        "described in 'Quality Investing' by Cunningham, Eide & Hargreaves. Speak with a "
        "calm, systematic, long-term European perspective. Reference the three pillars: "
        "strong predictable cash generation, sustainably high ROIC, and attractive "
        "reinvestment opportunities. Identify which of the 12 quality patterns applies "
        "(recurring revenue, toll roads, friendly middlemen, pricing power, brand strength, "
        "innovation dominance, etc.). Check for the three pitfalls: cyclicality, "
        "technological disruption, and dependency. Emphasise that the best margin of "
        "safety comes from the depth of competitive advantage, not a low entry price."
    ),
}


def _format_metrics(data: FinancialData, score: InvestorScore) -> str:
    """Build a compact key-metrics string for the Claude prompt."""
    parts = []
    if pe := data.pe_ratio:
        parts.append(f"P/E={pe:.1f}x")
    if pb := data.pb_ratio:
        parts.append(f"P/B={pb:.1f}x")
    if de := data.debt_to_equity:
        if de > 10:
            de /= 100
        parts.append(f"D/E={de:.2f}")
    roics = data.roic_series
    if roics:
        import statistics
        parts.append(f"ROIC(avg)={statistics.mean(roics)*100:.1f}%")
    fcf = data.free_cash_flow_series
    if fcf:
        parts.append(f"FCF(latest)=${fcf[-1]/1e9:.1f}B")
    if mc := data.market_cap:
        parts.append(f"MarketCap=${mc/1e9:.0f}B")
    return ", ".join(parts) if parts else "metrics unavailable"


def _call_claude_sync(prompt: str) -> str:
    """Make a synchronous Claude API call."""
    if not ANTHROPIC_API_KEY:
        return "Claude API key not configured — narrative unavailable."
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Claude API call failed: {e}")
        return f"Narrative generation unavailable ({type(e).__name__})."


async def _generate_insight_async(
    investor_score: InvestorScore, data: FinancialData
) -> str:
    """Generate a 2-sentence investor-voice insight using Claude."""
    voice = INVESTOR_VOICES.get(investor_score.investor, "You are a legendary investor.")
    metrics = _format_metrics(data, investor_score)
    passed_names = ", ".join(r.name for r in investor_score.rules_passed[:4]) or "none"
    failed_names = ", ".join(r.name for r in investor_score.rules_failed[:4]) or "none"

    prompt = (
        f"{voice}\n\n"
        f"You are evaluating {data.ticker} ({data.company_name}).\n"
        f"The company scored {investor_score.total_score:.0f}/100 on your investment criteria.\n"
        f"Key metrics: {metrics}\n"
        f"Criteria passed: {passed_names}\n"
        f"Criteria failed: {failed_names}\n\n"
        f"In exactly 2 sentences, give your verdict in your own characteristic voice. "
        f"Be specific about numbers. Do not use the word 'overall'. "
        f"Write plain prose only — no Markdown, no headers, no bullet points."
    )
    return await asyncio.to_thread(_call_claude_sync, prompt)


async def _generate_consensus_async(
    ticker: str,
    company_name: str,
    investor_scores: list[InvestorScore],
    weighted_avg: float,
    agreement_level: str,
) -> str:
    """Generate a consensus narrative paragraph using Claude."""
    score_summary = ", ".join(
        f"{s.investor}: {s.total_score:.0f}/100 ({s.verdict})"
        for s in investor_scores
    )
    prompt = (
        f"Nine legendary investors evaluated {ticker} ({company_name}).\n"
        f"Their verdicts: {score_summary}\n"
        f"Consensus score: {weighted_avg:.0f}/100 ({agreement_level})\n\n"
        f"Write exactly one paragraph (3-4 sentences) summarising where the investors agree "
        f"and disagree, and what it means for a long-term investor considering this stock. "
        f"Be specific, direct, and mention any notable divergences. "
        f"Write plain prose only — no Markdown, no headers, no bullet points."
    )
    if not ANTHROPIC_API_KEY:
        return "Claude API key not configured — consensus narrative unavailable."
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Consensus Claude call failed: {e}")
        return f"Consensus narrative unavailable ({type(e).__name__})."


async def analyze_async(data: FinancialData) -> ConsensusScore:
    """
    Run all 6 investor scorers, generate Claude insights concurrently,
    then build and return the ConsensusScore.
    """
    logger.info(f"Scoring {data.ticker} across {len(INVESTORS)} investors")

    # Step 1: run all scoring modules (CPU-bound, thread pool)
    investor_scores: list[InvestorScore] = []
    for inv in INVESTORS:
        try:
            s = await asyncio.to_thread(inv.score, data)
            investor_scores.append(s)
            logger.debug(f"{inv.name}: {s.total_score:.1f}/100 ({s.verdict})")
        except Exception as e:
            logger.error(f"Scoring failed for {inv.name}: {e}", exc_info=True)

    # Step 2: generate Claude insights concurrently for all investors
    insight_tasks = [
        _generate_insight_async(s, data) for s in investor_scores
    ]
    insights = await asyncio.gather(*insight_tasks, return_exceptions=True)
    for score, insight in zip(investor_scores, insights):
        if isinstance(insight, Exception):
            score.key_insight = f"Insight generation failed: {insight}"
        else:
            score.key_insight = insight

    # Step 3: aggregate
    consensus = build_consensus(data.ticker, investor_scores)

    # Step 4: generate consensus narrative
    consensus.overall_narrative = await _generate_consensus_async(
        data.ticker,
        data.company_name,
        investor_scores,
        consensus.weighted_avg,
        consensus.agreement_level,
    )

    return consensus
