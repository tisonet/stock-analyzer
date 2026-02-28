"""Unit tests for Graham scoring module."""
from __future__ import annotations

import pytest
from src.backend.investors.graham import GrahamInvestor


def test_graham_net_net_scores_well(net_net_data):
    inv = GrahamInvestor()
    result = inv.score(net_net_data)
    assert result.total_score >= 60, f"Expected >= 60 for net-net, got {result.total_score}"
    assert result.verdict in ("Buy", "Strong Buy", "Hold")


def test_graham_expensive_growth_scores_poorly(high_quality_data):
    """High P/E technology company should score poorly for Graham."""
    inv = GrahamInvestor()
    result = inv.score(high_quality_data)
    # P/E=22, P/B=7 → P/E*P/B=154 >> 22.5 → should fail valuation rule
    pe_pb_rule = next(
        (r for r in result.rules_failed if "P/E" in r.name), None
    )
    assert pe_pb_rule is not None, "High P/E×P/B should fail Graham valuation rule"


def test_graham_low_current_ratio_flagged(low_quality_data):
    inv = GrahamInvestor()
    result = inv.score(low_quality_data)
    cr_rule = next(
        (r for r in result.rules_failed if "Current Ratio" in r.name), None
    )
    assert cr_rule is not None, "Current ratio < 1 should fail"


def test_graham_dividend_rule_net_net(net_net_data):
    inv = GrahamInvestor()
    result = inv.score(net_net_data)
    div_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "dividend" in r.name.lower()),
        None,
    )
    assert div_rule is not None
    assert div_rule.passed, "net_net_data pays dividends → should pass"


def test_graham_no_dividend_fails(low_quality_data):
    inv = GrahamInvestor()
    result = inv.score(low_quality_data)
    div_rule = next(
        (r for r in result.rules_failed if "dividend" in r.name.lower()), None
    )
    assert div_rule is not None, "No dividend company should fail dividend rule"


def test_graham_eps_growth(net_net_data):
    """EPS series in net_net_data goes from 0.7 to 1.5 → 114% growth > 33%."""
    inv = GrahamInvestor()
    result = inv.score(net_net_data)
    eps_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "EPS growth" in r.name), None
    )
    assert eps_rule is not None
    assert eps_rule.passed, "EPS doubled over 10yr should pass 33% threshold"


def test_graham_score_bounds(net_net_data):
    inv = GrahamInvestor()
    result = inv.score(net_net_data)
    assert 0 <= result.total_score <= 100


def test_graham_missing_pe_pb(net_net_data):
    """Should not crash if P/E or P/B is missing."""
    net_net_data.info.pop("trailingPE", None)
    inv = GrahamInvestor()
    result = inv.score(net_net_data)
    assert result.total_score >= 0
