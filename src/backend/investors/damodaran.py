"""
Aswath Damodaran – Value Creation Investor Module

Based on the valuation framework of Professor Aswath Damodaran (NYU Stern),
widely known as the "Dean of Valuation."

Core philosophy: a company creates value ONLY when its return on invested
capital exceeds its cost of capital.  Growth is desirable only when funded by
reinvestment that earns above-WACC returns.

Key sources:
- "Investment Valuation" (Wiley, 3rd edition)
- "The Little Book of Valuation" (Wiley)
- "Narrative and Numbers" (Columbia Business School Publishing)
- Damodaran's annual industry datasets (pages.stern.nyu.edu/~adamodar/)
- "Musings on Markets" blog

Rule weights (total = 100):
1. ROIC vs WACC spread              — 20 pts  (core value creation test)
2. Excess return persistence         — 15 pts  (competitive advantage durability)
3. Revenue growth quality            — 15 pts  (sustainable, funded growth)
4. Operating margin stability        — 15 pts  (margin trend and consistency)
5. Capital efficiency                — 10 pts  (sales-to-capital ratio)
6. Free cash flow conversion         — 10 pts  (cash generation ability)
7. Financial risk                    — 15 pts  (interest coverage + leverage)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# Damodaran's cost-of-capital building blocks
_RISK_FREE_RATE = 0.045       # ≈ 10-year US Treasury yield
_EQUITY_RISK_PREMIUM = 0.055  # Damodaran's implied ERP (updated annually)


class DamodaranInvestor(BaseInvestor):
    """Aswath Damodaran's value-creation framework.

    Estimates WACC bottom-up (risk-free rate + beta × ERP for equity,
    synthetic-rating spread for debt) then checks whether the company
    earns above its cost of capital persistently.
    """

    @property
    def name(self) -> str:
        return "Damodaran"

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _synthetic_spread(interest_coverage: float) -> float:
        """Map interest coverage ratio to a default spread using
        Damodaran's synthetic-rating table (simplified)."""
        if interest_coverage > 12.5:
            return 0.0075
        if interest_coverage > 9.5:
            return 0.01
        if interest_coverage > 7.5:
            return 0.011
        if interest_coverage > 6.0:
            return 0.0125
        if interest_coverage > 4.5:
            return 0.015
        if interest_coverage > 4.0:
            return 0.0175
        if interest_coverage > 3.5:
            return 0.025
        if interest_coverage > 3.0:
            return 0.03
        if interest_coverage > 2.5:
            return 0.0375
        if interest_coverage > 2.0:
            return 0.045
        if interest_coverage > 1.5:
            return 0.055
        if interest_coverage > 1.25:
            return 0.065
        if interest_coverage > 0.8:
            return 0.08
        return 0.12

    def _estimate_wacc(self, data: FinancialData) -> float | None:
        """Bottom-up WACC estimation à la Damodaran."""
        beta = self._safe(data.beta) or 1.0
        cost_of_equity = _RISK_FREE_RATE + beta * _EQUITY_RISK_PREMIUM

        # Cost of debt via synthetic rating
        op_inc = data._latest(
            data.income_stmt, "Operating Income", "EBIT", "Ebit"
        )
        int_exp_s = data._series(data.income_stmt, "Interest Expense")
        int_exp = abs(int_exp_s[-1]) if int_exp_s else None

        if int_exp and int_exp > 0 and op_inc and op_inc > 0:
            spread = self._synthetic_spread(op_inc / int_exp)
        else:
            spread = 0.01  # minimal / no debt

        cost_of_debt = _RISK_FREE_RATE + spread
        tax_rate = data.tax_rate or 0.25

        total_debt = self._safe(data.total_debt) or 0
        mkt_cap = self._safe(data.market_cap) or 0
        total_value = mkt_cap + total_debt
        if total_value <= 0:
            return None

        e_w = mkt_cap / total_value
        d_w = total_debt / total_value
        return e_w * cost_of_equity + d_w * cost_of_debt * (1 - tax_rate)

    def _interest_coverage(self, data: FinancialData) -> float | None:
        """EBIT / |Interest Expense| (latest year)."""
        op_inc = data._latest(
            data.income_stmt, "Operating Income", "EBIT", "Ebit"
        )
        int_exp_s = data._series(data.income_stmt, "Interest Expense")
        int_exp = abs(int_exp_s[-1]) if int_exp_s else None
        if op_inc and int_exp and int_exp > 0:
            return op_inc / int_exp
        return None

    # ── scoring ───────────────────────────────────────────────────

    def score(self, data: FinancialData) -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        wacc = self._estimate_wacc(data)
        roic_s = data.roic_series

        # ── 1. ROIC vs WACC spread — 20 pts ──────────────────────
        latest_roic = roic_s[-1] if roic_s else None
        spread = None
        if latest_roic is not None and wacc is not None:
            spread = latest_roic - wacc

        if spread is not None and wacc is not None:
            if spread >= 0.10:
                p1 = 1.0
                d1 = (
                    f"ROIC {latest_roic:.1%} exceeds WACC {wacc:.1%} by "
                    f"{spread:.1%} — strong value creation"
                )
            elif spread >= 0.02:
                p1 = 0.7
                d1 = (
                    f"ROIC {latest_roic:.1%} exceeds WACC {wacc:.1%} by "
                    f"{spread:.1%} — moderate value creation"
                )
            elif spread >= 0:
                p1 = 0.4
                d1 = (
                    f"ROIC {latest_roic:.1%} barely exceeds WACC {wacc:.1%} "
                    f"— marginal value creation"
                )
            else:
                p1 = 0.0
                d1 = (
                    f"ROIC {latest_roic:.1%} below WACC {wacc:.1%} "
                    f"— value destruction"
                )
        else:
            p1 = 0.0
            d1 = "Data unavailable"

        r1 = self._make_rule(
            name="ROIC vs WACC Spread",
            value=spread,
            threshold=0.02,
            points_possible=20,
            description=d1,
            source=(
                "Investment Valuation, Ch. 12: "
                "'A firm creates value only when ROIC > cost of capital'"
            ),
            passed=spread is not None and spread >= 0,
            partial=p1,
            explanation=(
                "Core Damodaran test: does reinvested capital earn more "
                "than it costs?"
            ),
        )
        rules.append(r1)
        if spread is not None and spread < -0.05:
            red_flags.append(
                f"Severe value destruction: ROIC trails WACC by {abs(spread):.1%}"
            )

        # ── 2. Excess return persistence — 15 pts ────────────────
        pct_above: float | None = None
        if roic_s and wacc is not None:
            years_above = sum(1 for r in roic_s if r > wacc)
            total_years = len(roic_s)
            pct_above = years_above / total_years if total_years else 0.0

            if pct_above >= 0.8:
                p2 = 1.0
            elif pct_above >= 0.6:
                p2 = 0.7
            elif pct_above >= 0.4:
                p2 = 0.4
            else:
                p2 = 0.0

            d2 = (
                f"ROIC > WACC in {years_above}/{total_years} years "
                f"({pct_above:.0%})"
            )
        else:
            p2 = 0.0
            d2 = "Data unavailable"

        r2 = self._make_rule(
            name="Excess Return Persistence",
            value=pct_above,
            threshold=0.6,
            points_possible=15,
            description=d2,
            source=(
                "Narrative and Numbers: 'True moats show up as sustained "
                "ROIC > WACC over long periods'"
            ),
            passed=pct_above is not None and pct_above >= 0.4,
            partial=p2,
            explanation=(
                "Durability of competitive advantage measured by years "
                "of value creation"
            ),
        )
        rules.append(r2)

        # ── 3. Revenue growth quality — 15 pts ───────────────────
        rev_s = data.revenue_series
        rev_cagr: float | None = None
        if len(rev_s) >= 2 and rev_s[0] and rev_s[0] > 0 and rev_s[-1] > 0:
            rev_cagr = (rev_s[-1] / rev_s[0]) ** (1 / (len(rev_s) - 1)) - 1

            if rev_cagr >= 0.15:
                p3 = 1.0
            elif rev_cagr >= 0.05:
                p3 = 0.7
            elif rev_cagr >= 0:
                p3 = 0.4
            else:
                p3 = 0.0

            d3 = f"Revenue CAGR {rev_cagr:.1%} over {len(rev_s)} years"
        else:
            p3 = 0.0
            d3 = "Data unavailable"

        r3 = self._make_rule(
            name="Revenue Growth",
            value=rev_cagr,
            threshold=0.05,
            points_possible=15,
            description=d3,
            source=(
                "The Little Book of Valuation: "
                "'Growth creates value only when coupled with excess returns'"
            ),
            passed=rev_cagr is not None and rev_cagr >= 0,
            partial=p3,
            explanation=(
                "Sustainable revenue growth — the raw material for "
                "value creation"
            ),
        )
        rules.append(r3)
        if rev_cagr is not None and rev_cagr < -0.05:
            red_flags.append(f"Revenue declining at {rev_cagr:.1%} CAGR")

        # ── 4. Operating margin stability — 15 pts ───────────────
        op_s = data.operating_income_series
        avg_margin: float | None = None
        p4 = 0.0
        if len(rev_s) >= 3 and len(op_s) >= 3:
            margins: list[float] = []
            for i in range(min(len(rev_s), len(op_s))):
                if rev_s[i] and rev_s[i] > 0:
                    margins.append(op_s[i] / rev_s[i])

            if len(margins) >= 3:
                avg_margin = statistics.mean(margins)
                margin_stdev = statistics.stdev(margins)
                mid = len(margins) // 2
                first_half = statistics.mean(margins[:mid]) if mid > 0 else 0
                second_half = statistics.mean(margins[mid:])
                improving = second_half >= first_half

                if avg_margin >= 0.15 and margin_stdev < 0.05 and improving:
                    p4 = 1.0
                elif avg_margin >= 0.10 and margin_stdev < 0.08:
                    p4 = 0.7
                elif avg_margin >= 0.05:
                    p4 = 0.4
                else:
                    p4 = 0.0

                trend = "improving" if improving else "declining"
                d4 = (
                    f"Avg operating margin {avg_margin:.1%}, "
                    f"stdev {margin_stdev:.1%}, {trend}"
                )
            else:
                d4 = "Insufficient margin data"
        else:
            d4 = "Data unavailable"

        r4 = self._make_rule(
            name="Operating Margin Stability",
            value=avg_margin,
            threshold=0.10,
            points_possible=15,
            description=d4,
            source=(
                "Musings on Markets: 'Stable or expanding margins signal "
                "pricing power and cost discipline'"
            ),
            passed=avg_margin is not None and avg_margin >= 0.05,
            partial=p4,
            explanation=(
                "Margin consistency reflects competitive positioning "
                "and operational efficiency"
            ),
        )
        rules.append(r4)
        if avg_margin is not None and avg_margin < 0:
            red_flags.append(
                "Operating at a loss — negative operating margins"
            )

        # ── 5. Capital efficiency (sales-to-capital) — 10 pts ────
        rev_latest = rev_s[-1] if rev_s else None
        equity = self._safe(data.stockholders_equity)
        debt = self._safe(data.total_debt) or 0
        cash = self._safe(data.cash_and_equivalents) or 0

        sales_to_cap: float | None = None
        if rev_latest and equity and equity > 0:
            invested_capital = equity + max(0, debt - min(cash, debt))
            if invested_capital > 0:
                sales_to_cap = rev_latest / invested_capital

        if sales_to_cap is not None:
            if sales_to_cap >= 2.0:
                p5 = 1.0
            elif sales_to_cap >= 1.0:
                p5 = 0.7
            elif sales_to_cap >= 0.5:
                p5 = 0.4
            else:
                p5 = 0.0
            d5 = f"Sales-to-Capital ratio of {sales_to_cap:.2f}x"
        else:
            p5 = 0.0
            d5 = "Data unavailable"

        r5 = self._make_rule(
            name="Capital Efficiency",
            value=sales_to_cap,
            threshold=1.0,
            points_possible=10,
            description=d5,
            source=(
                "Investment Valuation: 'The sales-to-capital ratio measures "
                "how efficiently capital is deployed'"
            ),
            passed=sales_to_cap is not None and sales_to_cap >= 0.5,
            partial=p5,
            explanation=(
                "Revenue generated per dollar of invested capital — "
                "higher means more efficient"
            ),
        )
        rules.append(r5)

        # ── 6. Free cash flow conversion — 10 pts ────────────────
        fcf_margins = data.fcf_margin_series
        avg_fcf_m: float | None = None
        if fcf_margins:
            avg_fcf_m = statistics.mean(fcf_margins)
            latest_fcf_m = fcf_margins[-1]

            if avg_fcf_m >= 0.15:
                p6 = 1.0
            elif avg_fcf_m >= 0.05:
                p6 = 0.7
            elif avg_fcf_m >= 0:
                p6 = 0.4
            else:
                p6 = 0.0

            d6 = (
                f"Avg FCF margin {avg_fcf_m:.1%}, latest {latest_fcf_m:.1%}"
            )
        else:
            p6 = 0.0
            d6 = "Data unavailable"

        r6 = self._make_rule(
            name="Free Cash Flow Conversion",
            value=avg_fcf_m,
            threshold=0.05,
            points_possible=10,
            description=d6,
            source=(
                "The Little Book of Valuation: "
                "'Cash flows, not earnings, drive value'"
            ),
            passed=avg_fcf_m is not None and avg_fcf_m >= 0,
            partial=p6,
            explanation=(
                "Ability to convert revenue into free cash flow "
                "available to all investors"
            ),
        )
        rules.append(r6)
        if avg_fcf_m is not None and avg_fcf_m < -0.05:
            red_flags.append("Persistent negative free cash flow")

        # ── 7. Financial risk — 15 pts ───────────────────────────
        coverage = self._interest_coverage(data)
        debt_to_capital: float | None = None
        eq_val = self._safe(data.stockholders_equity)
        debt_val = self._safe(data.total_debt) or 0
        if eq_val and eq_val > 0:
            debt_to_capital = debt_val / (debt_val + eq_val)

        # Sub-scores (coverage 60%, leverage 40%)
        if coverage is not None:
            if coverage > 6.0:
                cov_s = 1.0
            elif coverage > 3.0:
                cov_s = 0.6
            elif coverage > 1.5:
                cov_s = 0.3
            else:
                cov_s = 0.0
        else:
            cov_s = 0.5  # no debt → moderate default

        if debt_to_capital is not None:
            if debt_to_capital < 0.30:
                lev_s = 1.0
            elif debt_to_capital < 0.50:
                lev_s = 0.6
            elif debt_to_capital < 0.70:
                lev_s = 0.3
            else:
                lev_s = 0.0
        else:
            lev_s = 0.5

        p7 = cov_s * 0.6 + lev_s * 0.4

        if coverage is not None and debt_to_capital is not None:
            d7 = (
                f"Interest coverage {coverage:.1f}x, "
                f"debt-to-capital {debt_to_capital:.1%}"
            )
        elif coverage is not None:
            d7 = f"Interest coverage {coverage:.1f}x"
        elif debt_to_capital is not None:
            d7 = f"Debt-to-capital {debt_to_capital:.1%}"
        else:
            d7 = "Data unavailable"

        r7 = self._make_rule(
            name="Financial Risk",
            value=coverage,
            threshold=3.0,
            points_possible=15,
            description=d7,
            source=(
                "Investment Valuation, Ch. 8: "
                "synthetic rating based on interest coverage"
            ),
            passed=p7 > 0,
            partial=p7,
            explanation=(
                "Bottom-up risk assessment via interest coverage "
                "and leverage"
            ),
        )
        rules.append(r7)
        if coverage is not None and coverage < 1.5:
            red_flags.append(
                f"Dangerously low interest coverage of {coverage:.1f}x "
                f"— distress risk"
            )

        return self._build_result(rules, red_flags)
