"""
Unit tests for Phil Fisher / Common Stocks and Uncommon Profits scoring module.

Test philosophy mirrors the real scoring: the seven rules are:
  1. Revenue Growth CAGR >= 10% (25 pts)
  2. R&D Commitment R&D/Revenue >= 5% (20 pts)
  3. Operating Margin Trend stable/improving (15 pts)
  4. Revenue Growth Consistency >= 75% of years (15 pts)
  5. Earnings Growth Alignment EPS CAGR >= 8% (10 pts)
  6. Low Share Dilution <= 2% total growth (10 pts)
  7. Long-term Price Appreciation positive return (5 pts)
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.backend.data.fetcher import FinancialData
from src.backend.investors.fisher import FisherInvestor
from tests.conftest import (
    _make_balance_sheet,
    _make_cashflow,
    _make_history,
    _make_income_stmt,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Fisher-ideal growth company fixture
# All 7 rules should pass → Strong Buy
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def growth_company_data() -> FinancialData:
    """
    Fisher-ideal growth company:
      - Revenue: ~$10B → $26B over 9 years, CAGR ≈ 11%
      - R&D: ~12% of revenue (strong innovation commitment)
      - Operating margin: improving from ~18% to ~22%
      - Revenue grows every year (100% consistency)
      - EPS CAGR ≈ 10%
      - Shares flat (no dilution)
      - Long-term price appreciation
    """
    # Newest-first to match _make_income_stmt convention
    revs = [
        26_000e6, 24_000e6, 22_000e6, 20_000e6, 18_000e6,
        16_000e6, 14_500e6, 13_000e6, 11_500e6, 10_000e6,
    ]
    # Operating margins improving: ~18% (oldest) → ~22% (newest)
    op_margins_pct = [0.22, 0.215, 0.21, 0.205, 0.20, 0.195, 0.19, 0.185, 0.18, 0.18]
    op_incs = [r * m for r, m in zip(revs, op_margins_pct)]
    # Net income ~14% of revenue
    ni = [r * 0.14 for r in revs]
    # Gross profit ~60% of revenue
    gp = [r * 0.60 for r in revs]
    # EPS growing at ~10% CAGR: 2.0 → 4.7 over 9 years
    epss = [4.70, 4.30, 3.90, 3.55, 3.20, 2.90, 2.65, 2.40, 2.20, 2.00]
    # Tax provision ~21% effective rate
    tax = [o * 1.2 * 0.21 for o in op_incs]
    # R&D at ~12% of revenue
    rnd = [r * 0.12 for r in revs]

    income = _make_income_stmt(revs, op_incs, ni, gp, epss, tax)
    # Inject R&D data into the income statement
    income.loc["Research And Development"] = income.loc["Total Revenue"] * 0.12

    # Balance sheet
    ta   = [30_000e6, 27_000e6, 24_000e6, 21_500e6, 19_000e6]
    ca   = [10_000e6,  9_000e6,  8_000e6,  7_200e6,  6_500e6]
    cl   = [ 4_000e6,  3_600e6,  3_200e6,  2_900e6,  2_600e6]
    tl   = [12_000e6, 10_800e6,  9_600e6,  8_600e6,  7_600e6]
    eq   = [18_000e6, 16_200e6, 14_400e6, 12_900e6, 11_400e6]
    debt = [ 4_000e6,  3_600e6,  3_200e6,  2_900e6,  2_600e6]
    # Flat shares — no dilution
    shares = [1_000e6, 1_000e6, 1_000e6, 1_000e6, 1_000e6]
    cash = [3_000e6, 2_700e6, 2_400e6, 2_100e6, 1_900e6]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, shares, cash)

    # Cash flow
    ocf  = [r * 0.20 for r in revs[:5]]
    capx = [r * 0.03 for r in revs[:5]]
    cashflow = _make_cashflow(ocf, capx)

    # Steady price appreciation over ~10 years
    prices = [50 + i * 0.10 for i in range(2517)]
    history = _make_history(prices)

    return FinancialData(
        ticker="GRCO",
        info={
            "trailingPE": 30.0,
            "priceToBook": 8.0,
            "debtToEquity": 22.0,
            "currentRatio": 2.5,
            "marketCap": 100_000e6,
            "currentPrice": 300.0,
            "sharesOutstanding": 1_000_000_000,
            "dividendYield": 0.005,
            "trailingEps": 4.70,
            "bookValue": 18.0,
            "beta": 1.0,
            "sector": "Technology",
            "industry": "Software — Application",
            "country": "United States",
            "longName": "Growth Company Corp",
            "longBusinessSummary": (
                "A leading software company investing heavily in R&D, "
                "delivering consistent revenue growth with improving margins."
            ),
            "revenueGrowth": 0.11,
            "earningsGrowth": 0.10,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core verdict tests
# ─────────────────────────────────────────────────────────────────────────────

def test_fisher_growth_company_strong_buy(growth_company_data):
    """Fisher-ideal growth company should score 75+ → Strong Buy."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    assert result.total_score >= 75, (
        f"Expected >= 75 for Fisher-ideal growth company, "
        f"got {result.total_score:.1f}"
    )
    assert result.verdict == "Strong Buy"


