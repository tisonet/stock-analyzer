"""
Financial data fetcher using yfinance.
Returns a FinancialData object with pre-computed convenience properties.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class FinancialData:
    """All raw and computed financial data for a single ticker."""

    ticker: str
    info: dict
    income_stmt: pd.DataFrame    # annual income statement (rows = metrics, cols = years)
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    history: pd.DataFrame        # 10yr daily OHLCV

    # ---------------------------------------------------------------- helpers

    def _safe_row(self, df: pd.DataFrame, *keys: str) -> Optional[pd.Series]:
        """Find first matching row in a DataFrame by trying multiple key names."""
        for key in keys:
            if key in df.index:
                return df.loc[key]
        return None

    def _latest(self, df: pd.DataFrame, *keys: str) -> Optional[float]:
        """Return the most recent non-null value for a metric."""
        row = self._safe_row(df, *keys)
        if row is None:
            return None
        for val in row:
            try:
                v = float(val)
                if not np.isnan(v):
                    return v
            except (TypeError, ValueError):
                continue
        return None

    def _series(self, df: pd.DataFrame, *keys: str) -> list[float]:
        """Return all non-null values for a metric as a list (oldest→newest)."""
        row = self._safe_row(df, *keys)
        if row is None:
            return []
        vals = []
        for val in reversed(row.tolist()):
            try:
                v = float(val)
                if not np.isnan(v):
                    vals.append(v)
            except (TypeError, ValueError):
                continue
        return vals

    # ---------------------------------------------------------------- income statement

    @property
    def revenue_series(self) -> list[float]:
        return self._series(self.income_stmt, "Total Revenue", "Revenue")

    @property
    def operating_income_series(self) -> list[float]:
        return self._series(
            self.income_stmt,
            "Operating Income",
            "EBIT",
            "Ebit",
        )

    @property
    def net_income_series(self) -> list[float]:
        return self._series(self.income_stmt, "Net Income", "Net Income Common Stockholders")

    @property
    def eps_series(self) -> list[float]:
        return self._series(self.income_stmt, "Basic EPS", "Diluted EPS", "EPS")

    @property
    def tax_rate(self) -> Optional[float]:
        """Effective tax rate from most recent year."""
        tax = self._latest(self.income_stmt, "Tax Provision", "Income Tax Expense")
        pretax = self._latest(self.income_stmt, "Pretax Income", "Income Before Tax")
        if tax is None or pretax is None or pretax == 0:
            return None
        return max(0.0, min(0.5, tax / pretax))

    @property
    def gross_margin_series(self) -> list[float]:
        rev = self._series(self.income_stmt, "Total Revenue", "Revenue")
        gp = self._series(self.income_stmt, "Gross Profit")
        if not rev or not gp:
            return []
        n = min(len(rev), len(gp))
        margins = []
        for i in range(n):
            if rev[i] != 0:
                margins.append(gp[i] / rev[i])
        return margins

    @property
    def interest_expense(self) -> Optional[float]:
        val = self._latest(
            self.income_stmt,
            "Interest Expense",
            "Interest Expense Non Operating",
            "Net Interest Income",
        )
        return abs(val) if val is not None else None

    @property
    def rd_expense_series(self) -> list[float]:
        raw = self._series(
            self.income_stmt,
            "Research And Development",
            "Research Development",
            "Research And Development Expenses",
        )
        return [abs(v) for v in raw]

    # ---------------------------------------------------------------- balance sheet

    @property
    def total_assets(self) -> Optional[float]:
        return self._latest(self.balance_sheet, "Total Assets")

    @property
    def current_assets(self) -> Optional[float]:
        return self._latest(self.balance_sheet, "Current Assets", "Total Current Assets")

    @property
    def current_liabilities(self) -> Optional[float]:
        return self._latest(
            self.balance_sheet, "Current Liabilities", "Total Current Liabilities"
        )

    @property
    def total_liabilities(self) -> Optional[float]:
        return self._latest(
            self.balance_sheet, "Total Liabilities Net Minority Interest", "Total Liabilities"
        )

    @property
    def total_debt(self) -> Optional[float]:
        return self._latest(
            self.balance_sheet,
            "Total Debt",
            "Long Term Debt",
            "LongTermDebt",
        )

    @property
    def stockholders_equity(self) -> Optional[float]:
        return self._latest(
            self.balance_sheet,
            "Stockholders Equity",
            "Total Stockholders Equity",
            "Common Stock Equity",
        )

    @property
    def cash_and_equivalents(self) -> Optional[float]:
        return self._latest(
            self.balance_sheet,
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
        )

    @property
    def inventory(self) -> Optional[float]:
        return self._latest(self.balance_sheet, "Inventory")

    @property
    def receivables(self) -> Optional[float]:
        return self._latest(self.balance_sheet, "Receivables", "Accounts Receivable")

    @property
    def shares_outstanding_series(self) -> list[float]:
        return self._series(
            self.balance_sheet,
            "Ordinary Shares Number",
            "Share Issued",
        )

    # ---------------------------------------------------------------- cash flow

    @property
    def operating_cash_flow_series(self) -> list[float]:
        return self._series(
            self.cash_flow,
            "Operating Cash Flow",
            "Cash Flow From Continuing Operating Activities",
        )

    @property
    def capex_series(self) -> list[float]:
        raw = self._series(
            self.cash_flow,
            "Capital Expenditure",
            "Purchase Of PPE",
            "Capital Expenditures",
        )
        # capex is typically negative in yfinance; return absolute values
        return [abs(v) for v in raw]

    @property
    def free_cash_flow_series(self) -> list[float]:
        ocf = self.operating_cash_flow_series
        capex = self.capex_series
        n = min(len(ocf), len(capex))
        if n == 0:
            return []
        return [ocf[i] - capex[i] for i in range(n)]

    # ---------------------------------------------------------------- computed metrics

    @property
    def roic_series(self) -> list[float]:
        """
        ROIC = NOPAT / Average Invested Capital
        NOPAT = Operating Income * (1 - effective_tax_rate)
        Average IC = (IC_beginning + IC_ending) / 2
        IC = Stockholders' Equity + max(0, Total Debt - Cash)

        For debt-financed companies (Debt > Cash) IC equals the standard
        GuruFocus formula: Equity + Total Debt - Cash.

        For net-cash companies (Cash > Debt) the cash deduction is capped at
        total debt, so IC = Equity. Subtracting excess cash beyond total debt
        would shrink IC to near-zero and produce artificially high ROIC (e.g.
        ASML: Cash 12.9B >> LTD 2.7B → IC only 7B → ROIC 88% vs GuruFocus 29%).
        Flooring IC at Equity avoids that distortion.

        Uses per-year effective tax rates (Tax Provision / Pretax Income) where
        available, capped at [0%, 50%], falling back to the most recent effective
        rate or a 25% default.

        Uses average invested capital (beginning-of-period + end-of-period) / 2
        to match the capital deployed throughout each year's operations, following
        McKinsey/GuruFocus methodology. For the earliest year where no prior
        balance sheet exists, ending IC is used directly.

        Uses Total Debt (short-term + long-term) rather than Long-term Debt
        alone, which is more consistent with GuruFocus and standard practice.

        Source: GuruFocus ROIC methodology; Koller, Goedhart & Wessels,
        "Valuation" (McKinsey, 7th ed.) Ch. 7
        """
        # Per-year effective tax rates (oldest → newest, aligned with income stmt)
        tax_prov_s = self._series(self.income_stmt, "Tax Provision", "Income Tax Expense")
        pretax_s = self._series(self.income_stmt, "Pretax Income", "Income Before Tax")
        default_tax = self.tax_rate or 0.25

        def _tax_for_year(i: int) -> float:
            if i < len(tax_prov_s) and i < len(pretax_s) and pretax_s[i] != 0:
                return max(0.0, min(0.5, tax_prov_s[i] / pretax_s[i]))
            return default_tax

        op_inc = self._series(
            self.income_stmt, "Operating Income", "EBIT", "Ebit"
        )
        equity = self._series(
            self.balance_sheet,
            "Stockholders Equity",
            "Total Stockholders Equity",
            "Common Stock Equity",
        )
        total_debt = self._series(
            self.balance_sheet,
            "Total Debt",
            "Long Term Debt",
        )
        cash = self._series(
            self.balance_sheet,
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
        )
        n = min(len(op_inc), len(equity))
        if n == 0:
            return []

        def _ic(i: int) -> float:
            """Invested capital at period-end for index i."""
            debt_v = total_debt[i] if i < len(total_debt) else 0.0
            cash_v = cash[i]       if i < len(cash)       else 0.0
            # Cap cash deduction at total debt so net-cash companies don't
            # end up with near-zero IC and inflated ROIC.
            net_debt = max(0.0, debt_v - cash_v)
            return equity[i] + net_debt

        roics = []
        for i in range(n):
            ic_end = _ic(i)
            # Average IC: use prior-period ending IC as beginning when available.
            avg_ic = (_ic(i - 1) + ic_end) / 2.0 if i > 0 else ic_end
            if avg_ic <= 0:
                continue
            nopat = op_inc[i] * (1 - _tax_for_year(i))
            roics.append(nopat / avg_ic)
        return roics

    @property
    def debt_to_equity(self) -> Optional[float]:
        """D/E from most recent balance sheet."""
        debt = self.total_debt
        equity = self.stockholders_equity
        if debt is None or equity is None or equity == 0:
            return self.info.get("debtToEquity")
        return debt / equity

    @property
    def current_ratio(self) -> Optional[float]:
        ca = self.current_assets
        cl = self.current_liabilities
        if ca is None or cl is None or cl == 0:
            return self.info.get("currentRatio")
        return ca / cl

    @property
    def pe_ratio(self) -> Optional[float]:
        return self.info.get("trailingPE") or self.info.get("forwardPE")

    @property
    def pb_ratio(self) -> Optional[float]:
        return self.info.get("priceToBook")

    @property
    def market_cap(self) -> Optional[float]:
        return self.info.get("marketCap")

    @property
    def dividend_yield(self) -> Optional[float]:
        return self.info.get("dividendYield")

    @property
    def five_year_avg_dividend_yield(self) -> Optional[float]:
        return self.info.get("fiveYearAvgDividendYield")

    @property
    def peg_ratio(self) -> Optional[float]:
        return self.info.get("pegRatio") or self.info.get("trailingPegRatio")

    @property
    def insider_ownership_pct(self) -> Optional[float]:
        """Fraction (0–1) of shares held by insiders."""
        return self.info.get("heldPercentInsiders")

    @property
    def beta(self) -> Optional[float]:
        return self.info.get("beta")

    @property
    def company_name(self) -> str:
        return self.info.get("longName") or self.info.get("shortName") or self.ticker

    @property
    def sector(self) -> str:
        return self.info.get("sector") or "Unknown"

    @property
    def industry(self) -> str:
        return self.info.get("industry") or "Unknown"

    @property
    def business_summary(self) -> str:
        return self.info.get("longBusinessSummary") or ""

    @property
    def country(self) -> str:
        return self.info.get("country") or "Unknown"

    @property
    def max_drawdown(self) -> Optional[float]:
        """Maximum peak-to-trough drawdown in 10yr price history."""
        if self.history.empty or "Close" not in self.history.columns:
            return None
        prices = self.history["Close"]
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        return float(drawdown.min())

    @property
    def price_return_12m(self) -> Optional[float]:
        """12-month price return."""
        if self.history.empty or len(self.history) < 252:
            return None
        close = self.history["Close"]
        return float((close.iloc[-1] / close.iloc[-252]) - 1)

    @property
    def book_value_per_share(self) -> Optional[float]:
        equity = self.stockholders_equity
        shares = self.info.get("sharesOutstanding")
        if equity and shares:
            return equity / shares
        return self.info.get("bookValue")

    @property
    def eps_ttm(self) -> Optional[float]:
        return self.info.get("trailingEps")

    @property
    def eps_growth_10yr(self) -> Optional[float]:
        """Total EPS growth over 10 years."""
        eps = self.eps_series
        if len(eps) < 2:
            return None
        if eps[0] <= 0:
            return None
        return (eps[-1] - eps[0]) / abs(eps[0])

    @property
    def eps_growth_rate_annual(self) -> Optional[float]:
        """CAGR of EPS over available history."""
        eps = self.eps_series
        n = len(eps)
        if n < 2 or eps[0] <= 0 or eps[-1] <= 0:
            # fall back to analyst estimate
            return self.info.get("earningsGrowth") or self.info.get("revenueGrowth")
        years = n - 1
        return (eps[-1] / eps[0]) ** (1 / years) - 1

    @property
    def fcf_margin_series(self) -> list[float]:
        fcf = self.free_cash_flow_series
        rev = self.revenue_series
        n = min(len(fcf), len(rev))
        margins = []
        for i in range(n):
            if rev[i] != 0:
                margins.append(fcf[i] / rev[i])
        return margins

    @property
    def roe_series(self) -> list[float]:
        """Return on Equity = Net Income / Stockholders Equity.

        Years with zero or negative equity are skipped — negative equity
        (common in buyback-heavy companies like FICO, MCD, SBUX) makes
        ROE economically meaningless and produces misleading negative
        values that don't reflect actual profitability.
        """
        ni = self.net_income_series
        eq = self._series(
            self.balance_sheet,
            "Stockholders Equity",
            "Total Stockholders Equity",
            "Common Stock Equity",
        )
        n = min(len(ni), len(eq))
        roes = []
        for i in range(n):
            if eq[i] > 0:
                roes.append(ni[i] / eq[i])
        return roes


def _safe_df(fn) -> pd.DataFrame:
    """Call fn(), return empty DataFrame on any error."""
    try:
        result = fn()
        if isinstance(result, pd.DataFrame):
            return result
        return pd.DataFrame()
    except Exception as e:
        logger.debug(f"DataFrame fetch failed: {e}")
        return pd.DataFrame()


def fetch(symbol: str) -> FinancialData:
    """
    Fetch all financial data for a ticker using yfinance.
    yfinance 1.x uses curl_cffi internally for proper TLS fingerprinting —
    no custom session needed.
    Raises ValueError if ticker cannot be resolved.
    """
    symbol = symbol.upper().strip()
    logger.info(f"Fetching data for {symbol}")

    t = yf.Ticker(symbol)

    # ── Company info ──────────────────────────────────────────────────────
    try:
        info = t.info or {}
    except Exception as e:
        logger.warning(f"t.info failed for {symbol}: {e}")
        info = {}

    # Validate ticker exists (yfinance returns minimal dict for invalid tickers)
    if not info or not info.get("quoteType"):
        # Try fast_info as a last resort
        try:
            fi = t.fast_info
            info = {
                "quoteType":          "EQUITY",
                "longName":           getattr(fi, "companyName", symbol),
                "shortName":          symbol,
                "currentPrice":       getattr(fi, "last_price",  None),
                "regularMarketPrice": getattr(fi, "last_price",  None),
                "marketCap":          getattr(fi, "market_cap",  None),
                "sharesOutstanding":  getattr(fi, "shares",      None),
                "beta":               getattr(fi, "beta",        None),
                "sector":             "Unknown",
                "industry":           "Unknown",
                "country":            "Unknown",
            }
        except Exception as e2:
            logger.error(f"fast_info also failed for {symbol}: {e2}")
            raise ValueError(
                f"Ticker '{symbol}' not found or Yahoo Finance is temporarily "
                f"unavailable. Please verify the symbol and retry."
            )

    if not info:
        raise ValueError(f"Ticker '{symbol}' not found.")

    # ── Financial statements ──────────────────────────────────────────────
    income_stmt   = _safe_df(lambda: t.financials)
    balance_sheet = _safe_df(lambda: t.balance_sheet)
    cash_flow     = _safe_df(lambda: t.cashflow)

    # ── Price history ─────────────────────────────────────────────────────
    history = _safe_df(lambda: t.history(period="10y"))

    logger.info(
        f"{symbol}: income={income_stmt.shape}, "
        f"balance={balance_sheet.shape}, cf={cash_flow.shape}, "
        f"history={len(history)} rows"
    )

    return FinancialData(
        ticker=symbol,
        info=info,
        income_stmt=income_stmt,
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        history=history,
    )
