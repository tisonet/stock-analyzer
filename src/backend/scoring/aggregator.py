"""
Aggregates individual InvestorScore objects into a ConsensusScore.
"""
from __future__ import annotations

import statistics
import logging

from src.backend.investors.base_investor import InvestorScore, ConsensusScore

logger = logging.getLogger(__name__)

# Investor weights (Dalio slightly lower — macro-focused, less stock-specific)
WEIGHTS: dict[str, float] = {
    "Buffett": 1.0,
    "Munger": 1.0,
    "Graham": 1.0,
    "Lynch": 1.0,
    "Dalio": 0.0,
    "Klarman": 1.0,
    "Terry Smith": 1.0,
    "Icahn": 0.0,
    "AKO Quality": 1.0,
    "Kantesaria": 1.0,
    "Dorsey": 1.0,
    "Ackman": 1.0,
    "Pabrai": 1.0,
    "Druckenmiller": 1.0,
    "Damodaran": 1.0,
    "Fisher": 1.0,
    "Moat Score": 0,    # analytical only — excluded from buy/sell consensus
    "Red Flag Score": 0,  # analytical only — excluded from buy/sell consensus
}


def build_consensus(ticker: str, investor_scores: list[InvestorScore]) -> ConsensusScore:
    """
    Compute weighted average score and agreement level from all investor scores.
    overall_narrative is set to empty string here; filled in by engine after Claude call.
    """
    if not investor_scores:
        return ConsensusScore(
            ticker=ticker,
            weighted_avg=0.0,
            agreement_level="No Data",
            investor_scores=[],
            overall_narrative="No investor scores available.",
        )

    total_weight = 0.0
    weighted_sum = 0.0
    for s in investor_scores:
        w = WEIGHTS.get(s.investor, 1.0)
        weighted_sum += s.total_score * w
        total_weight += w

    weighted_avg = weighted_sum / total_weight if total_weight > 0 else 0.0

    # Agreement level based on score standard deviation
    raw_scores = [s.total_score for s in investor_scores]
    std_dev = statistics.stdev(raw_scores) if len(raw_scores) > 1 else 0.0

    if std_dev < 12:
        agreement_level = "High Conviction"
    elif std_dev < 22:
        agreement_level = "Mixed"
    else:
        agreement_level = "Divided"

    logger.info(
        f"{ticker} consensus: {weighted_avg:.1f}/100 ({agreement_level}), "
        f"stdev={std_dev:.1f}"
    )

    return ConsensusScore(
        ticker=ticker,
        weighted_avg=weighted_avg,
        agreement_level=agreement_level,
        investor_scores=investor_scores,
        overall_narrative="",  # filled by engine
    )