def test_fisher_low_quality_scores_poorly(low_quality_data):
    """Leveraged, declining company → Avoid."""
    inv = FisherInvestor()
    result = inv.score(low_quality_data)
    assert result.total_score < 40, (
        f"Expected < 40 for low quality company, got {result.total_score:.1f}"
    )
    assert result.verdict == "Avoid"


def test_fisher_high_quality_data_moderate(high_quality_data):
    """
    AAPL-like fixture: ~9% revenue CAGR (narrowly misses 10%), no R&D data
    but Technology sector (fails R&D rule), decent margins and EPS.
    Should score in the moderate range.
    """
    inv = FisherInvestor()
    result = inv.score(high_quality_data)
    # Passes: margin trend, consistency, EPS growth, dilution (buybacks), price
    # Fails: revenue CAGR (9% < 10%), R&D (tech sector with no R&D data)
    assert 30 <= result.total_score <= 70, (
        f"Expected 30-70 for AAPL-like company, got {result.total_score:.1f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual rule tests
# ─────────────────────────────────────────────────────────────────────────────

def test_fisher_revenue_growth_rule_passes(growth_company_data):
    """~11% revenue CAGR should pass Rule 1 (>= 10%)."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    rev_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Revenue Growth CAGR" in r.name), None
    )
    assert rev_rule is not None, "Revenue Growth CAGR rule must be present"
    assert rev_rule.passed, (
        f"Revenue CAGR = {rev_rule.value:.1f}% should exceed 10%"
    )
    assert rev_rule.value >= 10.0


def test_fisher_rd_rule_passes(growth_company_data):
    """~12% R&D/Revenue should pass Rule 2 (>= 5%)."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    rd_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "R&D" in r.name), None
    )
    assert rd_rule is not None, "R&D Commitment rule must be present"
    assert rd_rule.passed, (
        f"R&D/Revenue = {rd_rule.value:.1f}% should exceed 5%"
    )


def test_fisher_rd_rule_neutral_for_non_rd_sectors():
    """Financial Services company with no R&D data should get a neutral pass."""
    revs = [10e9] * 5
    op_incs = [r * 0.20 for r in revs]
    ni = [r * 0.12 for r in revs]
    gp = [r * 0.50 for r in revs]
    income = _make_income_stmt(revs, op_incs, ni, gp)
    # No R&D row in income statement

    ta = [50e9] * 5
    ca = [20e9] * 5
    cl = [10e9] * 5
    tl = [30e9] * 5
    eq = [20e9] * 5
    debt = [10e9] * 5
    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow([r * 0.15 for r in revs], [r * 0.02 for r in revs])

    data = FinancialData(
        ticker="BANK",
        info={
            "sector": "Financial Services",
            "industry": "Banks",
            "longName": "Big Bank Corp",
            "marketCap": 80e9,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=_make_history([100] * 2517),
    )

    inv = FisherInvestor()
    result = inv.score(data)
    rd_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "R&D" in r.name), None
    )
    assert rd_rule is not None, "R&D rule must be present"
    assert rd_rule.passed, (
        "Financial Services company should get neutral pass on R&D rule"
    )


def test_fisher_rd_rule_fails_tech_without_rd(high_quality_data):
    """Technology company with no R&D data should fail the R&D rule."""
    inv = FisherInvestor()
    result = inv.score(high_quality_data)
    rd_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "R&D" in r.name), None
    )
    assert rd_rule is not None, "R&D rule must be present"
    assert not rd_rule.passed, (
        "Technology company with no R&D data should fail the R&D rule"
    )


