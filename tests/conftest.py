"""
Shared test fixtures with realistic financial data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backend.data.fetcher import FinancialData


def _make_income_stmt(
    revenues: list,
    op_incomes: list,
    net_incomes: list,
    gross_profits: list | None = None,
    epss: list | None = None,
    tax_provisions: list | None = None,
) -> pd.DataFrame:
    """Build a minimal income statement DataFrame."""
    years = [f"2023-12-31", f"2022-12-31", f"2021-12-31", f"2020-12-31",
             "2019-12-31", "2018-12-31", "2017-12-31", "2016-12-31",
             "2015-12-31", "2014-12-31"]
    n = len(revenues)
    years = years[:n]
    data = {
        "Total Revenue": revenues,
        "Operating Income": op_incomes,
        "Net Income": net_incomes,
    }
    if gross_profits:
        data["Gross Profit"] = gross_profits
    if epss:
        data["Basic EPS"] = epss
    if tax_provisions:
        data["Tax Provision"] = tax_provisions
        data["Pretax Income"] = [o * 1.3 for o in op_incomes]
    # yfinance format: index=metric names, columns=dates
    df = pd.DataFrame(data, index=pd.to_datetime(years)).T
    return df


def _make_balance_sheet(
    total_assets: list,
    current_assets: list,
    current_liabilities: list,
    total_liabilities: list,
    equity: list,
    total_debt: list,
    shares: list | None = None,
    cash: list | None = None,
    inventory: list | None = None,
    receivables: list | None = None,
) -> pd.DataFrame:
    n = len(total_assets)
    years = [f"2023-12-31", f"2022-12-31", f"2021-12-31", f"2020-12-31",
             "2019-12-31"][:n]
    data = {
        "Total Assets": total_assets,
        "Current Assets": current_assets,
        "Current Liabilities": current_liabilities,
        "Total Liabilities Net Minority Interest": total_liabilities,
        "Stockholders Equity": equity,
        "Total Debt": total_debt,
    }
    if shares:
        data["Ordinary Shares Number"] = shares
    if cash:
        data["Cash And Cash Equivalents"] = cash
    if inventory:
        data["Inventory"] = inventory
    if receivables:
        data["Receivables"] = receivables
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(years)
    return df.T


def _make_cashflow(
    op_cf: list,
    capex: list,
) -> pd.DataFrame:
    n = len(op_cf)
    years = [f"2023-12-31", f"2022-12-31", f"2021-12-31", f"2020-12-31",
             "2019-12-31"][:n]
    data = {
        "Operating Cash Flow": op_cf,
        "Capital Expenditure": [-c for c in capex],
    }
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(years)
    return df.T


def _make_history(prices: list) -> pd.DataFrame:
    idx = pd.date_range("2014-01-01", periods=len(prices), freq="B")
    return pd.DataFrame({"Close": prices}, index=idx)


# ─────────────────────────────────────────────────────────────────────────────
# High-quality company (Buffett Strong Buy candidate)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def high_quality_data() -> FinancialData:
    """AAPL-like: high ROIC, low debt, strong FCF, reasonable valuation."""
    revs =    [380e9, 365e9, 350e9, 330e9, 290e9, 260e9, 230e9, 210e9, 190e9, 175e9]
    op_incs = [110e9, 100e9,  95e9,  85e9,  70e9,  60e9,  55e9,  50e9,  45e9,  40e9]
    net_incs = [90e9,  85e9,  80e9,  70e9,  57e9,  50e9,  46e9,  42e9,  38e9,  35e9]
    gp =      [175e9, 168e9, 160e9, 150e9, 130e9, 115e9, 105e9,  95e9,  85e9,  78e9]
    epss =    [6.0,   5.7,   5.2,   4.8,   3.8,   3.2,   2.9,   2.5,   2.2,   2.0]

    income = _make_income_stmt(revs, op_incs, net_incs, gp, epss,
                               [op * 0.18 for op in op_incs])

    ta =   [350e9, 335e9, 320e9, 305e9, 290e9]
    ca =   [140e9, 130e9, 125e9, 120e9, 110e9]
    cl =   [ 70e9,  65e9,  60e9,  55e9,  50e9]
    tl =   [240e9, 228e9, 216e9, 205e9, 195e9]
    eq =   [110e9, 107e9, 104e9, 100e9,  95e9]
    debt = [ 90e9,  85e9,  80e9,  75e9,  70e9]
    sh =   [15.5e9, 15.8e9, 16.4e9, 17.0e9, 17.5e9]  # declining (buybacks)
    cash = [ 50e9,  48e9,  45e9,  42e9,  40e9]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, sh, cash)
    cashflow = _make_cashflow(
        [100e9, 95e9, 90e9, 85e9, 75e9],
        [ 10e9,  9e9,  9e9,  8e9,  8e9],
    )
    # Simple rising price history with only a 25% max drawdown
    prices = list(range(100, 200)) + list(range(200, 170, -3)) + list(range(170, 350))
    history = _make_history(prices[:2517])  # ~10yr trading days

    return FinancialData(
        ticker="HQCO",
        info={
            "trailingPE": 22.0,
            "priceToBook": 7.0,
            "debtToEquity": 82.0,   # 0.82 → high but manageable for this co
            "currentRatio": 2.0,
            "marketCap": 2_800e9,
            "currentPrice": 180.0,
            "sharesOutstanding": 15_500_000_000,
            "dividendYield": 0.006,
            "fiveYearAvgDividendYield": 0.007,
            "trailingEps": 6.0,
            "bookValue": 7.0,
            "pegRatio": 1.5,
            "heldPercentInsiders": 0.03,
            "beta": 1.1,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "United States",
            "longName": "High Quality Company Inc",
            "longBusinessSummary": "Makes great products sold directly to consumers.",
            "revenueGrowth": 0.04,
            "earningsGrowth": 0.05,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Low-quality company (Avoid candidate)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def low_quality_data() -> FinancialData:
    """Highly leveraged company with declining earnings and no dividends."""
    revs =    [50e9,  52e9,  55e9,  53e9,  48e9,  45e9,  42e9,  40e9,  38e9,  37e9]
    op_incs = [ 2e9,   3e9,   4e9,   1e9,  -1e9,   2e9,   1e9,   0.5e9, 0.8e9, 0.5e9]
    net_incs = [-1e9, -0.5e9,  1e9,  -2e9,  -3e9,   0.5e9, 0.3e9, -0.2e9, 0.1e9, -0.3e9]
    gp =      [10e9,  11e9,  12e9,  10e9,   8e9,   9e9,   8.5e9,  8e9,   7.5e9,  7e9]

    income = _make_income_stmt(revs, op_incs, net_incs, gp)

    ta =   [120e9, 118e9, 115e9, 112e9, 110e9]
    ca =   [ 20e9,  22e9,  21e9,  20e9,  19e9]
    cl =   [ 25e9,  24e9,  23e9,  22e9,  21e9]   # < current assets — bad ratio
    tl =   [110e9, 108e9, 105e9, 103e9, 100e9]
    eq =   [ 10e9,  10e9,  10e9,   9e9,  10e9]
    debt = [ 90e9,  88e9,  85e9,  83e9,  80e9]
    sh =   [2.5e9, 2.4e9, 2.2e9, 2.1e9, 2.0e9]  # 2023=most shares (dilution over time)
    cash = [  5e9,   4e9,   4e9,   3e9,   3e9]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, sh, cash)
    cashflow = _make_cashflow(
        [ 3e9,  2e9,  4e9,  -1e9, -2e9],
        [ 8e9,  9e9,  9e9,   8e9,  7e9],
    )
    # Price crashes 70%
    import math
    prices = [100] * 500 + [int(100 * math.exp(-i / 300)) for i in range(2017)]
    history = _make_history(prices[:2517])

    return FinancialData(
        ticker="LQCO",
        info={
            "trailingPE": 85.0,
            "priceToBook": 3.5,
            "debtToEquity": 900.0,  # 9x D/E
            "currentRatio": 0.8,
            "marketCap": 15e9,
            "currentPrice": 50.0,
            "sharesOutstanding": 300_000_000,
            "dividendYield": None,
            "fiveYearAvgDividendYield": None,
            "trailingEps": -0.5,
            "bookValue": 14.0,
            "pegRatio": None,
            "heldPercentInsiders": 0.002,
            "beta": 2.1,
            "sector": "Industrials",
            "industry": "Aerospace & Defense",
            "country": "United States",
            "longName": "Low Quality Corp",
            "longBusinessSummary": "A very complex business operating in many segments across "
                "multiple geographies with extensive regulatory exposure and significant "
                "reliance on government contracts that may be cancelled at any time.",
            "revenueGrowth": -0.03,
            "earningsGrowth": None,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Graham net-net company (cheap on assets, no growth)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def net_net_data() -> FinancialData:
    """Classic Graham net-net: cheap on assets, pays dividends, modest earnings."""
    revs =    [5e9,  4.8e9, 4.9e9, 5.1e9, 4.7e9, 4.5e9, 4.6e9, 4.4e9, 4.3e9, 4.2e9]
    op_incs = [0.4e9, 0.35e9, 0.38e9, 0.42e9, 0.30e9, 0.28e9, 0.29e9, 0.27e9, 0.25e9, 0.24e9]
    net_incs = [0.3e9, 0.25e9, 0.27e9, 0.32e9, 0.20e9, 0.18e9, 0.19e9, 0.17e9, 0.15e9, 0.14e9]
    gp =      [1.5e9, 1.4e9, 1.45e9, 1.55e9, 1.3e9, 1.25e9, 1.3e9, 1.2e9, 1.15e9, 1.1e9]
    epss =    [1.5, 1.25, 1.35, 1.6, 1.0, 0.9, 0.95, 0.85, 0.75, 0.7]

    income = _make_income_stmt(revs, op_incs, net_incs, gp, epss,
                               [o * 0.22 for o in op_incs])

    ta =   [8e9,   7.8e9,  7.6e9,  7.5e9,  7.4e9]
    ca =   [5e9,   4.8e9,  4.6e9,  4.5e9,  4.4e9]
    cl =   [1.5e9, 1.4e9,  1.35e9, 1.3e9,  1.25e9]
    tl =   [3e9,   2.9e9,  2.8e9,  2.7e9,  2.6e9]
    eq =   [5e9,   4.9e9,  4.8e9,  4.8e9,  4.8e9]
    debt = [1.5e9, 1.4e9,  1.35e9, 1.3e9,  1.25e9]
    sh =   [200e6, 201e6, 202e6, 203e6, 204e6]  # slight dilution
    cash = [2e9,   1.9e9,  1.8e9,  1.75e9, 1.7e9]
    recv = [1.5e9, 1.4e9,  1.35e9, 1.3e9,  1.25e9]

    balance = _make_balance_sheet(ta, ca, cl, tl, eq, debt, sh, cash,
                                   receivables=recv)
    cashflow = _make_cashflow(
        [0.45e9, 0.4e9, 0.42e9, 0.48e9, 0.35e9],
        [0.10e9, 0.09e9, 0.10e9, 0.11e9, 0.09e9],
    )
    prices = [60, 62, 58, 65, 64, 63, 67, 70, 68, 72, 69, 71] * 210
    history = _make_history(prices[:2517])

    return FinancialData(
        ticker="NNET",
        info={
            "trailingPE": 12.0,
            "priceToBook": 1.0,
            "debtToEquity": 30.0,   # 0.3x
            "currentRatio": 3.3,
            "marketCap": 4.5e9,
            "currentPrice": 22.0,
            "sharesOutstanding": 200_000_000,
            "dividendYield": 0.035,
            "fiveYearAvgDividendYield": 0.033,
            "trailingEps": 1.5,
            "bookValue": 25.0,
            "pegRatio": 1.2,
            "heldPercentInsiders": 0.06,
            "beta": 0.75,
            "sector": "Consumer Defensive",
            "industry": "Grocery Stores",
            "country": "United States",
            "longName": "Net Net Corp",
            "longBusinessSummary": "Sells groceries.",
            "revenueGrowth": 0.02,
            "earningsGrowth": 0.03,
        },
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )
