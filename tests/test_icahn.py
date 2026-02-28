"""Unit tests for Carl Icahn scoring module."""
from __future__ import annotations

import pytest
from src.backend.investors.icahn import IcahnInvestor


def test_icahn_target_scores_well(icahn_target_data):
    """Classic Icahn target: cheap P/B, high FCF yield, clean balance sheet → score well."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    assert result.total_score >= 80, (
        f"Expected >= 80 for Icahn target, got {result.total_score}"
    )
    assert result.verdict in ("Strong Buy", "Buy")


def test_icahn_non_target_scores_poorly(non_icahn_target_data):
    """Well-managed, expensive, founder-led company — no activist angle → score poorly."""
    inv = IcahnInvestor()
    result = inv.score(non_icahn_target_data)
    assert result.total_score <= 20, (
        f"Expected <= 20 for non-Icahn target, got {result.total_score}"
    )
    assert result.verdict == "Avoid"


def test_icahn_pb_rule_passes(icahn_target_data):
    """P/B < 1.5 should pass for a cheap target."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    pb_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "P/B" in r.name), None
    )
    assert pb_rule is not None, "P/B rule must be present"
    assert pb_rule.passed, f"P/B = {pb_rule.value:.2f} should be < 1.5"


def test_icahn_pb_rule_fails_expensive(non_icahn_target_data):
    """P/B > 1.5 should fail for an expensive stock."""
    inv = IcahnInvestor()
    result = inv.score(non_icahn_target_data)
    pb_rule = next(
        (r for r in result.rules_failed if "P/B" in r.name), None
    )
    assert pb_rule is not None, "Expensive stock should fail the Asset Discount rule"


def test_icahn_fcf_yield_rule(icahn_target_data):
    """FCF yield > 5% should pass for a cash-generative target."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    fcf_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "FCF Yield" in r.name), None
    )
    assert fcf_rule is not None, "FCF Yield rule must be present"
    assert fcf_rule.passed, f"FCF yield = {fcf_rule.value:.1f}% should be > 5%"


def test_icahn_governance_gap_rule(icahn_target_data):
    """Low insider ownership < 10% should signal governance opportunity."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    gov_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "Governance" in r.name), None
    )
    assert gov_rule is not None, "Governance Gap rule must be present"
    assert gov_rule.passed, f"Insider ownership {gov_rule.value:.1f}% should be < 10%"


def test_icahn_leverage_rule(icahn_target_data):
    """D/E < 1.0 should pass for a clean balance sheet."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    lev_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "Leverage" in r.name), None
    )
    assert lev_rule is not None, "Low Leverage rule must be present"
    assert lev_rule.passed, f"D/E = {lev_rule.value:.2f}x should be < 1.0"


def test_icahn_ev_ebitda_rule(icahn_target_data):
    """EV/EBITDA < 8x should pass for a cheap enterprise."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    ev_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Enterprise Value" in r.name), None
    )
    assert ev_rule is not None, "EV/EBITDA rule must be present"
    assert ev_rule.passed, f"EV/EBITDA = {ev_rule.value:.1f}x should be < 8x"


def test_icahn_roe_underperformance_rule(icahn_target_data):
    """ROE between 0-15% with positive FCF should pass the fixable management rule."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    roe_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "ROE" in r.name), None
    )
    assert roe_rule is not None, "ROE rule must be present"
    assert roe_rule.passed, f"ROE = {roe_rule.value:.1f}% should be in 0-15% fixable range"


def test_icahn_score_bounds(icahn_target_data, non_icahn_target_data, net_net_data):
    """Score must always be between 0 and 100."""
    inv = IcahnInvestor()
    for data in [icahn_target_data, non_icahn_target_data, net_net_data]:
        result = inv.score(data)
        assert 0 <= result.total_score <= 100, (
            f"Score {result.total_score} out of bounds for {data.ticker}"
        )


def test_icahn_verdict_consistency(icahn_target_data):
    """Verdict must match the score threshold."""
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)
    score = result.total_score
    if score >= 75:
        assert result.verdict == "Strong Buy"
    elif score >= 55:
        assert result.verdict == "Buy"
    elif score >= 40:
        assert result.verdict == "Hold"
    else:
        assert result.verdict == "Avoid"


def test_icahn_no_crash_missing_data(icahn_target_data):
    """Removing all financial statements and info fields should not crash the scorer."""
    import pandas as pd
    icahn_target_data.income_stmt = pd.DataFrame()
    icahn_target_data.cash_flow = pd.DataFrame()
    icahn_target_data.balance_sheet = pd.DataFrame()
    # Strip the info fields Icahn uses
    for key in ("priceToBook", "debtToEquity", "heldPercentInsiders",
                "enterpriseToEbitda", "returnOnEquity", "marketCap"):
        icahn_target_data.info.pop(key, None)
    inv = IcahnInvestor()
    result = inv.score(icahn_target_data)  # must not raise
    assert result.total_score >= 0
