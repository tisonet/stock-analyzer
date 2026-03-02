"""
Unit tests for Dev Kantesaria / Valley Forge Capital Management scoring module.

Test philosophy mirrors the real scoring: the six rules are:
  1. ROIC > 20% every year (25 pts)
  2. Gross margin > 50% (20 pts)
  3. CapEx / Revenue < 5% (15 pts)
  4. FCF margin > 20% (15 pts)
  5. Revenue CAGR > 8% (15 pts)
  6. Revenue growth stdev < 10% (10 pts)
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.backend.data.fetcher import FinancialData
from src.backend.investors.kantesaria import KantesariaInvestor
from tests.conftest import (
    _make_balance_sheet,
    _make_cashflow,
    _make_history,
    _make_income_stmt,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: MSCI/FICO-like "compounding machine" fixture
# All 6 rules should pass → Strong Buy
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def compounding_machine_data() -> FinancialData:
    """
    MSCI/FICO-like compounder:
      - Revenue: ~$2B → $5B over 9 years, CAGR ≈ 10.7%, stdev ≈ 2%
      - Gross margin: ~80% (index licensing / score royalties, near-zero COGS)
      - CapEx: ~1% of revenue (pure software/data; no factories)
      - FCF margin: ~35% (moat + capital-light = cash machine)
      - ROIC: ~28% consistently every year
    """
    # Revenues grow steadily ~10-11% each year (low variance).
    # List is NEWEST FIRST to match _make_income_stmt convention (2023→2014).
    revs = [
        4_730e6, 4_300e6, 3_910e6, 3_560e6, 3_240e6,
        2_950e6, 2_680e6, 2_430e6, 2_200e6, 2_000e6,
    ]
    # Gross profit: 80% of revenue
    gp   = [r * 0.80 for r in revs]
    # Operating income: 38% of revenue (high-margin data/software)
    op   = [r * 0.38 for r in revs]
    # Net income: 28% of revenue
    ni   = [r * 0.28 for r in revs]
    # Tax provision: ~21% effective rate, derived from pretax ~= op * 1.05
    tax  = [o * 1.05 * 0.21 for o in op]

    income = _make_income_stmt(revs, op, ni, gp, epss=None, tax_provisions=tax)

    # Balance sheet: light on assets (software business), low debt
    ta   = [3_500e6, 3_800e6, 4_100e6, 4_450e6, 4_850e6]
    ca   = [1_200e6, 1_300e6, 1_400e6, 1_500e6, 1_650e6]
    cl   =   [400e6,   430e6,   460e6,   490e6,   530e6]
    tl   = [1_500e6, 1_600e6, 1_700e6, 1_800e6, 1_950e6]
    eq   = [2_000e6, 2_200e6, 2_400e6, 2_650e6, 2_900e6]
    debt =   [500e6,   520e6,   540e6,   560e6,   580e6]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt)

    # Cash flow: OCF ≈ 38% of revenue, CapEx ≈ 1% of revenue.
    # Use newest 5 years (revs[0:5]), already in newest-first order.
    ocf  = [r * 0.38 for r in revs[:5]]
    capx = [r * 0.01 for r in revs[:5]]
    cashflow = _make_cashflow(ocf, capx)

    # Steady price appreciation
    prices = [100 + i * 0.15 for i in range(2517)]
    history = _make_history(prices)

    return FinancialData(
        ticker="CMCO",
        info={
            "trailingPE": 35.0,
            "priceToBook": 12.0,
            "debtToEquity": 25.0,   # 0.25x
            "currentRatio": 3.0,
            "marketCap": 20_000e6,
            "currentPrice": 200.0,
            "sharesOutstanding": 100_000_000,
            "dividendYield": 0.005,
            "trailingEps": 13.3,
            "bookValue": 20.0,
            "beta": 0.85,
            "sector": "Financial Services",
            "industry": "Financial Data & Analytics",
            "country": "United States",
            "longName": "Compounding Machine Corp",
            "longBusinessSummary": (
                "Provides mission-critical data and analytics with recurring subscription "
                "revenue, deep client integration, and network effects. Customers face "
                "significant switching costs and multi-year contracts."
            ),
            "revenueGrowth": 0.10,
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

def test_kantesaria_compounding_machine_strong_buy(compounding_machine_data):
    """MSCI/FICO-like compounder should score 75+ → Strong Buy."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    assert result.total_score >= 75, (
        f"Expected >= 75 for a compounding machine (MSCI/FICO archetype), "
        f"got {result.total_score:.1f}"
    )
    assert result.verdict == "Strong Buy"


