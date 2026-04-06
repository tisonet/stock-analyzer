"""
Compute year-by-year historical financial ratios by pairing annual
income-statement / cash-flow data with the closest trading-day closing
price from the 10yr daily history.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from src.backend.data.fetcher import FinancialData

logger = logging.getLogger(__name__)


def _closest_price(history: pd.DataFrame, target_date: pd.Timestamp) -> Optional[float]:
    """Return the closing price on or nearest before *target_date*."""
    if history.empty or "Close" not in history.columns:
        return None
    # Normalise tz: history index may be tz-aware (yfinance) while fiscal dates are tz-naive
    idx = history.index
    if idx.tz is not None and target_date.tzinfo is None:
        target_date = target_date.tz_localize(idx.tz)
    elif idx.tz is None and target_date.tzinfo is not None:
        target_date = target_date.tz_localize(None)
    mask = idx <= target_date
    if mask.any():
        nearest = idx[mask][-1]
    else:
        # target_date is before the earliest history row — use the earliest
        nearest = idx[0]
    try:
        val = float(history.loc[nearest, "Close"])
        return val if not np.isnan(val) else None
    except (KeyError, TypeError, ValueError):
        return None


def compute_historical_ratios(data: FinancialData) -> dict:
    """
    Compute P/E, P/S, FCF yield, Gross Margin, and Net Margin for each
    fiscal year present in the income statement.

    Returns::

        {
            "ticker": "AAPL",
            "years": [
                {
                    "year": 2023,
                    "pe": 22.5,
                    "ps": 7.3,
                    "fcf_yield": 0.035,
                    "gross_margin": 0.44,
                    "net_margin": 0.25,
                    "fcf_per_share": 5.8,
                    "eps": 6.0,
                    "revenue_per_share": 24.5,
                },
                ...
            ],
        }
    """
    income = data.income_stmt
    if income.empty:
        return {"ticker": data.ticker, "years": []}

    # Column dates represent fiscal year-ends (newest → oldest in yfinance)
    fiscal_dates: list[pd.Timestamp] = list(income.columns)

    # Helper to get a row value for a specific column date
    def _val(df: pd.DataFrame, col: pd.Timestamp, *keys: str) -> Optional[float]:
        for key in keys:
            if key in df.index:
                try:
                    v = float(df.loc[key, col])
                    if not np.isnan(v):
                        return v
                except (KeyError, TypeError, ValueError):
                    continue
        return None

    cash_flow = data.cash_flow
    balance_sheet = data.balance_sheet

    years: list[dict] = []

    for col_date in fiscal_dates:
        year = col_date.year

        revenue = _val(income, col_date, "Total Revenue", "Revenue")
        net_income = _val(income, col_date, "Net Income", "Net Income Common Stockholders")
        gross_profit = _val(income, col_date, "Gross Profit")
        eps = _val(income, col_date, "Basic EPS", "Diluted EPS", "EPS")

        # Shares outstanding from balance sheet for this year
        shares = None
        if not balance_sheet.empty and col_date in balance_sheet.columns:
            shares = _val(balance_sheet, col_date, "Ordinary Shares Number", "Share Issued")

        # FCF = Operating Cash Flow - |CapEx|
        fcf = None
        if not cash_flow.empty and col_date in cash_flow.columns:
            ocf = _val(cash_flow, col_date, "Operating Cash Flow",
                        "Cash Flow From Continuing Operating Activities")
            capex_raw = _val(cash_flow, col_date, "Capital Expenditure",
                              "Purchase Of PPE", "Capital Expenditures")
            if ocf is not None and capex_raw is not None:
                fcf = ocf - abs(capex_raw)

        # Gross Margin & Net Margin (no price needed)
        gross_margin = (gross_profit / revenue) if (gross_profit and revenue and revenue != 0) else None
        net_margin = (net_income / revenue) if (net_income is not None and revenue and revenue != 0) else None

        # Price-dependent ratios
        price = _closest_price(data.history, col_date)
        market_cap = (price * shares) if (price is not None and shares) else None

        pe = (price / eps) if (price is not None and eps and eps > 0) else None
        revenue_per_share = (revenue / shares) if (revenue and shares and shares > 0) else None
        ps = (market_cap / revenue) if (market_cap and revenue and revenue > 0) else None
        fcf_per_share = (fcf / shares) if (fcf is not None and shares and shares > 0) else None
        fcf_yield = (fcf / market_cap) if (fcf is not None and market_cap and market_cap > 0) else None

        years.append({
            "year": year,
            "pe": _round(pe),
            "ps": _round(ps),
            "fcf_yield": _round(fcf_yield, 4),
            "gross_margin": _round(gross_margin, 4),
            "net_margin": _round(net_margin, 4),
            "fcf_per_share": _round(fcf_per_share),
            "eps": _round(eps),
            "revenue_per_share": _round(revenue_per_share),
        })

    # Sort oldest → newest
    years.sort(key=lambda r: r["year"])

    return {"ticker": data.ticker, "years": years}


def _round(val: Optional[float], decimals: int = 2) -> Optional[float]:
    """Round a value if not None."""
    if val is None:
        return None
    return round(val, decimals)
