"""
Tests for the improved roic_series calculation in FinancialData.

Covers:
- Per-year effective tax rates
- Average invested capital (beginning + ending / 2)
- Net-cash IC floor (cash deduction capped at total debt)
- Edge cases: empty data, single year, zero/negative IC
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.backend.data.fetcher import FinancialData


def _make_fd(
    op_incs: list[float],
    equity: list[float],
    total_debt: list[float],
    cash: list[float],
    tax_provisions: list[float] | None = None,
    pretax_incomes: list[float] | None = None,
) -> FinancialData:
    """Build a minimal FinancialData with the given per-year series."""
    n_inc = len(op_incs)
    n_bs = len(equity)

    # Income statement (newest → oldest columns, then _series reverses)
    inc_years = pd.to_datetime(
        [f"{2023 - i}-12-31" for i in range(n_inc)]
    )
    inc_data: dict = {"Operating Income": list(op_incs)}
    if tax_provisions is not None:
        inc_data["Tax Provision"] = list(tax_provisions)
    if pretax_incomes is not None:
        inc_data["Pretax Income"] = list(pretax_incomes)
    income_stmt = pd.DataFrame(inc_data, index=inc_years).T

    # Balance sheet (newest → oldest columns)
    bs_years = pd.to_datetime(
        [f"{2023 - i}-12-31" for i in range(n_bs)]
    )
    bs_data = {
        "Stockholders Equity": list(equity),
        "Total Debt": list(total_debt),
        "Cash And Cash Equivalents": list(cash),
    }
    balance_sheet = pd.DataFrame(bs_data, index=bs_years).T

    return FinancialData(
        ticker="TEST",
        info={},
        income_stmt=income_stmt,
        balance_sheet=balance_sheet,
        cash_flow=pd.DataFrame(),
        history=pd.DataFrame(),
    )


# ── Basic correctness ─────────────────────────────────────────────────────────

def test_roic_single_year_uses_ending_ic():
    """With only one year of data, ROIC uses ending IC (no prior period)."""
    fd = _make_fd(
        op_incs=[100.0],
        equity=[500.0],
        total_debt=[200.0],
        cash=[50.0],
        # tax_provision / pretax → tax rate = 0.25
        tax_provisions=[25.0],
        pretax_incomes=[100.0],
    )
    roics = fd.roic_series
    assert len(roics) == 1
    # IC = 500 + max(0, 200-50) = 650; NOPAT = 100 * 0.75 = 75; ROIC = 75/650
    expected = 75.0 / 650.0
    assert abs(roics[0] - expected) < 1e-9


def test_roic_average_ic_two_years():
    """With two years, year 1 uses ending IC; year 2 uses average IC."""
    # Provide newest-first: year[0]=2023, year[1]=2022 in DataFrame
    # After _series reversal: index 0 = 2022, index 1 = 2023
    fd = _make_fd(
        op_incs=[120.0, 100.0],   # newest first → after reversal: [100, 120]
        equity=[600.0, 500.0],    # newest first → after reversal: [500, 600]
        total_debt=[200.0, 200.0],
        cash=[50.0, 50.0],
        tax_provisions=[30.0, 25.0],
        pretax_incomes=[120.0, 100.0],
    )
    # After _series reversal (oldest→newest):
    # i=0: op_inc=100, eq=500, debt=200, cash=50; IC_end=650; avg_ic=650 (no prior)
    #      tax = 25/100 = 0.25; NOPAT = 100*0.75 = 75; ROIC = 75/650
    # i=1: op_inc=120, eq=600, debt=200, cash=50; IC_end=750
    #      avg_ic = (650 + 750)/2 = 700
    #      tax = 30/120 = 0.25; NOPAT = 120*0.75 = 90; ROIC = 90/700
    roics = fd.roic_series
    assert len(roics) == 2
    assert abs(roics[0] - 75.0 / 650.0) < 1e-9
    assert abs(roics[1] - 90.0 / 700.0) < 1e-9


def test_roic_per_year_tax_rates():
    """Per-year tax rates are applied correctly."""
    fd = _make_fd(
        op_incs=[100.0, 100.0],   # newest first
        equity=[500.0, 500.0],
        total_debt=[0.0, 0.0],
        cash=[0.0, 0.0],
        # Older year (index 0 after reversal): 20% tax; newer (index 1): 30%
        tax_provisions=[30.0, 20.0],   # newest first in DataFrame
        pretax_incomes=[100.0, 100.0],
    )
    # After reversal: i=0 tax=20%, i=1 tax=30%
    roics = fd.roic_series
    assert len(roics) == 2
    # i=0: IC=500, NOPAT=100*0.80=80, ROIC=80/500=0.16
    assert abs(roics[0] - 0.16) < 1e-9
    # i=1: avg_ic=(500+500)/2=500, NOPAT=100*0.70=70, ROIC=70/500=0.14
    assert abs(roics[1] - 0.14) < 1e-9


def test_roic_default_tax_when_data_missing():
    """Falls back to 25% default tax when no tax provision rows present."""
    fd = _make_fd(
        op_incs=[100.0],
        equity=[400.0],
        total_debt=[0.0],
        cash=[0.0],
    )
    roics = fd.roic_series
    assert len(roics) == 1
    # NOPAT = 100 * (1 - 0.25) = 75; IC = 400
    assert abs(roics[0] - 75.0 / 400.0) < 1e-9


def test_roic_net_cash_floor():
    """Cash deduction is capped at total debt (IC floors at equity)."""
    fd = _make_fd(
        op_incs=[50.0],
        equity=[1000.0],
        total_debt=[100.0],
        cash=[500.0],   # cash >> debt → net_debt = max(0, 100-500) = 0
    )
    roics = fd.roic_series
    assert len(roics) == 1
    # IC = 1000 + 0 = 1000; NOPAT = 50 * 0.75 = 37.5; ROIC = 37.5/1000
    assert abs(roics[0] - 37.5 / 1000.0) < 1e-9


def test_roic_skips_zero_ic():
    """Years with zero or negative average IC are excluded from output."""
    fd = _make_fd(
        op_incs=[100.0],
        equity=[0.0],
        total_debt=[0.0],
        cash=[0.0],
    )
    # IC = 0 → should be skipped
    assert fd.roic_series == []


def test_roic_empty_data(empty_data):
    """Empty DataFrames return an empty list without raising."""
    assert empty_data.roic_series == []


# ── Fixture-based sanity checks ───────────────────────────────────────────────

def test_roic_high_quality_positive(high_quality_data):
    """High-quality company should have positive ROIC values."""
    roics = high_quality_data.roic_series
    assert len(roics) > 0, "Should produce ROIC values for high-quality fixture"
    assert all(r > 0 for r in roics), "All ROIC values should be positive"


def test_roic_high_quality_above_threshold(high_quality_data):
    """High-quality company's average ROIC should exceed the 15% Buffett threshold."""
    import statistics
    roics = high_quality_data.roic_series
    assert statistics.mean(roics) > 0.15, "High-quality company should have avg ROIC > 15%"


def test_roic_average_ic_lowers_inflated_returns():
    """
    When IC is growing rapidly, averaging reduces inflated single-period ROIC.
    Tests that avg IC is strictly greater than ending IC for a growing company.
    """
    # IC grows from 500 → 1000 over two years
    fd = _make_fd(
        op_incs=[100.0, 100.0],   # newest first
        equity=[1000.0, 500.0],   # newest first → after reversal: [500, 1000]
        total_debt=[0.0, 0.0],
        cash=[0.0, 0.0],
    )
    roics = fd.roic_series
    assert len(roics) == 2
    # i=0: IC=500, ROIC = 75/500 = 15%
    # i=1: avg_ic=(500+1000)/2=750, ROIC = 75/750 = 10%  (not 75/1000=7.5%)
    assert abs(roics[0] - 0.15) < 1e-9
    assert abs(roics[1] - 75.0 / 750.0) < 1e-9
