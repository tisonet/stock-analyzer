"""Unit tests for the scoring aggregator logic."""
from __future__ import annotations

import pytest
from src.backend.investors.base_investor import InvestorScore, Rule
from src.backend.scoring.aggregator import build_consensus, WEIGHTS


def _make_score(investor: str, total_score: float) -> InvestorScore:
    return InvestorScore(
        investor=investor,
        total_score=total_score,
        verdict="Buy",
        rules_passed=[],
        rules_failed=[],
        key_insight="",
        red_flags=[],
    )


def test_consensus_high_conviction():
    """All investors agree (low std dev) → High Conviction."""
    scores = [
        _make_score("Buffett", 72),
        _make_score("Munger", 70),
        _make_score("Graham", 68),
        _make_score("Lynch", 74),
        _make_score("Dalio", 71),
        _make_score("Klarman", 69),
    ]
    consensus = build_consensus("TEST", scores)
    assert consensus.agreement_level == "High Conviction"
    assert 65 <= consensus.weighted_avg <= 78


def test_consensus_divided():
    """Large score spread → Divided."""
    scores = [
        _make_score("Buffett", 85),
        _make_score("Munger", 80),
        _make_score("Graham", 20),
        _make_score("Lynch", 75),
        _make_score("Dalio", 60),
        _make_score("Klarman", 15),
    ]
    consensus = build_consensus("TEST", scores)
    assert consensus.agreement_level == "Divided"


def test_consensus_mixed():
    """Moderate spread → Mixed."""
    scores = [
        _make_score("Buffett", 70),
        _make_score("Munger", 65),
        _make_score("Graham", 45),
        _make_score("Lynch", 60),
        _make_score("Dalio", 55),
        _make_score("Klarman", 40),
    ]
    consensus = build_consensus("TEST", scores)
    assert consensus.agreement_level in ("Mixed", "High Conviction")


def test_dalio_weight_zero():
    """Dalio has weight=0 (excluded from consensus, macro-focused).
    A Dalio score of 0 must not drag down the consensus avg.
    """
    scores = [
        _make_score("Buffett", 100),
        _make_score("Munger", 100),
        _make_score("Graham", 100),
        _make_score("Lynch", 100),
        _make_score("Dalio", 0),     # weight=0 → excluded from consensus
        _make_score("Klarman", 100),
    ]
    consensus = build_consensus("TEST", scores)
    # Dalio excluded (weight=0): weighted_avg = 500 / 5.0 = 100.0
    assert WEIGHTS["Dalio"] == 0, "Dalio weight must be 0 (excluded from buy/sell consensus)"
    assert abs(consensus.weighted_avg - 100.0) < 0.5


def test_consensus_empty():
    """Empty investor list should not crash."""
    consensus = build_consensus("EMPTY", [])
    assert consensus.weighted_avg == 0.0
    assert consensus.agreement_level == "No Data"


def test_consensus_ticker_preserved():
    scores = [_make_score("Buffett", 60)]
    consensus = build_consensus("AAPL", scores)
    assert consensus.ticker == "AAPL"
