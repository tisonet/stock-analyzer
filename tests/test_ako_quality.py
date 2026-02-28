"""Unit tests for AKO Capital / Quality Investing scoring module."""
from __future__ import annotations

import pytest
from src.backend.investors.ako_quality import AKOQualityInvestor


def test_ako_high_quality_scores_well(high_quality_data):
    """AAPL-like company with sustained ROIC, high margins, strong FCF → scores well."""
    inv = AKOQualityInvestor()
    result = inv.score(high_quality_data)
    assert result.total_score >= 55, (
        f"Expected >= 55 for high quality company, got {result.total_score}"
    )
    assert result.verdict in ("Strong Buy", "Buy")


def test_ako_low_quality_scores_poorly(low_quality_data):
    """Highly leveraged, declining company with negative earnings → scores poorly."""
    inv = AKOQualityInvestor()
    result = inv.score(low_quality_data)
    assert result.total_score <= 35, (
        f"Expected <= 35 for low quality company, got {result.total_score}"
    )
    assert result.verdict in ("Hold", "Avoid")


def test_ako_roic_rule(high_quality_data):
    """Sustained ROIC > 15% every year should pass for a quality compounder."""
    inv = AKOQualityInvestor()
    result = inv.score(high_quality_data)
    roic_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "ROIC" in r.name), None
    )
    assert roic_rule is not None, "ROIC rule must be present"
    assert roic_rule.passed, (
        f"ROIC avg = {roic_rule.value:.1f}% should exceed 15% threshold"
    )


def test_ako_gross_margin_rule(high_quality_data):
    """Gross margin > 40% should pass for a high-quality company."""
    inv = AKOQualityInvestor()
    result = inv.score(high_quality_data)
    gm_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "Gross Margin" in r.name), None
    )
    assert gm_rule is not None, "Gross Margin rule must be present"
    assert gm_rule.passed, (
        f"Gross margin = {gm_rule.value:.1f}% should exceed 40%"
    )


def test_ako_fcf_conversion_rule(high_quality_data):
    """FCF/Net Income > 80% should pass — confirms earnings quality."""
    inv = AKOQualityInvestor()
    result = inv.score(high_quality_data)
    fcf_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "FCF Conversion" in r.name), None
    )
    assert fcf_rule is not None, "FCF Conversion rule must be present"
    assert fcf_rule.passed, (
        f"FCF conversion = {fcf_rule.value:.1f}% should exceed 80%"
    )


def test_ako_revenue_growth_rule(high_quality_data):
    """Consistent revenue growth in most years should pass."""
    inv = AKOQualityInvestor()
    result = inv.score(high_quality_data)
    rev_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Revenue Growth" in r.name), None
    )
    assert rev_rule is not None, "Revenue Growth rule must be present"
    assert rev_rule.passed, "High quality company should pass revenue growth consistency"


def test_ako_low_gross_margin_flagged(low_quality_data):
    """Gross margin below quality threshold should fail and raise a red flag."""
    inv = AKOQualityInvestor()
    result = inv.score(low_quality_data)
    gm_rule = next(
        (r for r in result.rules_failed if "Gross Margin" in r.name), None
    )
    assert gm_rule is not None, "Low-margin company should fail the Gross Margin rule"


def test_ako_inconsistent_roic_rejected():
    """A company with variable ROIC (one negative year) must fail even with a high average."""
    import pandas as pd
    from tests.conftest import (
        _make_income_stmt, _make_balance_sheet, _make_cashflow, _make_history
    )
    from src.backend.data.fetcher import FinancialData

    # ROIC will be negative in the years where op_income is negative
    revs     = [10e9, 10e9, 10e9, 10e9, 10e9]
    op_incs  = [3e9, 3e9, -1e9, 3e9, 3e9]   # one negative year → ROIC goes negative
    net_incs = [2e9, 2e9, -0.8e9, 2e9, 2e9]
    gp       = [5e9, 5e9, 5e9, 5e9, 5e9]
    income = _make_income_stmt(revs, op_incs, net_incs, gp)

    ta   = [20e9] * 5
    ca   = [8e9]  * 5
    cl   = [3e9]  * 5
    tl   = [10e9] * 5
    eq   = [10e9] * 5
    debt = [3e9]  * 5
    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([2.5e9]*5, [0.5e9]*5)
    history = _make_history([100]*2517)

    data = FinancialData(
        ticker="VARI",
        info={
            "trailingPE": 15.0, "priceToBook": 2.0, "debtToEquity": 30.0,
            "marketCap": 20e9, "currentPrice": 20.0, "longName": "Variable ROIC Corp",
        },
        income_stmt=income, balance_sheet=balance, cash_flow=cashflow, history=history,
    )

    inv = AKOQualityInvestor()
    result = inv.score(data)
    roic_rule = next(
        (r for r in result.rules_failed if "ROIC" in r.name), None
    )
    assert roic_rule is not None, (
        "Company with a negative ROIC year must fail the sustained ROIC rule"
    )


def test_ako_score_bounds(high_quality_data, low_quality_data, net_net_data):
    """Score must always be between 0 and 100."""
    inv = AKOQualityInvestor()
    for data in [high_quality_data, low_quality_data, net_net_data]:
        result = inv.score(data)
        assert 0 <= result.total_score <= 100, (
            f"Score {result.total_score} out of bounds for {data.ticker}"
        )


def test_ako_verdict_consistency(high_quality_data):
    """Verdict must match the score threshold."""
    inv = AKOQualityInvestor()
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


def test_ako_no_crash_missing_data(high_quality_data):
    """Removing all financial statements should not crash the scorer."""
    import pandas as pd
    high_quality_data.income_stmt = pd.DataFrame()
    high_quality_data.cash_flow = pd.DataFrame()
    high_quality_data.balance_sheet = pd.DataFrame()
    high_quality_data.info.pop("debtToEquity", None)
    inv = AKOQualityInvestor()
    result = inv.score(high_quality_data)  # must not raise
    assert result.total_score >= 0
