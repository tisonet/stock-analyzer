"""Unit tests for Buffett scoring module."""
from __future__ import annotations

import pytest
from src.backend.investors.buffett import BuffettInvestor


def test_buffett_high_quality_scores_well(high_quality_data):
    inv = BuffettInvestor()
    result = inv.score(high_quality_data)
    assert result.investor == "Buffett"
    assert result.total_score >= 50, f"Expected >= 50 for high-quality co, got {result.total_score}"
    assert result.verdict in ("Strong Buy", "Buy", "Hold")
    assert len(result.rules_passed) > 0
    assert result.key_insight == ""  # filled by engine


def test_buffett_low_quality_scores_poorly(low_quality_data):
    inv = BuffettInvestor()
    result = inv.score(low_quality_data)
    assert result.total_score < 50, f"Expected < 50 for low-quality co, got {result.total_score}"
    assert result.verdict in ("Avoid", "Hold")
    assert len(result.rules_failed) > 0


def test_buffett_high_debt_flagged(low_quality_data):
    inv = BuffettInvestor()
    result = inv.score(low_quality_data)
    # High D/E company should have some red flags
    de_rule = next(
        (r for r in result.rules_failed if "Debt" in r.name), None
    )
    assert de_rule is not None, "High D/E should fail Debt/Equity rule"


def test_buffett_roic_rule(high_quality_data):
    inv = BuffettInvestor()
    result = inv.score(high_quality_data)
    roic_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "ROIC" in r.name), None
    )
    assert roic_rule is not None, "ROIC rule should always be present"
    assert roic_rule.points_possible == 20.0


def test_buffett_no_crash_on_missing_cashflow(high_quality_data):
    """Buffett scorer must not crash if cashflow is empty."""
    import pandas as pd
    high_quality_data.cash_flow = pd.DataFrame()
    inv = BuffettInvestor()
    result = inv.score(high_quality_data)
    assert result.total_score >= 0


def test_buffett_buyback_rule_detected(high_quality_data):
    """Declining shares should be rewarded."""
    inv = BuffettInvestor()
    result = inv.score(high_quality_data)
    buyback_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "Buyback" in r.name), None
    )
    assert buyback_rule is not None
    # high_quality_data has declining share count → should pass
    assert buyback_rule.passed


def test_buffett_dilution_flagged(low_quality_data):
    """Increasing shares should fail buyback rule."""
    inv = BuffettInvestor()
    result = inv.score(low_quality_data)
    buyback_rule = next(
        (r for r in result.rules_failed if "Buyback" in r.name), None
    )
    assert buyback_rule is not None


def test_buffett_score_bounds(high_quality_data):
    inv = BuffettInvestor()
    result = inv.score(high_quality_data)
    assert 0 <= result.total_score <= 100
