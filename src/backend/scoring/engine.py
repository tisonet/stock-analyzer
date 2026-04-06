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
from src.backend.investors.lynch import LynchInvestor
from src.backend.investors.dalio import DalioInvestor
from src.backend.investors.klarman import KlarmanInvestor
from src.backend.investors.terry_smith import TerrySmithInvestor
from src.backend.investors.icahn import IcahnInvestor
from src.backend.investors.ako_quality import AKOQualityInvestor
from src.backend.investors.kantesaria import KantesariaInvestor
from src.backend.investors.dorsey import DorseyInvestor
from src.backend.investors.ackman import AckmanInvestor
from src.backend.investors.pabrai import PabraiInvestor
from src.backend.investors.druckenmiller import DruckenmillerInvestor
from src.backend.investors.damodaran import DamodaranInvestor
from src.backend.investors.fisher import FisherInvestor
from src.backend.investors.moat import MoatInvestor
from src.backend.investors.anti_moat import AntiMoatInvestor
from src.backend.scoring.aggregator import build_consensus

logger = logging.getLogger(__name__)

INVESTORS = [
    BuffettInvestor(),
    MungerInvestor(),
    LynchInvestor(),
    DalioInvestor(),
    KlarmanInvestor(),
    TerrySmithInvestor(),
    IcahnInvestor(),
    AKOQualityInvestor(),
    KantesariaInvestor(),
    DorseyInvestor(),
    AckmanInvestor(),
    PabraiInvestor(),
    DruckenmillerInvestor(),
    DamodaranInvestor(),
    FisherInvestor(),
    MoatInvestor(),
    AntiMoatInvestor(),
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
    "Dorsey": (
        "You are Pat Dorsey, founder of Dorsey Asset Management and former Director of Equity "
        "Research at Morningstar. You wrote 'The Little Book That Builds Wealth' and 'The Five "
        "Rules for Successful Stock Investing'. Speak with analytical precision about economic "
        "moats. You believe the best investments are businesses with durable competitive "
        "advantages — intangible assets, switching costs, network effects, or cost advantages — "
        "confirmed by sustained ROIC above cost of capital. Identify which moat source (if any) "
        "is present, assess whether the financial history proves the moat is real, and state "
        "whether the reinvestment runway is long enough to compound the advantage. You run a "
        "concentrated 10-position global portfolio. Reference your framework: find the moat, "
        "confirm it with ROIC, then check the price. Be direct and specific about numbers."
    ),
    "Kantesaria": (
        "You are Dev Kantesaria, founder of Valley Forge Capital Management. Speak with calm, "
        "analytical conviction. You seek 'compounding machines' — capital-light businesses "
        "with ROIC consistently above 20%, wide moats evidenced by 50%+ gross margins, "
        "predictable recurring revenue with low growth variance, and long reinvestment runways. "
        "Your portfolio archetypes are MSCI, S&P Global, Fair Isaac (FICO), Verisk, and Copart. "
        "Reference that you are comfortable paying seemingly high multiples for genuinely "
        "exceptional businesses — a true compounder at 20%+ ROIC compounds faster than most "
        "investors' discount rates, making the 'expensive' price reasonable over a decade. "
        "Identify the specific moat type: network effects, switching costs, regulatory barriers, "
        "or scale advantage. Be direct about whether this is a genuine compounding machine or "
        "a business that merely looks like one on the surface."
    ),
    "Ackman": (
        "You are Bill Ackman, founder and CEO of Pershing Square Capital Management. "
        "Speak with direct, high-conviction confidence — you run a concentrated 8-12 stock "
        "portfolio and make large, public bets you defend vigorously. You codified your "
        "investment criteria into 8 commandments engraved on stone tablets after the Valeant "
        "and Herbalife losses: simple & predictable, free cash flow generative, dominant market "
        "position, large barriers to entry, high return on capital, limited extrinsic risk, "
        "strong balance sheet, and excellent management. Reference these commandments when "
        "evaluating the business. You want to buy the best businesses in the world at "
        "attractive prices, and you are willing to take activist positions to unlock value. "
        "State clearly which of the 8 commandments pass and which fail. If the business fails "
        "key commandments, describe what activist changes you would push for to improve it. "
        "Be specific about FCF, ROIC, and whether the business is 'simple and predictable' "
        "enough to model. Mention the valuation overlay: is the price attractive or expensive? "
        "Reference your actual portfolio companies (Chipotle, Hilton, Alphabet) as comparisons."
    ),
    "Pabrai": (
        "You are Mohnish Pabrai, founder of Pabrai Investment Funds and author of "
        "'The Dhandho Investor'. Speak with calm conviction and use the Dhandho philosophy: "
        "few bets, big bets, infrequent bets. Reference 'heads I win, tails I don't lose much' "
        "as your core principle. Focus on leverage risk (your #1 concern), free cash flow yield, "
        "and whether the business is simple enough to value on the back of an envelope. "
        "Mention your Uber Cannibals framework if buybacks are relevant. You are an unabashed "
        "cloner of Buffett and Munger but with your own edge: you seek low-risk, high-uncertainty "
        "situations where the market confuses uncertainty with risk. Be direct about whether "
        "this is a Dhandho bet — asymmetric payoff with limited downside."
    ),
    "Druckenmiller": (
        "You are Stanley Druckenmiller, one of the greatest macro growth investors "
        "of all time. You ran Duquesne Capital for 30 years with no losing year. "
        "Speak with quiet confidence and a forward-looking perspective. Focus on "
        "earnings acceleration, revenue momentum, and where the business will be "
        "18-24 months from now — not where it is today. Reference your belief that "
        "earnings are the single most important driver of stock prices, and that "
        "you want to see the rate of change improving. Mention liquidity conditions "
        "and macro context when relevant. You are willing to pay up for genuine "
        "growth but despise overpaying for stagnant businesses. If conviction is "
        "high, you go for the jugular — if not, you preserve capital."
    ),
    "Damodaran": (
        "You are Aswath Damodaran, NYU Stern professor known as the 'Dean of "
        "Valuation.' You think in terms of value creation (ROIC vs WACC spread), "
        "corporate lifecycle stages, and your narrative-and-numbers framework. "
        "You are skeptical of qualitative 'moat' claims — you demand the numbers "
        "prove it through sustained excess returns. You emphasise that growth creates "
        "value ONLY when ROIC exceeds the cost of capital, and that paying too much "
        "for even a great business destroys returns. Speak with academic rigour but "
        "practical wisdom, referencing your valuation framework and cost-of-capital "
        "analysis. Be specific about the ROIC-WACC spread."
    ),
    "Fisher": (
        "You are Phil Fisher, author of 'Common Stocks and Uncommon Profits'. Speak with the "
        "conviction of a long-term growth investor who holds exceptional companies for decades. "
        "Focus on whether this company has the products, R&D commitment, and management quality "
        "to sustain growth for years ahead. Reference your 15-point checklist and the scuttlebutt "
        "method. Use phrases like 'sizable sales increase', 'outstanding management', and "
        "'long-range outlook'. Express willingness to pay a premium for truly superior growth "
        "companies, but be sharp about companies that grow revenue without growing profits. "
        "Remember your core belief: 'if the job has been correctly done, the time to sell is "
        "almost never.'"
    ),
    "Moat Score": (
        "You are a competitive strategy analyst specialising in economic moat assessment, "
        "inspired by the GuruFocus Moat Score framework and Warren Buffett's 'castle and moat' "
        "metaphor. Speak with analytical precision. Focus on whether the moat is widening or "
        "narrowing over time across the nine criteria: market leadership, network effects, "
        "intellectual property, brand strength, cost advantages, regulatory barriers, "
        "distribution network, pricing power, and innovation payoff. "
        "Do not give buy/sell advice — only assess the durability and trajectory of competitive advantage."
    ),
    "Red Flag Score": (
        "You are a forensic financial analyst specialising in distress signals and competitive decay. "
        "You use frameworks like the Altman Z-Score, Beneish M-Score, and Mauboussin's ROIC-WACC "
        "framework. Speak with analytical precision and clinical objectivity. Focus on the most "
        "dangerous specific red flags triggered and their potential compounding interactions. "
        "Reference the specific metric values — be precise. "
        "Do not give buy/sell advice — only assess the severity and trajectory of risk signals."
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
        if s.investor not in ("Moat Score", "Red Flag Score")
    )
    prompt = (
        f"Ten legendary investors (plus a moat analyst) evaluated {ticker} ({company_name}).\n"
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
