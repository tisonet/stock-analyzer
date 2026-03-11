"""Tests for the Druckenmiller macro growth investor module."""
from __future__ import annotations

import pytest

from src.backend.data.fetcher import FinancialData
from src.backend.investors.druckenmiller import DruckenmillerInvestor
from tests.conftest import (
    _make_income_stmt,
    _make_balance_sheet,
    _make_cashflow,
    _make_history,
)

inv = DruckenmillerInvestor()


# ─────────────────────────────────────────────────────────────────────────────
# Custom fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def nvidia_clone() -> FinancialData:
    """NVDA-like: accelerating earnings, expanding margins, strong momentum."""
    # Revenue growing ~28% CAGR (newest first for 5 years)
    revs = [60e9, 48e9, 37e9, 28e9, 22e9]
    op_incs = [21e9, 15e9, 10e9, 6.5e9, 4.5e9]
    net_incs = [16e9, 11e9, 7e9, 4e9, 2.5e9]
    gp = [42e9, 33e9, 24e9, 17e9, 13e9]
    epss = [6.5, 4.0, 2.5, 1.8, 1.5]

    income = _make_income_stmt(revs, op_incs, net_incs, gp, epss,
                               [o * 0.12 for o in op_incs])

    ta = [50e9, 40e9, 32e9, 26e9, 22e9]
    ca = [25e9, 20e9, 16e9, 13e9, 11e9]
    cl = [8e9, 7e9, 6e9, 5e9, 4e9]
    tl = [20e9, 17e9, 14e9, 12e9, 10e9]
    eq = [30e9, 23e9, 18e9, 14e9, 12e9]
    debt = [10e9, 9e9, 8e9, 7e9, 6e9]
    sh = [2.5e9, 2.5e9, 2.5e9, 2.5e9, 2.5e9]
    cash = [8e9, 6e9, 5e9, 4e9, 3e9]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, sh, cash)
    cashflow = _make_cashflow(
        [18e9, 13e9, 9e9, 6e9, 4e9],
        [2e9, 1.5e9, 1.2e9, 1e9, 0.8e9],
    )
    # Strong uptrend: 50 → ~500
    prices = [int(50 + i * 0.18) for i in range(2517)]
    history = _make_history(prices)

    return FinancialData(
        ticker="NVGR",
        info={
            "trailingPE": 35.0,
            "priceToBook": 15.0,
            "debtToEquity": 33.0,
            "currentRatio": 3.1,
            "marketCap": 1500e9,
            "currentPrice": 600.0,
            "sharesOutstanding": 2_500_000_000,
            "dividendYield": 0.001,
            "trailingEps": 6.5,
            "bookValue": 12.0,
            "pegRatio": 1.2,
            "heldPercentInsiders": 0.04,
            "beta": 1.6,
            "sector": "Technology",
            "industry": "Semiconductors",
            "country": "United States",
            "longName": "Growth Accelerator Corp",
            "longBusinessSummary": "Leading AI chip company with dominant market position.",
            "revenueGrowth": 0.25,
            "earningsGrowth": 0.35,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


@pytest.fixture
def utility_stagnant() -> FinancialData:
    """Utility-like: no growth, flat margins, expensive PEG — Druckenmiller Avoid."""
    revs = [20e9] * 5
    op_incs = [3.5e9] * 5
    net_incs = [2e9] * 5
    gp = [8e9] * 5
    epss = [4.0] * 5

    income = _make_income_stmt(revs, op_incs, net_incs, gp, epss,
                               [o * 0.20 for o in op_incs])

    ta = [80e9, 78e9, 76e9, 74e9, 72e9]
    ca = [10e9, 9.5e9, 9e9, 8.5e9, 8e9]
    cl = [12e9, 11.5e9, 11e9, 10.5e9, 10e9]
    tl = [50e9, 49e9, 48e9, 47e9, 46e9]
    eq = [30e9, 29e9, 28e9, 27e9, 26e9]
    debt = [40e9, 39e9, 38e9, 37e9, 36e9]
    sh = [500e6] * 5
    cash = [3e9] * 5

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, sh, cash)
    cashflow = _make_cashflow(
        [4e9] * 5,
        [2.5e9] * 5,
    )
    # Slowly declining prices
    prices = [int(55 - i * 0.002) for i in range(2517)]
    history = _make_history(prices)

    return FinancialData(
        ticker="UTIL",
        info={
            "trailingPE": 18.0,
            "priceToBook": 1.5,
            "debtToEquity": 133.0,
            "currentRatio": 0.83,
            "marketCap": 25e9,
            "currentPrice": 50.0,
            "sharesOutstanding": 500_000_000,
            "dividendYield": 0.04,
            "trailingEps": 4.0,
            "bookValue": 60.0,
            "pegRatio": 3.5,
            "heldPercentInsiders": 0.01,
            "beta": 0.5,
            "sector": "Utilities",
            "industry": "Utilities - Regulated Electric",
            "country": "United States",
            "longName": "Steady Utility Corp",
            "longBusinessSummary": "Regulated electric utility serving the Midwest.",
            "revenueGrowth": 0.01,
            "earningsGrowth": 0.02,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Basic property tests
# ─────────────────────────────────────────────────────────────────────────────

def test_druckenmiller_name():
    assert inv.name == "Druckenmiller"


def test_druckenmiller_rules_count_is_10(nvidia_clone):
    result = inv.score(nvidia_clone)
    total_rules = len(result.rules_passed) + len(result.rules_failed)
    assert total_rules == 10


# ─────────────────────────────────────────────────────────────────────────────
# Score bounds and verdict validity
# ─────────────────────────────────────────────────────────────────────────────

def test_druckenmiller_score_bounded_0_100(nvidia_clone, utility_stagnant):
    for data in [nvidia_clone, utility_stagnant]:
        result = inv.score(data)
        assert 0.0 <= result.total_score <= 100.0


def test_druckenmiller_verdict_valid(nvidia_clone, utility_stagnant):
    for data in [nvidia_clone, utility_stagnant]:
        result = inv.score(data)
        assert result.verdict in ("Strong Buy", "Buy", "Hold", "Avoid")


# ─────────────────────────────────────────────────────────────────────────────
# Archetype scoring
# ─────────────────────────────────────────────────────────────────────────────

def test_druckenmiller_nvidia_scores_high(nvidia_clone):
    result = inv.score(nvidia_clone)
    assert result.total_score >= 70, (
        f"High-growth accelerating company should score ≥70, got {result.total_score}"
    )


def test_druckenmiller_utility_scores_low(utility_stagnant):
    result = inv.score(utility_stagnant)
    assert result.total_score < 40, (
        f"No-growth utility should score <40, got {result.total_score}"
    )


def test_druckenmiller_nvidia_beats_utility(nvidia_clone, utility_stagnant):
    good = inv.score(nvidia_clone).total_score
    bad = inv.score(utility_stagnant).total_score
    assert good > bad


# ─────────────────────────────────────────────────────────────────────────────
# Cross-fixture tests (shared conftest fixtures)
# ─────────────────────────────────────────────────────────────────────────────

def test_druckenmiller_high_quality_beats_low_quality(high_quality_data, low_quality_data):
    good = inv.score(high_quality_data).total_score
    bad = inv.score(low_quality_data).total_score
    assert good > bad


# ─────────────────────────────────────────────────────────────────────────────
# Crash safety
# ─────────────────────────────────────────────────────────────────────────────

def test_druckenmiller_empty_data_no_crash(empty_data):
    result = inv.score(empty_data)
    assert result.total_score >= 0.0
    assert result.verdict in ("Strong Buy", "Buy", "Hold", "Avoid")


# ─────────────────────────────────────────────────────────────────────────────
# Red flag tests
# ─────────────────────────────────────────────────────────────────────────────

def test_druckenmiller_low_quality_has_red_flags(low_quality_data):
    result = inv.score(low_quality_data)
    assert len(result.red_flags) > 0, "Low quality data should trigger red flags"


def test_druckenmiller_nvidia_few_red_flags(nvidia_clone):
    result = inv.score(nvidia_clone)
    assert len(result.red_flags) == 0, (
        f"High-growth stock should have no red flags, got: {result.red_flags}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual rule tests
# ─────────────────────────────────────────────────────────────────────────────

def test_druckenmiller_earnings_acceleration_detected(nvidia_clone):
    """NVDA-like stock should show earnings acceleration."""
    result = inv.score(nvidia_clone)
    accel_rules = [r for r in result.rules_passed if "Acceleration" in r.name and "Earnings" in r.name]
    assert len(accel_rules) == 1, "Earnings acceleration should be detected"


def test_druckenmiller_flat_eps_fails_acceleration(utility_stagnant):
    """Flat EPS should fail the acceleration test."""
    result = inv.score(utility_stagnant)
    accel_rules = [r for r in result.rules_failed if "Acceleration" in r.name and "Earnings" in r.name]
    assert len(accel_rules) == 1, "Flat EPS should fail acceleration"


def test_druckenmiller_peg_check(nvidia_clone, utility_stagnant):
    """PEG 1.2 should pass; PEG 3.5 should fail."""
    good = inv.score(nvidia_clone)
    bad = inv.score(utility_stagnant)
    peg_pass = [r for r in good.rules_passed if "PEG" in r.name]
    peg_fail = [r for r in bad.rules_failed if "PEG" in r.name]
    assert len(peg_pass) == 1, "PEG 1.2 should pass"
    assert len(peg_fail) == 1, "PEG 3.5 should fail"
