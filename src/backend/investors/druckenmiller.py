"""
Stanley Druckenmiller scoring module.

Rules based on:
- "The New Market Wizards" by Jack Schwager (1992) — Druckenmiller interview
- Public interviews and conference talks (Sohn, Ira Sohn, CNBC)
- Duquesne Capital track record analysis (1986–2010, ~30% annualised)

Druckenmiller's core philosophy:
  1. Earnings growth and acceleration are the primary drivers of stock returns
  2. Pay up for growth — valuation matters only relative to the growth rate
  3. Look forward 18–24 months; buy inflection points before the market sees them
  4. Preserve capital, then go for the jugular on high-conviction ideas
  5. Price momentum confirms the fundamental thesis
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class DruckenmillerInvestor(BaseInvestor):
    """
    Stanley Druckenmiller scoring: macro growth with earnings acceleration.
    Emphasis on EPS/revenue growth trajectories, margin expansion, and momentum.
    """

    @property
    def name(self) -> str:
        return "Druckenmiller"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: Earnings Growth > 15% CAGR — 15 pts ─────────────────────
        # "Earnings are the most important factor driving stocks."
        eps_growth = data.eps_growth_rate_annual
        r1 = self._make_rule(
            name="EPS Growth > 15% CAGR",
            value=eps_growth * 100 if eps_growth is not None else None,
            threshold=15.0,
            points_possible=15.0,
            description=(
                f"EPS CAGR = {eps_growth*100:.1f}%"
                if eps_growth is not None else "EPS growth data unavailable"
            ),
            source="Schwager, 'The New Market Wizards' — earnings as primary driver",
            explanation=(
                "Druckenmiller considers earnings growth the single most important "
                "factor driving stock prices. A CAGR above 15% signals strong "
                "fundamental momentum — the kind of growth trajectory that attracts "
                "institutional capital and sustains price appreciation."
            ),
        )
        rules.append(r1)
        if eps_growth is not None and eps_growth < 0:
            red_flags.append(
                f"EPS declining at {eps_growth*100:.1f}% — negative earnings momentum"
            )

        # ── Rule 2: Earnings Acceleration — 12 pts ──────────────────────────
        # Druckenmiller looks for the growth rate itself to be increasing.
        # Compare second-half CAGR vs first-half CAGR of the EPS series.
        eps_series = data.eps_series
        accel_pass = None
        accel_desc = "Insufficient EPS history for acceleration analysis"
        accel_value = None
        if len(eps_series) >= 4:
            mid = len(eps_series) // 2
            early = eps_series[:mid + 1]
            late = eps_series[mid:]
            early_growth = None
            late_growth = None
            if early[0] > 0 and early[-1] > 0 and len(early) > 1:
                early_growth = (early[-1] / early[0]) ** (1 / (len(early) - 1)) - 1
            if late[0] > 0 and late[-1] > 0 and len(late) > 1:
                late_growth = (late[-1] / late[0]) ** (1 / (len(late) - 1)) - 1
            if early_growth is not None and late_growth is not None:
                accel_pass = late_growth > early_growth
                accel_value = (late_growth - early_growth) * 100
                accel_desc = (
                    f"Recent EPS growth {late_growth*100:.1f}% vs earlier "
                    f"{early_growth*100:.1f}% — "
                    f"{'accelerating' if accel_pass else 'decelerating'}"
                )
        r2 = self._make_rule(
            name="Earnings Acceleration (recent > earlier growth)",
            value=accel_value,
            threshold=0.0,
            points_possible=12.0,
            description=accel_desc,
            source="Druckenmiller interviews — 'look for the rate of change to improve'",
            passed=accel_pass,
            explanation=(
                "Druckenmiller doesn't just want growth — he wants accelerating "
                "growth. A company whose earnings growth rate is increasing signals "
                "an inflection point, often 18-24 months before the market fully "
                "recognises the improvement. Deceleration is an early exit signal."
            ),
        )
        rules.append(r2)

        # ── Rule 3: Revenue Growth > 10% CAGR — 15 pts ─────────────────────
        # Top-line growth confirms real demand, not just cost cuts or buybacks.
        rev_series = data.revenue_series
        rev_cagr = None
        if len(rev_series) >= 2 and rev_series[0] > 0 and rev_series[-1] > 0:
            rev_cagr = (
                (rev_series[-1] / rev_series[0]) ** (1 / (len(rev_series) - 1)) - 1
            )
        r3 = self._make_rule(
            name="Revenue Growth > 10% CAGR",
            value=rev_cagr * 100 if rev_cagr is not None else None,
            threshold=10.0,
            points_possible=15.0,
            description=(
                f"Revenue CAGR = {rev_cagr*100:.1f}% over {len(rev_series)} years"
                if rev_cagr is not None else "Revenue growth data unavailable"
            ),
            source="Druckenmiller — organic top-line growth validates demand",
            explanation=(
                "Druckenmiller insists on real top-line growth, not earnings "
                "manufactured through buybacks or cost-cutting alone. Revenue "
                "growing above 10% annually proves genuine demand expansion — a "
                "prerequisite for sustainable earnings growth."
            ),
        )
        rules.append(r3)

        # ── Rule 4: Revenue Acceleration — 8 pts ────────────────────────────
        rev_accel_pass = None
        rev_accel_desc = "Insufficient revenue history for acceleration analysis"
        rev_accel_value = None
        if len(rev_series) >= 4:
            mid = len(rev_series) // 2
            early_rev = rev_series[:mid + 1]
            late_rev = rev_series[mid:]
            early_rev_g = None
            late_rev_g = None
            if early_rev[0] > 0 and early_rev[-1] > 0 and len(early_rev) > 1:
                early_rev_g = (
                    (early_rev[-1] / early_rev[0]) ** (1 / (len(early_rev) - 1)) - 1
                )
            if late_rev[0] > 0 and late_rev[-1] > 0 and len(late_rev) > 1:
                late_rev_g = (
                    (late_rev[-1] / late_rev[0]) ** (1 / (len(late_rev) - 1)) - 1
                )
            if early_rev_g is not None and late_rev_g is not None:
                rev_accel_pass = late_rev_g > early_rev_g
                rev_accel_value = (late_rev_g - early_rev_g) * 100
                rev_accel_desc = (
                    f"Recent revenue growth {late_rev_g*100:.1f}% vs earlier "
                    f"{early_rev_g*100:.1f}% — "
                    f"{'accelerating' if rev_accel_pass else 'decelerating'}"
                )
        r4 = self._make_rule(
            name="Revenue Acceleration (recent > earlier growth)",
            value=rev_accel_value,
            threshold=0.0,
            points_possible=8.0,
            description=rev_accel_desc,
            source="Druckenmiller — top-line acceleration confirms inflection",
            passed=rev_accel_pass,
            explanation=(
                "Revenue acceleration — the growth rate itself increasing — is a "
                "powerful signal that the company is gaining market share or entering "
                "a new growth phase. Druckenmiller tries to identify these inflection "
                "points 18-24 months before the market catches on."
            ),
        )
        rules.append(r4)

        # ── Rule 5: FCF Margin > 10% — 10 pts ──────────────────────────────
        # Strong FCF validates that reported earnings are real.
        fcf_margin_series = data.fcf_margin_series
        fcf_margin_avg = (
            statistics.mean(fcf_margin_series) if fcf_margin_series else None
        )
        fcf_series = data.free_cash_flow_series
        fcf_growing = None
        if len(fcf_series) >= 2:
            fcf_growing = fcf_series[-1] > fcf_series[0]

        fcf_desc = "FCF data unavailable"
        fcf_pass = None
        if fcf_margin_avg is not None:
            fcf_pass = fcf_margin_avg > 0.10
            growth_str = ""
            if fcf_growing is not None:
                growth_str = f", {'growing' if fcf_growing else 'declining'} FCF"
            fcf_desc = f"Avg FCF margin = {fcf_margin_avg*100:.1f}%{growth_str}"

        r5 = self._make_rule(
            name="FCF Margin > 10% (real earnings)",
            value=fcf_margin_avg * 100 if fcf_margin_avg is not None else None,
            threshold=10.0,
            points_possible=10.0,
            description=fcf_desc,
            source="Druckenmiller — FCF validates earnings quality",
            passed=fcf_pass,
            explanation=(
                "Strong free cash flow generation confirms that reported earnings "
                "translate into real cash. An FCF margin above 10% indicates a "
                "capital-efficient business model where growth doesn't consume "
                "all the cash — the kind of business that can self-fund expansion."
            ),
        )
        rules.append(r5)
        if fcf_margin_avg is not None and fcf_margin_avg < 0:
            red_flags.append(
                f"Negative FCF margin of {fcf_margin_avg*100:.1f}% — business burns cash"
            )

        # ── Rule 6: Operating Margin Expansion — 10 pts ─────────────────────
        # Expanding margins signal operating leverage and competitive strength.
        op_inc_series = data.operating_income_series
        op_margin_series = []
        n = min(len(op_inc_series), len(rev_series))
        for i in range(n):
            if rev_series[i] > 0:
                op_margin_series.append(op_inc_series[i] / rev_series[i])

        margin_expanding = None
        margin_desc = "Insufficient margin data"
        margin_value = None
        if len(op_margin_series) >= 3:
            mid = len(op_margin_series) // 2
            first_half = statistics.mean(op_margin_series[:mid + 1])
            second_half = statistics.mean(op_margin_series[mid:])
            margin_expanding = second_half > first_half
            margin_value = (second_half - first_half) * 100
            margin_desc = (
                f"Operating margin: earlier avg {first_half*100:.1f}% → "
                f"recent avg {second_half*100:.1f}% — "
                f"{'expanding' if margin_expanding else 'contracting'}"
            )

        r6 = self._make_rule(
            name="Operating Margin Expansion",
            value=margin_value,
            threshold=0.0,
            points_possible=10.0,
            description=margin_desc,
            source="Druckenmiller — expanding margins signal operating leverage",
            passed=margin_expanding,
            explanation=(
                "Expanding operating margins prove that revenue growth translates "
                "into disproportionate profit growth — operating leverage in action. "
                "This is the hallmark of a business gaining competitive strength, "
                "not just growing by throwing more capital at the problem."
            ),
        )
        rules.append(r6)
        if margin_expanding is False and margin_value is not None and margin_value < -3:
            red_flags.append(
                f"Operating margins contracting by {abs(margin_value):.1f}pp — "
                f"growth may be coming at the expense of profitability"
            )

        # ── Rule 7: ROE > 15% — 10 pts ──────────────────────────────────────
        # Falls back to ROIC when equity is negative (buyback-heavy companies).
        roe_series = data.roe_series
        ret_series = roe_series
        ret_label = "ROE"
        if not roe_series:
            roic_s = data.roic_series
            if roic_s:
                ret_series = roic_s
                ret_label = "ROIC"
        ret_avg = statistics.mean(ret_series) if ret_series else None
        r7 = self._make_rule(
            name="ROE > 15% (capital efficiency)",
            value=ret_avg * 100 if ret_avg is not None else None,
            threshold=15.0,
            points_possible=10.0,
            description=(
                f"Avg {ret_label} = {ret_avg*100:.1f}% across {len(ret_series)} years"
                + (" (ROIC fallback — negative equity)" if ret_label == "ROIC" else "")
                if ret_avg is not None else "Data unavailable"
            ),
            source="Druckenmiller — high ROE signals efficient capital allocation",
            explanation=(
                "Return on Equity measures how efficiently a company converts "
                "shareholder capital into profits. ROE above 15% indicates the "
                "business earns well above its cost of equity — a sign of "
                "competitive advantage and efficient capital deployment. "
                "Falls back to ROIC for companies with negative equity."
            ),
        )
        rules.append(r7)

        # ── Rule 8: Valuation Relative to Growth (PEG < 2.0) — 10 pts ──────
        # Druckenmiller will pay up for growth but still wants some discipline.
        peg = data.peg_ratio
        r8 = self._make_rule(
            name="PEG Ratio < 2.0 (not overpaying for growth)",
            value=peg,
            threshold=2.0,
            points_possible=10.0,
            description=(
                f"PEG = {peg:.2f} — "
                f"{'reasonable for growth' if peg and peg < 2.0 else 'expensive relative to growth'}"
                if peg is not None else "PEG unavailable"
            ),
            source="Druckenmiller — will pay up for growth but avoids extreme overvaluation",
            passed=peg < 2.0 if peg is not None else None,
            explanation=(
                "Unlike strict value investors, Druckenmiller will pay a premium "
                "for genuine growth. But even he has limits — a PEG above 2.0 "
                "means the market is pricing in more growth than is reasonably "
                "achievable. He evaluates P/E relative to growth rate, not P/E "
                "in isolation."
            ),
        )
        rules.append(r8)
        if peg is not None and peg > 3.0:
            red_flags.append(
                f"PEG of {peg:.1f} — extreme overvaluation relative to growth"
            )

        # ── Rule 9: Balance Sheet Strength (D/E < 1.0) — 5 pts ─────────────
        de = data.debt_to_equity
        de_value = de
        if de is not None and de > 10:
            de_value = de / 100  # yfinance sometimes returns as percentage
        r9 = self._make_rule(
            name="Debt-to-Equity < 1.0 (manageable leverage)",
            value=de_value,
            threshold=1.0,
            points_possible=5.0,
            description=(
                f"D/E = {de_value:.2f}x"
                if de_value is not None else "D/E data unavailable"
            ),
            source="Druckenmiller — capital preservation requires manageable debt",
            passed=de_value < 1.0 if de_value is not None else None,
            explanation=(
                "While not a balance-sheet-first investor, Druckenmiller recognises "
                "that excessive debt constrains flexibility and amplifies downside "
                "risk. A D/E below 1.0 ensures the company can survive macro shocks "
                "and continue investing in growth during tightening liquidity cycles."
            ),
        )
        rules.append(r9)
        if de_value is not None and de_value > 2.0:
            red_flags.append(
                f"D/E of {de_value:.1f}x — dangerous leverage in a tightening cycle"
            )

        # ── Rule 10: Price Momentum (12-month return > 0%) — 5 pts ──────────
        # "I use technical analysis as a confirming signal."
        return_12m = data.price_return_12m
        r10 = self._make_rule(
            name="Positive Price Momentum (12-month return > 0%)",
            value=return_12m * 100 if return_12m is not None else None,
            threshold=0.0,
            points_possible=5.0,
            description=(
                f"12-month return = {return_12m*100:.1f}%"
                if return_12m is not None else "Price history insufficient"
            ),
            source="Druckenmiller — price momentum confirms the fundamental thesis",
            explanation=(
                "Druckenmiller uses price action as a confirming signal. Positive "
                "12-month momentum suggests the market is already recognising the "
                "improving fundamentals. He prefers to buy stocks in uptrends with "
                "improving fundamentals, not falling knives."
            ),
        )
        rules.append(r10)
        if return_12m is not None and return_12m < -0.30:
            red_flags.append(
                f"12-month return of {return_12m*100:.1f}% — severe negative "
                f"momentum, potential fundamental deterioration"
            )

        return self._build_result(rules, red_flags)
