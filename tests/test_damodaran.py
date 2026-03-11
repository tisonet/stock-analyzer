"""
Tests for the Aswath Damodaran value-creation investor module.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.backend.data.fetcher import FinancialData
from src.backend.investors.damodaran import DamodaranInvestor
from tests.conftest import (
    _make_balance_sheet,
    _make_cashflow,
    _make_history,
    _make_income_stmt,
)

INV = DamodaranInvestor()


def _add_interest_expense(income_stmt: pd.DataFrame, values: list) -> pd.DataFrame:
    """Inject an Interest Expense row into an existing income statement."""
    cols = income_stmt.columns[:len(values)]
    row = pd.DataFrame(
        [values[:len(cols)]],
        columns=cols,
        index=["Interest Expense"],
    )
    return pd.concat([income_stmt, row])


# ── Ideal Damodaran company fixture ──────────────────────────────────────

@pytest.fixture
def damodaran_ideal() -> FinancialData:
    """High-ROIC, low-leverage company with consistent value creation."""
    revs =    [100e9, 92e9, 85e9, 78e9, 72e9, 66e9, 60e9, 55e9, 50e9, 46e9]
    op_incs = [ 25e9, 23e9, 21e9, 19e9, 17e9, 15e9, 13e9, 12e9, 11e9, 10e9]
    net_incs = [20e9, 18e9, 17e9, 15e9, 13e9, 12e9, 10e9,  9e9,  8e9,  7e9]
    gp =      [ 55e9, 50e9, 46e9, 42e9, 38e9, 35e9, 32e9, 29e9, 26e9, 24e9]

    income = _make_income_stmt(
        revs, op_incs, net_incs, gp,
        tax_provisions=[op * 0.20 for op in op_incs],
    )
    # Add interest expense (low — well covered)
    income = _add_interest_expense(income, [2e9, 1.8e9, 1.6e9, 1.5e9, 1.4e9,
                                             1.3e9, 1.2e9, 1.1e9, 1.0e9, 0.9e9])

    ta =   [80e9, 75e9, 70e9, 65e9, 60e9]
    ca =   [30e9, 28e9, 26e9, 24e9, 22e9]
    cl =   [15e9, 14e9, 13e9, 12e9, 11e9]
    tl =   [35e9, 33e9, 31e9, 29e9, 27e9]
    eq =   [45e9, 42e9, 39e9, 36e9, 33e9]
    debt = [15e9, 14e9, 13e9, 12e9, 11e9]
    cash = [ 8e9,  7e9,  6e9,  5e9,  5e9]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, cash=cash)
    cashflow = _make_cashflow(
        [22e9, 20e9, 18e9, 16e9, 14e9],
        [ 3e9,  2.8e9, 2.5e9, 2.2e9, 2e9],
    )
    prices = list(range(100, 350)) + list(range(350, 320, -3)) + list(range(320, 500))
    history = _make_history(prices[:2517])

    return FinancialData(
        ticker="DAMO",
        info={
            "trailingPE": 20.0,
            "priceToBook": 5.0,
            "debtToEquity": 33.0,
            "currentRatio": 2.0,
            "marketCap": 400e9,
            "currentPrice": 200.0,
            "sharesOutstanding": 2_000_000_000,
            "trailingEps": 10.0,
            "bookValue": 22.5,
            "beta": 1.0,
            "sector": "Technology",
            "industry": "Software",
            "country": "United States",
            "longName": "Damodaran Ideal Corp",
            "longBusinessSummary": "High-ROIC software company.",
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ── Basic tests ──────────────────────────────────────────────────────────

def test_name():
    assert INV.name == "Damodaran"


def test_ideal_strong_buy(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    assert result.total_score >= 75
    assert result.verdict == "Strong Buy"


def test_high_quality_strong_buy(high_quality_data):
    result = INV.score(high_quality_data)
    assert result.total_score >= 75
    assert result.verdict == "Strong Buy"


def test_low_quality_avoid(low_quality_data):
    result = INV.score(low_quality_data)
    assert result.total_score <= 30
    assert result.verdict == "Avoid"


def test_empty_data_crash_safety(empty_data):
    result = INV.score(empty_data)
    assert 0 <= result.total_score <= 100
    assert result.verdict in ("Strong Buy", "Buy", "Hold", "Avoid")


def test_score_bounded(high_quality_data, low_quality_data, empty_data):
    for data in [high_quality_data, low_quality_data, empty_data]:
        result = INV.score(data)
        assert 0 <= result.total_score <= 100


def test_verdict_matches_score(high_quality_data, low_quality_data, empty_data):
    for data in [high_quality_data, low_quality_data, empty_data]:
        result = INV.score(data)
        if result.total_score >= 75:
            assert result.verdict == "Strong Buy"
        elif result.total_score >= 55:
            assert result.verdict == "Buy"
        elif result.total_score >= 40:
            assert result.verdict == "Hold"
        else:
            assert result.verdict == "Avoid"


def test_rules_sum_to_100(high_quality_data):
    result = INV.score(high_quality_data)
    all_rules = result.rules_passed + result.rules_failed
    total_possible = sum(r.points_possible for r in all_rules)
    assert total_possible == 100.0


def test_seven_rules(high_quality_data):
    result = INV.score(high_quality_data)
    assert len(result.rules_passed) + len(result.rules_failed) == 7


# ── Rule-level tests ─────────────────────────────────────────────────────

def _find_rule(result, keyword: str):
    """Locate a rule by partial name match."""
    for r in result.rules_passed + result.rules_failed:
        if keyword.lower() in r.name.lower():
            return r
    raise KeyError(f"No rule matching '{keyword}'")


def test_roic_wacc_spread_passes(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    rule = _find_rule(result, "ROIC vs WACC")
    assert rule.passed
    assert rule.points_awarded > 0


def test_roic_wacc_spread_fails_low_quality(low_quality_data):
    result = INV.score(low_quality_data)
    rule = _find_rule(result, "ROIC vs WACC")
    assert not rule.passed


def test_excess_return_persistence_passes(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    rule = _find_rule(result, "Persistence")
    assert rule.passed
    assert rule.points_awarded > 0


def test_revenue_growth_passes(high_quality_data):
    result = INV.score(high_quality_data)
    rule = _find_rule(result, "Revenue Growth")
    assert rule.passed
    assert rule.points_awarded > 0


def test_revenue_growth_declining():
    """Revenue declining year-over-year → fails."""
    revs =    [30e9, 35e9, 40e9, 45e9, 50e9, 55e9, 60e9, 65e9, 70e9, 75e9]
    op_incs = [ 1e9,  1e9,  1e9,  1e9,  1e9,  1e9,  1e9,  1e9,  1e9,  1e9]
    net_incs = [0.5e9]*10

    income = _make_income_stmt(revs, op_incs, net_incs)
    balance = _make_balance_sheet(
        [50e9]*5, [20e9]*5, [10e9]*5, [30e9]*5, [20e9]*5, [10e9]*5,
    )
    cashflow = _make_cashflow([2e9]*5, [1e9]*5)
    prices = [100]*2517
    history = _make_history(prices)

    data = FinancialData(
        ticker="DECL",
        info={"marketCap": 40e9, "beta": 1.0},
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )
    result = INV.score(data)
    rule = _find_rule(result, "Revenue Growth")
    # Revenues go from 75e9 → 30e9 after reversal (oldest=75e9, newest=30e9)
    # That's negative CAGR → partial = 0
    assert rule.points_awarded == 0


def test_operating_margin_stability_passes(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    rule = _find_rule(result, "Operating Margin")
    assert rule.passed
    assert rule.points_awarded > 0


def test_capital_efficiency_passes(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    rule = _find_rule(result, "Capital Efficiency")
    assert rule.passed
    assert rule.points_awarded > 0


def test_fcf_conversion_passes(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    rule = _find_rule(result, "Free Cash Flow")
    assert rule.passed
    assert rule.points_awarded > 0


def test_fcf_conversion_fails_negative():
    """Negative FCF margins → fails."""
    revs =    [50e9]*10
    op_incs = [3e9]*10
    net_incs = [1e9]*10

    income = _make_income_stmt(revs, op_incs, net_incs)
    balance = _make_balance_sheet(
        [80e9]*5, [20e9]*5, [15e9]*5, [50e9]*5, [30e9]*5, [20e9]*5,
    )
    # CapEx far exceeds OCF → negative FCF
    cashflow = _make_cashflow([2e9]*5, [10e9]*5)
    prices = [100]*2517
    history = _make_history(prices)

    data = FinancialData(
        ticker="BURN",
        info={"marketCap": 100e9, "beta": 1.0},
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )
    result = INV.score(data)
    rule = _find_rule(result, "Free Cash Flow")
    assert rule.points_awarded == 0


def test_financial_risk_passes_with_coverage(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    rule = _find_rule(result, "Financial Risk")
    assert rule.passed
    assert rule.points_awarded > 0


def test_financial_risk_high_leverage():
    """Extremely leveraged company → low risk score."""
    revs =    [20e9]*10
    op_incs = [2e9]*10
    net_incs = [0.5e9]*10

    income = _make_income_stmt(revs, op_incs, net_incs)
    # Add high interest expense → low coverage
    income = _add_interest_expense(income, [1.8e9]*10)

    balance = _make_balance_sheet(
        [100e9]*5, [10e9]*5, [20e9]*5, [90e9]*5, [10e9]*5, [80e9]*5,
    )
    cashflow = _make_cashflow([3e9]*5, [1e9]*5)
    prices = [100]*2517
    history = _make_history(prices)

    data = FinancialData(
        ticker="LEVR",
        info={"marketCap": 10e9, "beta": 1.5},
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )
    result = INV.score(data)
    rule = _find_rule(result, "Financial Risk")
    # Coverage = 2e9/1.8e9 ≈ 1.1x, debt/capital = 80/(80+10)=0.89
    # Very low coverage + very high leverage → low score
    assert rule.points_awarded < 5


# ── Red flag tests ───────────────────────────────────────────────────────

def test_red_flags_on_value_destruction(low_quality_data):
    result = INV.score(low_quality_data)
    # Low-quality company may trigger red flags for revenue decline or negative FCF
    # At minimum it should not crash
    assert isinstance(result.red_flags, list)


def test_no_red_flags_ideal(damodaran_ideal):
    result = INV.score(damodaran_ideal)
    assert len(result.red_flags) == 0


# ── Synthetic-spread helper test ─────────────────────────────────────────

def test_synthetic_spread_table():
    """Verify the synthetic rating table returns expected spreads."""
    assert DamodaranInvestor._synthetic_spread(15.0) == 0.0075   # AAA
    assert DamodaranInvestor._synthetic_spread(10.0) == 0.01     # AA
    assert DamodaranInvestor._synthetic_spread(5.0) == 0.015     # A-
    assert DamodaranInvestor._synthetic_spread(3.2) == 0.03      # BB
    assert DamodaranInvestor._synthetic_spread(1.0) == 0.08      # CC
    assert DamodaranInvestor._synthetic_spread(0.5) == 0.12      # D


# ── WACC estimation test ────────────────────────────────────────────────

def test_wacc_estimation(damodaran_ideal):
    wacc = INV._estimate_wacc(damodaran_ideal)
    assert wacc is not None
    # WACC should be reasonable (5-15% range for a US equity)
    assert 0.05 < wacc < 0.15


def test_wacc_returns_none_empty(empty_data):
    wacc = INV._estimate_wacc(empty_data)
    assert wacc is None
