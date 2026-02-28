"""Unit tests for Terry Smith scoring module."""
from __future__ import annotations

import pytest
from src.backend.investors.terry_smith import TerrySmithInvestor


def test_terry_smith_high_quality_scores_well(high_quality_data):
    """High ROCE, high gross margin, good cash conversion → should score well."""
    inv = TerrySmithInvestor()
    result = inv.score(high_quality_data)
    assert result.total_score >= 60, (
        f"Expected >= 60 for high-quality data, got {result.total_score}"
    )
    assert result.verdict in ("Strong Buy", "Buy", "Hold")


def test_terry_smith_low_quality_scores_poorly(low_quality_data):
    """Low margins, erratic cash flow, negative FCF → should score poorly."""
    inv = TerrySmithInvestor()
    result = inv.score(low_quality_data)
    assert result.total_score <= 40, (
        f"Expected <= 40 for low-quality data, got {result.total_score}"
    )


def test_terry_smith_roce_rule(high_quality_data):
    """High-quality data has ROIC well above 15% — ROCE rule should pass."""
    inv = TerrySmithInvestor()
    result = inv.score(high_quality_data)
    roce_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "ROCE" in r.name), None
    )
    assert roce_rule is not None, "ROCE rule must be present"
    assert roce_rule.passed, f"High-quality data should pass ROCE rule (value={roce_rule.value})"


def test_terry_smith_gross_margin_rule(high_quality_data):
    """High-quality data has gross margins ~46% → should pass the 40% threshold."""
    inv = TerrySmithInvestor()
    result = inv.score(high_quality_data)
    gm_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Gross Margin" in r.name), None
    )
    assert gm_rule is not None, "Gross Margin rule must be present"
    assert gm_rule.passed, f"Expected gross margin > 40%, got value={gm_rule.value}"


def test_terry_smith_low_gross_margin_flagged(low_quality_data):
    """Low-quality data has gross margins ~20% → should fail the 40% threshold."""
    inv = TerrySmithInvestor()
    result = inv.score(low_quality_data)
    gm_rule = next(
        (r for r in result.rules_failed if "Gross Margin" in r.name), None
    )
    assert gm_rule is not None, "Low gross margin should fail the Gross Margin rule"


def test_terry_smith_cash_conversion_rule(high_quality_data):
    """High-quality data has strong OCF relative to operating income."""
    inv = TerrySmithInvestor()
    result = inv.score(high_quality_data)
    cc_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Cash Conversion" in r.name), None
    )
    assert cc_rule is not None, "Cash Conversion rule must be present"


def test_terry_smith_score_bounds(high_quality_data, low_quality_data, net_net_data):
    """Score must always be between 0 and 100."""
    inv = TerrySmithInvestor()
    for data in [high_quality_data, low_quality_data, net_net_data]:
        result = inv.score(data)
        assert 0 <= result.total_score <= 100, (
            f"Score {result.total_score} out of bounds for {data.ticker}"
        )


def test_terry_smith_verdict_consistency(high_quality_data):
    """Verdict must match the score threshold."""
    inv = TerrySmithInvestor()
    result = inv.score(high_quality_data)
    score = result.total_score
    if score >= 75:
        assert result.verdict == "Strong Buy"
    elif score >= 55:
        assert result.verdict == "Buy"
    elif score >= 40:
        assert result.verdict == "Hold"
    else:
        assert result.verdict == "Avoid"


def test_terry_smith_no_crash_missing_data(high_quality_data):
    """Removing all financial statements should not crash the scorer."""
    import pandas as pd
    high_quality_data.income_stmt = pd.DataFrame()
    high_quality_data.cash_flow = pd.DataFrame()
    inv = TerrySmithInvestor()
    result = inv.score(high_quality_data)  # must not raise
    assert result.total_score >= 0
