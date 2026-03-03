"""
Unit tests for Pat Dorsey / Dorsey Asset Management scoring module.

Test philosophy mirrors the real scoring — six rules, 100 pts total:
  1. ROIC ≥ 15% (financial fingerprint of a moat)              — 25 pts
  2. Net Profit Margin ≥ 15% (structural pricing power)        — 20 pts
  3. FCF/Sales ≥ 5% (cash generation quality)                  — 15 pts
  4. Revenue CAGR ≥ 8% (reinvestment runway)                   — 20 pts
  5. Earnings Quality: OCF/Net Income ≥ 0.85                   — 10 pts
  6. Capital Structure: D/E ≤ 1.0 and Interest Coverage ≥ 3×   — 10 pts
"""
from __future__ import annotations

import pytest

from src.backend.data.fetcher import FinancialData
from src.backend.investors.dorsey import DorseyInvestor
from tests.conftest import (
    _make_balance_sheet,
    _make_cashflow,
    _make_history,
    _make_income_stmt,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper fixture: ideal "Dorsey compounder" — all 6 rules should pass
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def dorsey_ideal_data() -> FinancialData:
    """
    Ideal Dorsey compounder — Visa/Mastercard-like:
      - ROIC ~25% (network effect moat confirmed)
      - Net margin ~40% (structural pricing power)
      - FCF/Sales ~35% (cash machine)
      - Revenue CAGR ~11% (long reinvestment runway)
      - OCF/NI ~1.2 (high-quality earnings)
      - D/E ~0.3 (clean balance sheet)
    """
    revs    = [30e9, 27e9, 24e9, 21e9, 19e9, 17e9, 15e9, 13e9, 12e9, 10e9]
    op_incs = [18e9, 16e9, 14e9, 12e9, 11e9, 10e9,  9e9,  8e9,  7e9,  6e9]
    ni      = [12e9, 11e9,  9e9,  8e9,  7e9,  6e9,  5e9,  4e9,  3.5e9, 3e9]
    gp      = [25e9, 22e9, 20e9, 17e9, 15e9, 14e9, 12e9, 11e9, 10e9,  8e9]
    tax_p   = [op * 0.20 for op in op_incs]

    income = _make_income_stmt(revs, op_incs, ni, gp, epss=None, tax_provisions=tax_p)

    ta   = [50e9, 47e9, 44e9, 41e9, 38e9]
    ca   = [20e9, 18e9, 17e9, 16e9, 15e9]
    cl   = [ 8e9,  7e9,  7e9,  6e9,  6e9]
    tl   = [20e9, 19e9, 18e9, 17e9, 16e9]
    eq   = [30e9, 28e9, 26e9, 24e9, 22e9]
    debt = [ 9e9,  8e9,  8e9,  7e9,  7e9]
    cash = [ 5e9,  4e9,  4e9,  3e9,  3e9]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, cash=cash)
    cashflow = _make_cashflow(
        [11e9, 10e9, 8.5e9, 7.5e9, 7e9],   # OCF ~37% of revenue
        [ 0.5e9, 0.4e9, 0.4e9, 0.3e9, 0.3e9],  # CapEx ~2%
    )
    prices = [100 + i * 0.2 for i in range(2517)]
    history = _make_history(prices)

    return FinancialData(
        ticker="IDEAL",
        info={
            "trailingPE": 28.0,
            "priceToBook": 8.0,
            "debtToEquity": 30.0,
            "currentRatio": 2.5,
            "marketCap": 300e9,
            "currentPrice": 120.0,
            "sharesOutstanding": 2_500_000_000,
            "longName": "Ideal Moat Corp",
            "longBusinessSummary": "Payment network with strong network effects and switching costs.",
            "sector": "Financial Services",
            "industry": "Credit Services",
            "country": "United States",
            "revenueGrowth": 0.11,
            "earningsGrowth": 0.12,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core verdict tests
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_investor_name():
    assert DorseyInvestor().name == "Dorsey"


def test_dorsey_ideal_compounder_strong_buy(dorsey_ideal_data):
    """Visa/Mastercard-like moat compounder → all rules pass → Strong Buy."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    assert result.total_score >= 75, (
        f"Expected ≥ 75 for an ideal Dorsey compounder, got {result.total_score:.1f}"
    )
    assert result.verdict == "Strong Buy"


def test_dorsey_high_quality_data_strong_buy(high_quality_data):
    """AAPL-like fixture: high ROIC, strong net margin, good FCF → Strong Buy."""
    inv = DorseyInvestor()
    result = inv.score(high_quality_data)
    assert result.total_score >= 75, (
        f"Expected ≥ 75 for AAPL-like company, got {result.total_score:.1f}"
    )
    assert result.verdict == "Strong Buy"


def test_dorsey_net_net_data_hold_or_lower(net_net_data):
    """Graham net-net: modest margins, slow growth → fails moat tests → Hold/Avoid."""
    inv = DorseyInvestor()
    result = inv.score(net_net_data)
    assert result.total_score <= 60, (
        f"Expected ≤ 60 for a slow-growth, modest-margin net-net, got {result.total_score:.1f}"
    )


def test_dorsey_low_quality_data_avoid(low_quality_data):
    """Leveraged, declining, cash-burning company → Avoid."""
    inv = DorseyInvestor()
    result = inv.score(low_quality_data)
    assert result.total_score <= 30, (
        f"Expected ≤ 30 for low quality company, got {result.total_score:.1f}"
    )
    assert result.verdict == "Avoid"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1: ROIC ≥ 15%
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_roic_rule_passes(dorsey_ideal_data):
    """ROIC ~25% should pass the ≥ 15% threshold."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    roic_rule = next(r for r in result.rules_passed + result.rules_failed if "ROIC" in r.name)
    assert roic_rule.passed, f"ROIC {roic_rule.value:.1f}% should pass 15% threshold"
    assert roic_rule.value >= 15.0


def test_dorsey_roic_rule_fails_below_15():
    """Low-margin commodity business with ROIC ~6% → ROIC rule fails."""
    revs    = [40e9] * 10
    op_incs = [ 2e9] * 10   # 5% op margin → low ROIC
    ni      = [ 1e9] * 10
    gp      = [10e9] * 10
    income  = _make_income_stmt(revs, op_incs, ni, gp)

    ta = [50e9] * 5; ca = [10e9] * 5; cl = [8e9] * 5
    tl = [30e9] * 5; eq = [20e9] * 5; debt = [10e9] * 5
    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([2.5e9] * 5, [1e9] * 5)

    data = FinancialData(
        ticker="COMM",
        info={"marketCap": 10e9, "longName": "Commodity Corp"},
        income_stmt=income, balance_sheet=balance,
        cash_flow=cashflow, history=_make_history([100] * 2517),
    )
    inv = DorseyInvestor()
    result = inv.score(data)
    roic_rule = next(r for r in result.rules_passed + result.rules_failed if "ROIC" in r.name)
    assert not roic_rule.passed, f"ROIC {roic_rule.value:.1f}% should fail 15% threshold"
    assert roic_rule.value < 15.0


def test_dorsey_roic_negative_year_fails():
    """One year of negative ROIC fails Rule 1 even with high average."""
    revs    = [10e9] * 5
    op_incs = [3e9, 3e9, -0.5e9, 3e9, 3e9]
    ni      = [2e9, 2e9, -0.3e9, 2e9, 2e9]
    gp      = [7e9] * 5
    income  = _make_income_stmt(revs, op_incs, ni, gp)

    ta = [15e9]*5; ca = [4e9]*5; cl = [1e9]*5
    tl = [6e9]*5;  eq = [9e9]*5; debt = [2e9]*5
    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([2e9]*5, [0.1e9]*5)

    data = FinancialData(
        ticker="NEG",
        info={"marketCap": 10e9, "longName": "Negative Year Corp"},
        income_stmt=income, balance_sheet=balance,
        cash_flow=cashflow, history=_make_history([100] * 2517),
    )
    inv = DorseyInvestor()
    result = inv.score(data)
    roic_rule = next(
        (r for r in result.rules_failed if "ROIC" in r.name), None
    )
    assert roic_rule is not None, "Company with a negative ROIC year must fail Rule 1"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2: Net Profit Margin ≥ 15%
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_net_margin_passes(dorsey_ideal_data):
    """Net margin ~40% should pass the ≥ 15% threshold."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    nm_rule = next(r for r in result.rules_passed + result.rules_failed if "Net Profit" in r.name)
    assert nm_rule.passed, f"Net margin {nm_rule.value:.1f}% should pass 15% threshold"
    assert nm_rule.value >= 15.0


def test_dorsey_net_margin_fails_below_15():
    """Low-margin retailer at 5% net margin → net margin rule fails."""
    revs    = [100e9] * 10
    op_incs = [ 8e9]  * 10
    ni      = [ 5e9]  * 10    # 5% net margin
    gp      = [25e9]  * 10
    income  = _make_income_stmt(revs, op_incs, ni, gp)

    ta = [80e9]*5; ca=[20e9]*5; cl=[15e9]*5
    tl = [50e9]*5; eq=[30e9]*5; debt=[20e9]*5
    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([6e9]*5, [4e9]*5)

    data = FinancialData(
        ticker="LOWM",
        info={"marketCap": 30e9, "longName": "Low Margin Retailer"},
        income_stmt=income, balance_sheet=balance,
        cash_flow=cashflow, history=_make_history([100] * 2517),
    )
    inv = DorseyInvestor()
    result = inv.score(data)
    nm_rule = next(r for r in result.rules_passed + result.rules_failed if "Net Profit" in r.name)
    assert not nm_rule.passed, f"Net margin {nm_rule.value:.1f}% should fail 15% threshold"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3: FCF/Sales ≥ 5%
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_fcf_sales_passes(dorsey_ideal_data):
    """FCF/Sales ~35% should pass the ≥ 5% threshold."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    fcf_rule = next(r for r in result.rules_passed + result.rules_failed if "FCF/Sales" in r.name)
    assert fcf_rule.passed, f"FCF/Sales {fcf_rule.value:.1f}% should pass 5% threshold"
    assert fcf_rule.value >= 5.0


def test_dorsey_fcf_sales_fails_capex_heavy():
    """Capital-intensive business with negative FCF → FCF/Sales rule fails."""
    revs    = [50e9] * 10
    op_incs = [ 8e9] * 10
    ni      = [ 5e9] * 10
    gp      = [20e9] * 10
    income  = _make_income_stmt(revs, op_incs, ni, gp)

    ta = [100e9]*5; ca=[15e9]*5; cl=[10e9]*5
    tl = [60e9]*5;  eq=[40e9]*5; debt=[25e9]*5
    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    # CapEx > OCF → negative FCF
    cashflow = _make_cashflow([5e9]*5, [8e9]*5)

    data = FinancialData(
        ticker="CAPX",
        info={"marketCap": 30e9, "longName": "Capex Heavy Corp"},
        income_stmt=income, balance_sheet=balance,
        cash_flow=cashflow, history=_make_history([100] * 2517),
    )
    inv = DorseyInvestor()
    result = inv.score(data)
    fcf_rule = next(r for r in result.rules_passed + result.rules_failed if "FCF/Sales" in r.name)
    assert not fcf_rule.passed, "Negative FCF should fail the FCF/Sales rule"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4: Revenue CAGR ≥ 8%
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_revenue_cagr_passes(dorsey_ideal_data):
    """Revenue CAGR ~11% should pass the ≥ 8% threshold."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    cagr_rule = next(r for r in result.rules_passed + result.rules_failed if "CAGR" in r.name)
    assert cagr_rule.passed, f"Revenue CAGR {cagr_rule.value:.1f}% should pass 8% threshold"
    assert cagr_rule.value >= 8.0


def test_dorsey_revenue_cagr_fails_slow_growth():
    """Stagnant business growing at 2% CAGR → CAGR rule fails."""
    # Revenue growing from 40e9 to 43e9 over 9 years → ~0.8% CAGR
    revs    = [43e9, 42.5e9, 42e9, 41.5e9, 41e9, 40.5e9, 40e9, 40e9, 40e9, 40e9]
    op_incs = [8e9] * 10; ni = [5e9] * 10; gp = [20e9] * 10
    income  = _make_income_stmt(revs, op_incs, ni, gp)

    ta = [60e9]*5; ca=[12e9]*5; cl=[8e9]*5
    tl = [30e9]*5; eq=[30e9]*5; debt=[10e9]*5
    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([6e9]*5, [1e9]*5)

    data = FinancialData(
        ticker="SLOW",
        info={"marketCap": 40e9, "longName": "Stagnant Corp"},
        income_stmt=income, balance_sheet=balance,
        cash_flow=cashflow, history=_make_history([100] * 2517),
    )
    inv = DorseyInvestor()
    result = inv.score(data)
    cagr_rule = next(r for r in result.rules_passed + result.rules_failed if "CAGR" in r.name)
    assert not cagr_rule.passed, f"CAGR {cagr_rule.value:.1f}% should fail 8% threshold"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 5: Earnings Quality (OCF/NI ≥ 0.85)
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_earnings_quality_passes(dorsey_ideal_data):
    """OCF/NI ~1.2 should pass the ≥ 0.85 threshold."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    eq_rule = next(r for r in result.rules_passed + result.rules_failed if "Earnings Quality" in r.name)
    assert eq_rule.passed, f"OCF/NI {eq_rule.value:.2f}x should pass 0.85 threshold"
    assert eq_rule.value >= 0.85


def test_dorsey_earnings_quality_fails_low_ocf():
    """OCF/NI ~0.50 → earnings quality rule fails (aggressive accruals)."""
    revs    = [30e9] * 10
    op_incs = [ 6e9] * 10
    ni      = [ 4e9] * 10
    gp      = [15e9] * 10
    income  = _make_income_stmt(revs, op_incs, ni, gp)

    ta = [40e9]*5; ca=[10e9]*5; cl=[7e9]*5
    tl = [20e9]*5; eq=[20e9]*5; debt=[8e9]*5
    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    # OCF = 2e9 but NI = 4e9 → ratio = 0.50 → earnings quality fail
    cashflow = _make_cashflow([2e9]*5, [0.5e9]*5)

    data = FinancialData(
        ticker="ACRL",
        info={"marketCap": 20e9, "longName": "Accrual Corp"},
        income_stmt=income, balance_sheet=balance,
        cash_flow=cashflow, history=_make_history([100] * 2517),
    )
    inv = DorseyInvestor()
    result = inv.score(data)
    eq_rule = next(r for r in result.rules_passed + result.rules_failed if "Earnings Quality" in r.name)
    assert not eq_rule.passed, f"OCF/NI {eq_rule.value:.2f}x should fail 0.85 threshold"
    assert eq_rule.value < 0.85


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6: Capital Structure (D/E ≤ 1.0 and Coverage ≥ 3×)
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_capital_structure_passes(dorsey_ideal_data):
    """D/E ~0.3 should pass the capital structure rule."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    cap_rule = next(r for r in result.rules_passed + result.rules_failed if "Capital Structure" in r.name)
    assert cap_rule.passed, f"D/E {cap_rule.value:.2f}x should pass 1.0x threshold"


def test_dorsey_capital_structure_fails_high_leverage(low_quality_data):
    """D/E ~9.0 should fail the capital structure rule."""
    inv = DorseyInvestor()
    result = inv.score(low_quality_data)
    cap_rule = next(r for r in result.rules_passed + result.rules_failed if "Capital Structure" in r.name)
    assert not cap_rule.passed, "D/E ~9.0 should fail the capital structure rule"


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases and robustness
# ─────────────────────────────────────────────────────────────────────────────

def test_dorsey_empty_dataframes():
    """Empty DataFrames should not raise — returns a valid InvestorScore."""
    import pandas as pd
    data = FinancialData(
        ticker="EMPTY",
        info={},
        income_stmt=pd.DataFrame(),
        balance_sheet=pd.DataFrame(),
        cash_flow=pd.DataFrame(),
        history=pd.DataFrame(),
    )
    inv = DorseyInvestor()
    result = inv.score(data)
    assert result is not None
    assert 0 <= result.total_score <= 100
    assert result.investor == "Dorsey"


def test_dorsey_score_bounded(dorsey_ideal_data, low_quality_data):
    """Total score is always within 0–100 for any fixture."""
    inv = DorseyInvestor()
    for data in (dorsey_ideal_data, low_quality_data):
        result = inv.score(data)
        assert 0 <= result.total_score <= 100


def test_dorsey_verdict_consistency(dorsey_ideal_data, low_quality_data):
    """Verdict matches score thresholds for all fixtures."""
    inv = DorseyInvestor()
    for data in (dorsey_ideal_data, low_quality_data):
        result = inv.score(data)
        score = result.total_score
        if score >= 75:
            assert result.verdict == "Strong Buy"
        elif score >= 55:
            assert result.verdict == "Buy"
        elif score >= 40:
            assert result.verdict == "Hold"
        else:
            assert result.verdict == "Avoid"


def test_dorsey_rules_sum_to_100(dorsey_ideal_data):
    """Points possible across all rules sums to exactly 100."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    total_possible = sum(
        r.points_possible for r in result.rules_passed + result.rules_failed
    )
    assert total_possible == 100.0, f"Expected 100 pts possible, got {total_possible}"


def test_dorsey_rules_count(dorsey_ideal_data):
    """There should be exactly 6 rules."""
    inv = DorseyInvestor()
    result = inv.score(dorsey_ideal_data)
    total_rules = len(result.rules_passed) + len(result.rules_failed)
    assert total_rules == 6, f"Expected 6 rules, got {total_rules}"