def test_kantesaria_low_quality_scores_poorly(low_quality_data):
    """Highly leveraged, capex-heavy, low-margin company → Avoid."""
    inv = KantesariaInvestor()
    result = inv.score(low_quality_data)
    assert result.total_score <= 30, (
        f"Expected <= 30 for low quality company, got {result.total_score:.1f}"
    )
    assert result.verdict == "Avoid"


def test_kantesaria_high_quality_data_scores_mid_range(high_quality_data):
    """AAPL-like fixture (ROIC ~31%, GM ~45%) passes 5/6 rules → Strong Buy range."""
    inv = KantesariaInvestor()
    result = inv.score(high_quality_data)
    # Passes: ROIC (31% > 20%), capital-light, FCF margin, revenue CAGR, revenue predictability
    # Fails:  gross margin < 50%  (only rule that misses)
    assert 75 <= result.total_score <= 100, (
        f"Expected 75-100 for AAPL-like company (5/6 rules pass), got {result.total_score:.1f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual rule tests
# ─────────────────────────────────────────────────────────────────────────────

def test_kantesaria_roic_rule_passes(compounding_machine_data):
    """ROIC consistently above 20% should pass Rule 1."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    roic_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "ROIC" in r.name), None
    )
    assert roic_rule is not None, "ROIC rule must be present"
    assert roic_rule.passed, (
        f"ROIC avg = {roic_rule.value:.1f}% should exceed 20% threshold"
    )
    assert roic_rule.value >= 20.0


def test_kantesaria_roic_rule_fails_below_20():
    """Capital-intensive company with low op margins → ROIC ~5% fails the 20% threshold."""
    # Low-margin, asset-heavy business: op income 6% of revenue, large IC
    revs    = [50e9] * 10
    op_incs = [ 3e9] * 10   # 6% op margin
    ni      = [ 2e9] * 10
    gp      = [20e9] * 10
    income = _make_income_stmt(revs, op_incs, ni, gp)

    # Large equity + debt relative to earnings → IC big → ROIC ~5%
    ta   = [70e9] * 5
    ca   = [10e9] * 5
    cl   = [ 8e9] * 5
    tl   = [40e9] * 5
    eq   = [30e9] * 5
    debt = [20e9] * 5   # "Long Term Debt" alias added by _make_balance_sheet
    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([4e9] * 5, [2e9] * 5)

    data = FinancialData(
        ticker="LRCO",
        info={"marketCap": 30e9, "longName": "Low Return Corp"},
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=_make_history([100] * 2517),
    )

    inv = KantesariaInvestor()
    result = inv.score(data)
    roic_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "ROIC" in r.name), None
    )
    assert roic_rule is not None
    assert not roic_rule.passed, (
        f"ROIC of {roic_rule.value:.1f}% should fail Kantesaria's 20% threshold"
    )
    assert roic_rule.value < 20.0


def test_kantesaria_roic_inconsistency_rejected():
    """A company with one negative ROIC year must fail even with a high average."""
    revs     = [10e9] * 5
    op_incs  = [3e9, 3e9, -0.5e9, 3e9, 3e9]   # one bad year drives ROIC negative
    net_incs = [2e9, 2e9, -0.3e9, 2e9, 2e9]
    gp       = [7e9] * 5
    income = _make_income_stmt(revs, op_incs, net_incs, gp)

    ta   = [15e9] * 5
    ca   = [4e9] * 5
    cl   = [1e9] * 5
    tl   = [6e9] * 5
    eq   = [9e9] * 5
    debt = [2e9] * 5
    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([2.5e9] * 5, [0.1e9] * 5)

    data = FinancialData(
        ticker="VARI",
        info={"debtToEquity": 22.0, "marketCap": 20e9, "longName": "Variable ROIC Inc"},
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=_make_history([100] * 2517),
    )

    inv = KantesariaInvestor()
    result = inv.score(data)
    roic_rule = next(
        (r for r in result.rules_failed if "ROIC" in r.name), None
    )
    assert roic_rule is not None, (
        "Company with negative ROIC in one year must fail the sustained ROIC rule"
    )


def test_kantesaria_gross_margin_rule_passes(compounding_machine_data):
    """80% gross margin should pass Rule 2 (>50%)."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    gm_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Gross Margin" in r.name), None
    )
    assert gm_rule is not None, "Gross Margin rule must be present"
    assert gm_rule.passed, (
        f"Gross margin = {gm_rule.value:.1f}% should exceed 50%"
    )


