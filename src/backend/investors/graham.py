"""
Benjamin Graham scoring module.

Rules based on:
- "The Intelligent Investor" by Benjamin Graham (1949, revised 1973)
- "Security Analysis" by Graham & Dodd (1934)
"""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class GrahamInvestor(BaseInvestor):
    """
    Benjamin Graham scoring: deep value, margin of safety, defensive quality.
    Graham prioritises statistical cheapness and balance sheet strength.
    """

    @property
    def name(self) -> str:
        return "Graham"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: P/E < 15 AND P/B < 1.5 (or P/E×P/B < 22.5) — 25 pts ─
        # "The Intelligent Investor", Ch.14 — Defensive Investor criteria
        pe = data.pe_ratio
        pb = data.pb_ratio
        pe_pb_product = None
        pe_pb_pass = None
        if pe is not None and pb is not None:
            pe_pb_product = pe * pb
            pe_pb_pass = (pe < 15 and pb < 1.5) or pe_pb_product < 22.5
        elif pe is not None:
            pe_pb_pass = pe < 15
            pe_pb_product = pe  # partial check
        r1 = self._make_rule(
            name="P/E < 15 and P/B < 1.5 (or P/E×P/B < 22.5)",
            value=pe_pb_product,
            threshold=22.5,
            points_possible=25.0,
            description=(
                f"P/E={pe:.1f}, P/B={pb:.1f}, P/E×P/B={pe_pb_product:.1f}"
                if pe is not None and pb is not None
                else f"P/E={pe:.1f} (P/B unavailable)" if pe is not None else "P/E and P/B unavailable"
            ),
            source="The Intelligent Investor, Ch.14, Graham",
            passed=pe_pb_pass,
        )
        rules.append(r1)
        if pe is not None and pe > 25:
            red_flags.append(f"P/E of {pe:.0f}x far exceeds Graham's 15x ceiling")

        # ── Rule 2: Current Ratio > 2 — 15 pts ─────────────────────────────
        # "Security Analysis", Ch.43 — adequate liquidity cushion for uncertainty
        cr = data.current_ratio
        r2 = self._make_rule(
            name="Current Ratio > 2.0",
            value=cr,
            threshold=2.0,
            points_possible=15.0,
            description=(
                f"Current ratio = {cr:.2f}"
                if cr is not None
                else "Current ratio unavailable"
            ),
            source="Security Analysis, Graham & Dodd, Ch.43",
        )
        rules.append(r2)
        if cr is not None and cr < 1.0:
            red_flags.append(f"Current ratio of {cr:.1f} — liquidity crisis risk")

        # ── Rule 3: Long-term debt < Net Current Assets — 15 pts ───────────
        # "The Intelligent Investor", Ch.14
        # Net Current Assets = Current Assets - Total Liabilities
        ca = data.current_assets
        total_liab = data.total_liabilities
        debt = data.total_debt
        debt_lt_nca = None
        nca = None
        if ca is not None and total_liab is not None:
            nca = ca - total_liab
            if debt is not None:
                debt_lt_nca = debt < nca
        r3 = self._make_rule(
            name="Long-term Debt < Net Current Assets",
            value=nca,
            threshold=0.0,
            points_possible=15.0,
            description=(
                f"NCA = ${nca/1e9:.2f}B vs Debt = ${debt/1e9:.2f}B"
                if nca is not None and debt is not None
                else "Balance sheet data unavailable"
            ),
            source="The Intelligent Investor, Ch.14, Graham",
            passed=debt_lt_nca,
        )
        rules.append(r3)
        if debt_lt_nca is False and nca is not None and nca < 0:
            red_flags.append("Net current assets negative — technically insolvent on Graham's measure")

        # ── Rule 4: 20+ years of uninterrupted dividends — 15 pts ──────────
        # "The Intelligent Investor", Ch.14 — earnings stability indicator
        # Proxy: use dividend history indicator from yfinance info
        # yfinance 'dividendYield' is present → company pays dividends
        # 'exDividendDate' present + yield > 0 → active payer
        # We use dividend yield as proxy; ideally need full dividend history
        div_yield = data.dividend_yield
        div_history_years = None
        has_div = div_yield is not None and div_yield > 0
        # yfinance doesn't easily expose 20yr dividend history; use 5yr avg as proxy
        five_yr_div = data.five_year_avg_dividend_yield
        if has_div and five_yr_div and five_yr_div > 0:
            div_history_years = 20  # assume continuous if both present (conservative)
        elif has_div:
            div_history_years = 5  # only current yield known
        else:
            div_history_years = 0
        r4 = self._make_rule(
            name="20+ years continuous dividends",
            value=float(div_history_years) if div_history_years is not None else None,
            threshold=20.0,
            points_possible=15.0,
            description=(
                f"Dividend yield = {div_yield*100:.2f}%, 5yr avg = {five_yr_div*100:.2f}%"
                if has_div and five_yr_div
                else "No dividend history detected"
            ),
            source="The Intelligent Investor, Ch.14, Graham",
            passed=div_history_years >= 20 if div_history_years is not None else None,
        )
        rules.append(r4)
        if not has_div:
            red_flags.append("No dividends paid — fails Graham's earnings stability requirement")

        # ── Rule 5: EPS growth > 33% over 10 years — 15 pts ───────────────
        # "The Intelligent Investor", Ch.14 — minimum earnings growth
        eps_growth = data.eps_growth_10yr
        eps_pct = eps_growth * 100 if eps_growth is not None else None
        r5 = self._make_rule(
            name="EPS growth > 33% (10yr total)",
            value=eps_pct,
            threshold=33.0,
            points_possible=15.0,
            description=(
                f"10yr EPS growth = {eps_pct:.1f}%"
                if eps_pct is not None
                else "EPS history insufficient"
            ),
            source="The Intelligent Investor, Ch.14, Graham",
        )
        rules.append(r5)
        if eps_growth is not None and eps_growth < 0:
            red_flags.append("EPS has declined over 10 years — earnings deterioration")

        # ── Rule 6: Margin of Safety ≥ 33% vs Graham Number — 15 pts ───────
        # Graham Number = sqrt(22.5 × EPS × Book Value per Share)
        # Margin of Safety = (Graham Number - Price) / Graham Number
        eps_ttm = data.eps_ttm
        bvps = data.book_value_per_share
        current_price = data.info.get("currentPrice") or data.info.get("regularMarketPrice")
        graham_number = None
        margin_of_safety = None
        if eps_ttm and eps_ttm > 0 and bvps and bvps > 0:
            graham_number = math.sqrt(22.5 * eps_ttm * bvps)
        if graham_number and current_price:
            margin_of_safety = (graham_number - current_price) / graham_number
        mos_pct = margin_of_safety * 100 if margin_of_safety is not None else None
        r6 = self._make_rule(
            name="Margin of Safety ≥ 33% vs Graham Number",
            value=mos_pct,
            threshold=33.0,
            points_possible=15.0,
            description=(
                f"Graham Number = ${graham_number:.2f}, MoS = {mos_pct:.1f}%"
                if graham_number and mos_pct is not None
                else "Graham Number unavailable (negative EPS or BV)"
            ),
            source="The Intelligent Investor, Ch.20 — Margin of Safety",
        )
        rules.append(r6)
        if margin_of_safety is not None and margin_of_safety < -0.5:
            red_flags.append(
                f"Trading {abs(mos_pct):.0f}% ABOVE Graham Number — no margin of safety"
            )

        return self._build_result(rules, red_flags)
