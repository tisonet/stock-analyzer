"""
Unit tests for MoatInvestor — GuruFocus-inspired economic moat scoring engine.

Test coverage:
- Wide Moat company (MSCI-like): all 9 criteria pass → score >= 75
- No Moat company (low_quality_data): most criteria fail → score < 40
- Rule count: exactly 9 rules regardless of data quality
- Points total: 100 points possible across all 9 criteria
- Pricing power erosion detection: red_flag fires when GM drops > 3pp
- Score bounds: 0 <= total_score <= 100
- Crash safety: empty DataFrames return score == 0, no exception
- Sector calibration: Utilities sector auto-passes regulatory barriers
- R&D intensity: high R&D software company passes IP criterion
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.backend.data.fetcher import FinancialData
from src.backend.investors.moat import MoatInvestor
from tests.conftest import (
    _make_balance_sheet,
    _make_cashflow,
    _make_history,
    _make_income_stmt,
)


# ── Moat-specific fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def compounding_machine_data() -> FinancialData:
    """
    MSCI-like company: Financial Services (regulated), ~80% GM, ~37% ROIC,
    ~10% revenue CAGR, ~11% EPS CAGR.
    Expected: all 9 criteria pass → score = 100 → Wide Moat.
    """
    # Newest → oldest (yfinance order); _series() reverses to oldest → newest
    revs     = [14e9, 12.7e9, 11.5e9, 10.5e9, 9.5e9, 8.6e9, 7.8e9, 7.1e9, 6.4e9, 5.8e9]
    op_incs  = [ 5.6e9,  5.1e9,  4.6e9,  4.2e9, 3.8e9, 3.4e9, 3.1e9, 2.8e9, 2.5e9, 2.3e9]
    net_incs = [ 4.0e9,  3.6e9,  3.3e9,  3.0e9, 2.7e9, 2.4e9, 2.2e9, 2.0e9, 1.8e9, 1.6e9]
    gp       = [11.2e9, 10.2e9,  9.2e9,  8.4e9, 7.6e9, 6.9e9, 6.2e9, 5.7e9, 5.1e9, 4.6e9]
    epss     = [35.0, 31.5, 28.3, 25.5, 22.9, 20.6, 18.6, 16.7, 15.0, 13.5]

    income = _make_income_stmt(revs, op_incs, net_incs, gp, epss)

    ta   = [8.0e9, 7.5e9, 7.0e9, 6.5e9, 6.0e9]
    ca   = [2.0e9, 1.9e9, 1.8e9, 1.7e9, 1.6e9]
    cl   = [1.5e9, 1.4e9, 1.3e9, 1.2e9, 1.1e9]
    tl   = [5.5e9, 5.2e9, 4.9e9, 4.6e9, 4.3e9]
    eq   = [2.5e9, 2.3e9, 2.1e9, 1.9e9, 1.7e9]
    debt = [3.0e9, 2.8e9, 2.6e9, 2.4e9, 2.2e9]
    sh   = [80e6,  83e6,  86e6,  90e6,  94e6]

    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt, sh)
    cashflow = _make_cashflow(
        [5.5e9, 5.0e9, 4.5e9, 4.1e9, 3.7e9],
        [0.4e9, 0.35e9, 0.30e9, 0.27e9, 0.25e9],
    )
    prices  = list(range(100, 600, 2)) + list(range(600, 1200, 4))
    history = _make_history((prices * 3)[:2517])

    return FinancialData(
        ticker="MSCI",
        info={
            "trailingPE": 45.0,
            "priceToBook": 25.0,
            "debtToEquity": 120.0,
            "currentRatio": 1.3,
            "marketCap": 25e9,
            "currentPrice": 500.0,
            "sharesOutstanding": 50_000_000,
            "trailingEps": 35.0,
            "beta": 0.9,
            "sector": "Financial Services",
            "industry": "Financial Data & Stock Exchanges",
            "country": "United States",
            "longName": "MSCI Inc.",
            "earningsGrowth": 0.115,
            "revenueGrowth": 0.10,
            "returnOnEquity": 0.45,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


@pytest.fixture
def eroding_margin_data() -> FinancialData:
    """
    Company with gross margins declining ~5pp over 6 years — pricing power eroding.
    GM newest→oldest: [30%, 31.6%, 33.3%, 35.1%, 36.9%, 38.9%] (after reversal becomes ascending drop).
    Expected: Rule 8 (Pricing Power) fails and red_flag fires.
    """
    revs     = [10e9, 9.8e9, 9.6e9, 9.4e9, 9.2e9, 9.0e9]  # newest → oldest
    op_incs  = [ 2e9,  2.0e9, 2.0e9, 2.0e9, 2.0e9, 2.0e9]
    net_incs = [1.5e9, 1.5e9, 1.5e9, 1.5e9, 1.5e9, 1.5e9]
    gp       = [ 3.0e9, 3.1e9, 3.2e9, 3.3e9, 3.4e9, 3.5e9]  # newest=30%, oldest=38.9%

    income  = _make_income_stmt(revs, op_incs, net_incs, gp)

    ta   = [30e9, 29e9, 28e9, 27e9, 26e9]
    ca   = [ 8e9,  7.5e9, 7.0e9, 6.5e9, 6.0e9]
    cl   = [ 7e9,  6.5e9, 6.0e9, 5.5e9, 5.0e9]
    tl   = [18e9, 17e9, 16e9, 15e9, 14e9]
    eq   = [12e9, 12e9, 12e9, 12e9, 12e9]
    debt = [ 8e9,  8e9,  8e9,  8e9,  8e9]

    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow(
        [2.5e9, 2.4e9, 2.3e9, 2.2e9, 2.1e9],
        [2.5e9, 2.4e9, 2.3e9, 2.2e9, 2.1e9],  # CapEx = OCF → zero FCF
    )
    prices  = [100] * 2517
    history = _make_history(prices)

    return FinancialData(
        ticker="EMCO",
        info={
            "sector": "Industrials",
            "industry": "Industrial Machinery",
            "longName": "Eroding Margin Co",
            "earningsGrowth": 0.02,
            "revenueGrowth": 0.02,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


@pytest.fixture
def utility_data() -> FinancialData:
    """
    Regulated utility: sector = 'Utilities' → structural regulatory protection.
    Expected: Rule 6 (Regulatory Barriers) passes via sector classification.
    """
    revs     = [25e9, 24.5e9, 24.0e9, 23.5e9, 23.0e9, 22.5e9]
    op_incs  = [ 7.5e9, 7.35e9,  7.2e9,  7.05e9,  6.9e9,  6.75e9]  # ~30% op margin
    net_incs = [ 4.0e9,  3.9e9,  3.8e9,   3.7e9,  3.6e9,   3.5e9]
    gp       = [ 8.5e9,  8.3e9,  8.1e9,   7.9e9,  7.7e9,   7.5e9]  # ~34% GM

    income  = _make_income_stmt(revs, op_incs, net_incs, gp)

    ta   = [80e9, 78e9, 76e9, 74e9, 72e9]
    ca   = [ 5e9,  5e9,  5e9,  5e9,  5e9]
    cl   = [ 8e9,  8e9,  8e9,  8e9,  8e9]
    tl   = [55e9, 54e9, 53e9, 52e9, 51e9]
    eq   = [25e9, 24e9, 23e9, 22e9, 21e9]
    debt = [45e9, 44e9, 43e9, 42e9, 41e9]

    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow(
        [7e9, 6.8e9, 6.6e9, 6.4e9, 6.2e9],
        [5e9, 4.9e9, 4.8e9, 4.7e9, 4.6e9],
    )
    prices  = [50] * 2517
    history = _make_history(prices)

    return FinancialData(
        ticker="UTIL",
        info={
            "sector": "Utilities",
            "industry": "Electric Utilities",
            "longName": "Utility Corp",
            "earningsGrowth": 0.03,
            "revenueGrowth": 0.02,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


@pytest.fixture
def high_rd_data() -> FinancialData:
    """
    Software company: R&D = 20% of revenue, ROIC ~33%, 65% gross margins.
    Expected: Rule 3 (Intellectual Property) passes via R&D + ROIC.
    """
    revs     = [60e9, 55e9, 50e9, 45e9, 41e9, 37e9]
    op_incs  = [15e9, 13.75e9, 12.5e9, 11.25e9, 10.25e9, 9.25e9]  # ~25% op margin
    net_incs = [12e9,   11e9,   10e9,    9e9,    8.2e9,   7.4e9]
    gp       = [39e9, 35.75e9, 32.5e9, 29.25e9, 26.65e9, 24.05e9]  # 65% GM

    income = _make_income_stmt(revs, op_incs, net_incs, gp)
    # Inject R&D row at 20% of revenue (newest → oldest, matching column order)
    income.loc["Research And Development"] = [0.20 * r for r in revs]

    ta   = [46e9, 42e9, 38e9, 35e9, 32e9]
    ca   = [15e9, 14e9, 13e9, 12e9, 11e9]
    cl   = [15e9, 14e9, 13e9, 12e9, 11e9]
    tl   = [30e9, 28e9, 26e9, 24e9, 22e9]
    eq   = [16e9, 14e9, 12e9, 11e9, 10e9]
    debt = [14e9, 13e9, 12e9, 11e9, 10e9]

    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt)
    cashflow = _make_cashflow(
        [14e9, 12.8e9, 11.5e9, 10.3e9, 9.3e9],
        [ 2e9,  1.8e9,  1.6e9,  1.4e9, 1.3e9],
    )
    prices  = list(range(100, 400)) + list(range(400, 100, -1)) + list(range(100, 400))
    history = _make_history((prices * 3)[:2517])

    return FinancialData(
        ticker="SRFT",
        info={
            "trailingPE": 35.0,
            "priceToBook": 8.0,
            "debtToEquity": 88.0,
            "currentRatio": 1.0,
            "marketCap": 300e9,
            "currentPrice": 300.0,
            "sharesOutstanding": 1_000_000_000,
            "trailingEps": 12.0,
            "beta": 1.1,
            "sector": "Technology",
            "industry": "Software",
            "country": "United States",
            "longName": "Software R&T Co",
            "earningsGrowth": 0.12,
            "revenueGrowth": 0.10,
            "returnOnEquity": 0.30,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_moat_wide_moat_company(compounding_machine_data: FinancialData) -> None:
    """MSCI-like: 80% GM, 37% ROIC, 10% rev CAGR → all 9 criteria pass → Wide Moat."""
    result = MoatInvestor().score(compounding_machine_data)
    assert result.total_score >= 75, (
        f"Expected Wide Moat (>=75) but got {result.total_score:.1f}. "
        f"Failed rules: {[r.name for r in result.rules_failed]}"
    )
    assert result.verdict == "Wide Moat"


def test_moat_no_moat_company(low_quality_data: FinancialData) -> None:
    """Distressed company: negative margins, high CapEx, declining EPS → No Moat (<40)."""
    result = MoatInvestor().score(low_quality_data)
    assert result.total_score < 40, (
        f"Expected No Moat (<40) but got {result.total_score:.1f}. "
        f"Passed rules: {[r.name for r in result.rules_passed]}"
    )
    assert result.verdict == "No Moat"


def test_moat_score_has_9_rules(compounding_machine_data: FinancialData) -> None:
    """MoatInvestor must produce exactly 9 rules regardless of outcome."""
    result = MoatInvestor().score(compounding_machine_data)
    all_rules = result.rules_passed + result.rules_failed
    assert len(all_rules) == 9, (
        f"Expected 9 rules, got {len(all_rules)}: {[r.name for r in all_rules]}"
    )


def test_moat_total_possible_100(compounding_machine_data: FinancialData) -> None:
    """Sum of points_possible across all 9 rules must equal 100."""
    result = MoatInvestor().score(compounding_machine_data)
    all_rules = result.rules_passed + result.rules_failed
    total_possible = sum(r.points_possible for r in all_rules)
    assert total_possible == 100.0, f"Expected 100 total possible pts, got {total_possible}"


def test_pricing_power_detects_erosion(eroding_margin_data: FinancialData) -> None:
    """Gross margin declining ~5pp over 6yr must fail Rule 8 and trigger a red_flag."""
    result = MoatInvestor().score(eroding_margin_data)

    pricing_rule = next(
        (r for r in result.rules_failed if "Pricing" in r.name), None
    )
    assert pricing_rule is not None, (
        "Pricing Power rule should be in rules_failed for eroding margins. "
        f"Passed rules: {[r.name for r in result.rules_passed]}"
    )
    assert not pricing_rule.passed

    assert any("eroding" in f.lower() for f in result.red_flags), (
        f"Expected 'eroding' in a red_flag, got: {result.red_flags}"
    )


def test_moat_score_bounds(compounding_machine_data: FinancialData) -> None:
    """total_score must always be in [0, 100]."""
    result = MoatInvestor().score(compounding_machine_data)
    assert 0 <= result.total_score <= 100


def test_moat_no_crash_on_empty_data(empty_data: FinancialData) -> None:
    """Empty DataFrames must not raise — returns score=0 gracefully."""
    result = MoatInvestor().score(empty_data)
    assert result is not None
    assert result.total_score == 0
    assert len(result.rules_passed) == 0
    assert len(result.rules_failed) == 9  # all 9 rules exist but all failed


def test_sector_calibration_utility(utility_data: FinancialData) -> None:
    """Sector='Utilities' (regulated) must pass Rule 6 via structural protection."""
    result = MoatInvestor().score(utility_data)
    reg_rule = next(
        (r for r in result.rules_passed if "Regulatory" in r.name), None
    )
    assert reg_rule is not None, (
        "Regulatory Barriers rule should be in rules_passed for Utilities sector. "
        f"Passed: {[r.name for r in result.rules_passed]}"
    )


def test_rd_intensity_software(high_rd_data: FinancialData) -> None:
    """Software company with 20% R&D/revenue and 33% ROIC must pass the IP rule."""
    result = MoatInvestor().score(high_rd_data)
    ip_rule = next(
        (r for r in result.rules_passed if "Intellectual" in r.name), None
    )
    assert ip_rule is not None, (
        "Intellectual Property rule should be in rules_passed for R&D=20% company. "
        f"Passed: {[r.name for r in result.rules_passed]}"
    )


def test_moat_investor_name() -> None:
    """MoatInvestor.name must be exactly 'Moat Score' for engine/aggregator lookup."""
    assert MoatInvestor().name == "Moat Score"