def test_kantesaria_gross_margin_rule_fails_below_50(high_quality_data):
    """AAPL-like ~45% gross margin fails Kantesaria's stricter 50% bar."""
    inv = KantesariaInvestor()
    result = inv.score(high_quality_data)
    gm_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Gross Margin" in r.name), None
    )
    assert gm_rule is not None
    # high_quality_data has ~45% GM — passes AKO (>40%) but fails Kantesaria (>50%)
    assert not gm_rule.passed, (
        f"Gross margin of {gm_rule.value:.1f}% should fail Kantesaria's 50% threshold"
    )


def test_kantesaria_capital_light_rule_passes(compounding_machine_data):
    """~1% CapEx/Revenue should pass Rule 3 (<5%)."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    capex_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Capital-Light" in r.name), None
    )
    assert capex_rule is not None, "Capital-Light rule must be present"
    assert capex_rule.passed, (
        f"CapEx/Revenue = {capex_rule.value:.1f}% should be below 5%"
    )
    assert capex_rule.value < 5.0


def test_kantesaria_fcf_margin_rule_passes(compounding_machine_data):
    """~37% FCF margin should pass Rule 4 (>20%)."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    fcf_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "FCF Margin" in r.name), None
    )
    assert fcf_rule is not None, "FCF Margin rule must be present"
    assert fcf_rule.passed, (
        f"FCF margin = {fcf_rule.value:.1f}% should exceed 20%"
    )


def test_kantesaria_revenue_cagr_rule_passes(compounding_machine_data):
    """~10.7% revenue CAGR should pass Rule 5 (>8%)."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    cagr_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "CAGR" in r.name), None
    )
    assert cagr_rule is not None, "Revenue CAGR rule must be present"
    assert cagr_rule.passed, (
        f"Revenue CAGR = {cagr_rule.value:.1f}% should exceed 8%"
    )


def test_kantesaria_revenue_cagr_fails_slow_grower():
    """A slow-growing business (CAGR ~3%) fails the reinvestment runway rule."""
    revs     = [5e9, 5.1e9, 5.2e9, 5.3e9, 5.4e9, 5.5e9, 5.6e9, 5.7e9, 5.8e9, 5.9e9]
    op_incs  = [r * 0.25 for r in revs]
    net_incs = [r * 0.18 for r in revs]
    gp       = [r * 0.65 for r in revs]
    income = _make_income_stmt(revs, op_incs, net_incs, gp)

    ta   = [10e9] * 5
    ca   = [3e9] * 5
    cl   = [1e9] * 5
    tl   = [4e9] * 5
    eq   = [6e9] * 5
    debt = [1e9] * 5
    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow(
        [r * 0.25 for r in revs[-5:]],
        [r * 0.01 for r in revs[-5:]],
    )

    data = FinancialData(
        ticker="SLOW",
        info={"debtToEquity": 17.0, "marketCap": 50e9, "longName": "Slow Grower Inc"},
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=_make_history([100] * 2517),
    )

    inv = KantesariaInvestor()
    result = inv.score(data)
    cagr_rule = next(
        (r for r in result.rules_failed if "CAGR" in r.name), None
    )
    assert cagr_rule is not None, (
        "Slow-growing business should fail the Revenue CAGR > 8% rule"
    )
    assert cagr_rule.value < 8.0


def test_kantesaria_revenue_predictability_passes(compounding_machine_data):
    """~2% growth stdev should pass Rule 6 (<10%)."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    pred_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Predictability" in r.name), None
    )
    assert pred_rule is not None, "Revenue Predictability rule must be present"
    assert pred_rule.passed, (
        f"Revenue growth stdev = {pred_rule.value:.1f}% should be below 10%"
    )