def test_fisher_margin_trend_passes(growth_company_data):
    """Improving margins should pass Rule 3."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    margin_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Margin Trend" in r.name), None
    )
    assert margin_rule is not None, "Operating Margin Trend rule must be present"
    assert margin_rule.passed, (
        f"Improving margins (Δ{margin_rule.value:+.1f}pp) should pass"
    )


def test_fisher_consistency_rule_passes(growth_company_data):
    """Revenue growing every year (100%) should pass Rule 4 (>= 75%)."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    cons_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Consistency" in r.name), None
    )
    assert cons_rule is not None, "Revenue Growth Consistency rule must be present"
    assert cons_rule.passed, (
        f"Consistency = {cons_rule.value:.0f}% should exceed 75%"
    )


def test_fisher_eps_growth_rule_passes(growth_company_data):
    """~10% EPS CAGR should pass Rule 5 (>= 8%)."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    eps_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Earnings Growth" in r.name), None
    )
    assert eps_rule is not None, "Earnings Growth Alignment rule must be present"
    assert eps_rule.passed, (
        f"EPS CAGR = {eps_rule.value:.1f}% should exceed 8%"
    )


def test_fisher_dilution_rule_passes(growth_company_data):
    """Flat shares should pass Rule 6 (<= 2%)."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    dilution_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Dilution" in r.name), None
    )
    assert dilution_rule is not None, "Low Share Dilution rule must be present"
    assert dilution_rule.passed, (
        f"Shares change = {dilution_rule.value:+.1f}% should be <= 2%"
    )


def test_fisher_dilution_rule_fails_on_diluted_company(low_quality_data):
    """Low quality data has increasing shares (dilution) — should fail."""
    inv = FisherInvestor()
    result = inv.score(low_quality_data)
    dilution_rule = next(
        (r for r in result.rules_passed + result.rules_failed
         if "Dilution" in r.name), None
    )
    assert dilution_rule is not None, "Low Share Dilution rule must be present"
    assert not dilution_rule.passed, (
        f"Diluted company ({dilution_rule.value:+.1f}%) should fail dilution rule"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Robustness and consistency tests
# ─────────────────────────────────────────────────────────────────────────────

def test_fisher_score_bounds(growth_company_data, high_quality_data, low_quality_data, net_net_data):
    """Score must always be 0-100, verdict must always be valid."""
    inv = FisherInvestor()
    for data in [growth_company_data, high_quality_data, low_quality_data, net_net_data]:
        result = inv.score(data)
        assert 0 <= result.total_score <= 100, (
            f"Score {result.total_score:.1f} out of bounds for {data.ticker}"
        )
        assert result.verdict in ("Strong Buy", "Buy", "Hold", "Avoid"), (
            f"Invalid verdict '{result.verdict}' for {data.ticker}"
        )


def test_fisher_no_crash_empty_dataframes(empty_data):
    """Empty DataFrames must not crash the scorer."""
    inv = FisherInvestor()
    result = inv.score(empty_data)
    assert result.total_score >= 0
    assert result.total_score <= 100


def test_fisher_no_crash_missing_statements(high_quality_data):
    """Removing all financial statements must not crash the scorer."""
    high_quality_data.income_stmt = pd.DataFrame()
    high_quality_data.balance_sheet = pd.DataFrame()
    high_quality_data.cash_flow = pd.DataFrame()

    inv = FisherInvestor()
    result = inv.score(high_quality_data)
    assert result.total_score >= 0
    assert result.total_score <= 100


def test_fisher_all_rules_present(growth_company_data):
    """All 7 rules must appear in the result, totalling 100 possible points."""
    inv = FisherInvestor()
    result = inv.score(growth_company_data)
    all_rules = result.rules_passed + result.rules_failed
    assert len(all_rules) == 7, f"Expected 7 rules, got {len(all_rules)}"
    total_possible = sum(r.points_possible for r in all_rules)
    assert total_possible == 100.0, (
        f"Total possible points should be 100, got {total_possible}"
    )


def test_fisher_investor_name():
    """Investor name must be 'Fisher'."""
    assert FisherInvestor().name == "Fisher"