def test_kantesaria_cyclical_revenue_fails_predictability():
    """Highly cyclical revenue (boom/bust) should fail the predictability rule."""
    # Revenue swings wildly — classic cyclical business
    revs = [5e9, 8e9, 3e9, 9e9, 4e9, 10e9, 3.5e9, 9.5e9, 4.5e9, 9e9]
    op_incs  = [r * 0.12 for r in revs]
    net_incs = [r * 0.08 for r in revs]
    gp       = [r * 0.55 for r in revs]
    income = _make_income_stmt(revs, op_incs, net_incs, gp)

    ta   = [20e9] * 5
    ca   = [6e9] * 5
    cl   = [2e9] * 5
    tl   = [9e9] * 5
    eq   = [11e9] * 5
    debt = [4e9] * 5
    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([r * 0.12 for r in revs[-5:]], [r * 0.02 for r in revs[-5:]])

    data = FinancialData(
        ticker="CYCL",
        info={"debtToEquity": 36.0, "marketCap": 30e9, "longName": "Cyclical Corp"},
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=_make_history([100] * 2517),
    )

    inv = KantesariaInvestor()
    result = inv.score(data)
    pred_rule = next(
        (r for r in result.rules_failed if "Predictability" in r.name), None
    )
    assert pred_rule is not None, (
        "Highly cyclical revenue should fail the predictability rule (stdev < 10%)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Robustness and consistency tests
# ─────────────────────────────────────────────────────────────────────────────

def test_kantesaria_score_bounds(compounding_machine_data, high_quality_data, low_quality_data, net_net_data):
    """Score must always be 0-100, verdict must always be valid, no crashes."""
    inv = KantesariaInvestor()
    for data in [compounding_machine_data, high_quality_data, low_quality_data, net_net_data]:
        result = inv.score(data)
        assert 0 <= result.total_score <= 100, (
            f"Score {result.total_score:.1f} out of bounds for {data.ticker}"
        )
        assert result.verdict in ("Strong Buy", "Buy", "Hold", "Avoid"), (
            f"Invalid verdict '{result.verdict}' for {data.ticker}"
        )


def test_kantesaria_verdict_matches_score(compounding_machine_data):
    """Verdict must be consistent with score thresholds."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    score = result.total_score
    if score >= 75:
        assert result.verdict == "Strong Buy"
    elif score >= 55:
        assert result.verdict == "Buy"
    elif score >= 40:
        assert result.verdict == "Hold"
    else:
        assert result.verdict == "Avoid"


def test_kantesaria_no_crash_empty_dataframes(high_quality_data):
    """Removing all financial statements must not crash the scorer."""
    high_quality_data.income_stmt = pd.DataFrame()
    high_quality_data.balance_sheet = pd.DataFrame()
    high_quality_data.cash_flow = pd.DataFrame()
    high_quality_data.info.pop("debtToEquity", None)

    inv = KantesariaInvestor()
    result = inv.score(high_quality_data)  # must not raise
    assert result.total_score >= 0
    assert result.total_score <= 100


def test_kantesaria_all_rules_present(compounding_machine_data):
    """All 6 rules must appear in the result, totalling 100 possible points."""
    inv = KantesariaInvestor()
    result = inv.score(compounding_machine_data)
    all_rules = result.rules_passed + result.rules_failed
    assert len(all_rules) == 6, f"Expected 6 rules, got {len(all_rules)}"
    total_possible = sum(r.points_possible for r in all_rules)
    assert total_possible == 100.0, (
        f"Total possible points should be 100, got {total_possible}"
    )


def test_kantesaria_investor_name():
    """Investor name must be 'Kantesaria'."""
    assert KantesariaInvestor().name == "Kantesaria"
