"""
Terry Smith scoring module.

Rules based on:
- Fundsmith Equity Fund annual letters (2010–present)
- "Investing for Growth" by Terry Smith (2020)
- Fundsmith investment criteria: buy good companies, don't overpay, do nothing.

Terry Smith's 3-step philosophy:
  1. Buy good companies (high quality, durable, asset-light)
  2. Don't overpay
  3. Do nothing (low turnover, very long hold periods)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class TerrySmithInvestor(BaseInvestor):
    """
    Terry Smith scoring: exceptional quality businesses at sensible prices.
    Emphasis on ROCE, gross margins, cash conversion, and organic growth.
    """

    @property
    def name(self) -> str:
        return "Terry Smith"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: ROCE > 15% sustained — 25 pts ─────────────────────────
        # "We look for companies with a high return on capital employed and
        #  which can deploy more capital at those high returns." — Fundsmith 2020
        # ROCE ≈ ROIC in our model (Operating Income * (1-tax) / Invested Capital)
        roic_series = data.roic_series
        roic_avg = statistics.mean(roic_series) if roic_series else None
        # Terry Smith sets a higher bar than Buffett — consistent >20% preferred
        r1 = self._make_rule(
            name="ROCE > 15% (sustained)",
            value=roic_avg * 100 if roic_avg is not None else None,
            threshold=15.0,
            points_possible=25.0,
            description=(
                f"Avg ROCE = {roic_avg*100:.1f}% across {len(roic_series)} years"
                if roic_avg is not None else "No ROCE data available"
            ),
            source="Fundsmith Annual Letters; 'Investing for Growth' (2020)",
            explanation="Return on Capital Employed (ROCE) measures operating profit relative to total capital used. Sustained ROCE above 15% every year proves the business consistently earns well above its cost of capital — the prerequisite for the quality compounders Terry Smith seeks.",
        )
        rules.append(r1)
        if r1.passed and roic_avg is not None and roic_avg < 0.20:
            # Pass but note it's below Terry's preferred 20%+ threshold
            pass
        if not r1.passed and roic_avg is not None and roic_avg < 0.10:
            red_flags.append(
                f"ROCE of {roic_avg*100:.1f}% is well below Fundsmith's minimum — "
                f"business does not earn adequate returns on capital"
            )

        # ── Rule 2: Gross Margin > 40% — 20 pts ───────────────────────────
        # High gross margins signal pricing power and a durable competitive moat.
        # Terry Smith specifically avoids low-margin, commoditised businesses.
        gm_series = data.gross_margin_series
        gm_avg = statistics.mean(gm_series) if gm_series else None
        r2 = self._make_rule(
            name="Gross Margin > 40%",
            value=gm_avg * 100 if gm_avg is not None else None,
            threshold=40.0,
            points_possible=20.0,
            description=(
                f"Avg gross margin = {gm_avg*100:.1f}%"
                if gm_avg is not None else "Gross margin data unavailable"
            ),
            source="Fundsmith Annual Letters — pricing power filter",
            explanation="Gross margin (revenue minus cost of goods sold, as a % of revenue) is the most direct measure of pricing power. Above 40% means customers pay a substantial premium over variable costs — evidence of genuine competitive differentiation that a commoditised business cannot achieve.",
        )
        rules.append(r2)
        if not r2.passed:
            if gm_avg is not None and gm_avg < 0.20:
                red_flags.append(
                    f"Gross margin of {gm_avg*100:.1f}% signals a commoditised, "
                    f"low-quality business — Terry Smith would not invest"
                )
            elif gm_avg is not None:
                red_flags.append(
                    f"Gross margin {gm_avg*100:.1f}% is below the 40% quality threshold"
                )

        # ── Rule 3: Operating Cash Conversion > 80% — 20 pts ──────────────
        # "We want companies whose profits are real — where FCF closely tracks
        #  reported earnings." — Fundsmith Investor Day 2018
        # Cash conversion = Operating Cash Flow / Operating Income
        ocf_series = data.operating_cash_flow_series
        op_inc_series = data.operating_income_series
        conversion_rates = []
        n = min(len(ocf_series), len(op_inc_series))
        for i in range(n):
            if op_inc_series[i] > 0:
                conversion_rates.append(ocf_series[i] / op_inc_series[i])
        conversion_avg = statistics.mean(conversion_rates) if conversion_rates else None

        r3 = self._make_rule(
            name="Cash Conversion > 80% (OCF / Operating Income)",
            value=conversion_avg * 100 if conversion_avg is not None else None,
            threshold=80.0,
            points_possible=20.0,
            description=(
                f"Avg cash conversion = {conversion_avg*100:.1f}%"
                if conversion_avg is not None else "Cash conversion data unavailable"
            ),
            source="Fundsmith Investor Day 2018 — 'profits must be real'",
            explanation="Cash conversion measures whether reported profits convert into actual cash. If operating cash flow is less than 80% of operating income, earnings may be inflated by accruals or aggressive accounting. High conversion confirms profits are real and collectible.",
        )
        rules.append(r3)
        if not r3.passed and conversion_avg is not None and conversion_avg < 0.60:
            red_flags.append(
                f"Cash conversion of {conversion_avg*100:.1f}% suggests earnings quality "
                f"concerns — profits are not flowing through to cash"
            )

        # ── Rule 4: Consistent Revenue Growth (positive in 4 of 5 years) — 15 pts
        # Terry Smith wants companies with organic growth drivers, not stagnant businesses.
        # He doesn't require high growth — consistency matters more than speed.
        rev_series = data.revenue_series
        positive_growth_years = 0
        total_growth_years = 0
        if len(rev_series) >= 3:
            for i in range(1, len(rev_series)):
                total_growth_years += 1
                if rev_series[i] > rev_series[i - 1]:
                    positive_growth_years += 1
        consistency_ratio = (
            positive_growth_years / total_growth_years
            if total_growth_years > 0 else None
        )
        # Also compute revenue CAGR
        rev_cagr = None
        if len(rev_series) >= 2 and rev_series[0] > 0 and rev_series[-1] > 0:
            rev_cagr = (rev_series[-1] / rev_series[0]) ** (1 / (len(rev_series) - 1)) - 1

        r4 = self._make_rule(
            name="Consistent Revenue Growth (≥4 of 5 years positive)",
            value=consistency_ratio * 100 if consistency_ratio is not None else None,
            threshold=80.0,
            points_possible=15.0,
            description=(
                f"Revenue grew in {positive_growth_years}/{total_growth_years} years "
                f"(CAGR {rev_cagr*100:.1f}%)"
                if consistency_ratio is not None and rev_cagr is not None
                else "Insufficient revenue history"
            ),
            source="Fundsmith Annual Letters — organic growth filter",
            explanation="Terry Smith values consistency over speed. Revenue growing in at least 4 of 5 years proves the business has reliable organic demand — not a one-time beneficiary of a favourable cycle. Consistency is what allows compounding to work reliably over a 10-20 year hold.",
        )
        rules.append(r4)
        if not r4.passed and rev_series and rev_series[-1] < rev_series[0]:
            red_flags.append(
                "Revenue has declined from its starting level — "
                "business lacks organic growth drivers"
            )

        # ── Rule 5: Low capital intensity (CapEx / Revenue < 5%) — 10 pts ──
        # "We don't want capital-intensive businesses. The best businesses
        #  require minimal reinvestment to maintain their earnings power." — Fundsmith
        capex_series = data.capex_series
        rev_series_2 = data.revenue_series
        capex_intensity_values = []
        n2 = min(len(capex_series), len(rev_series_2))
        for i in range(n2):
            if rev_series_2[i] > 0:
                capex_intensity_values.append(capex_series[i] / rev_series_2[i])
        capex_intensity_avg = (
            statistics.mean(capex_intensity_values) if capex_intensity_values else None
        )

        r5 = self._make_rule(
            name="Low Capital Intensity (CapEx / Revenue < 5%)",
            value=capex_intensity_avg * 100 if capex_intensity_avg is not None else None,
            threshold=5.0,
            points_possible=10.0,
            description=(
                f"Avg CapEx/Revenue = {capex_intensity_avg*100:.1f}%"
                if capex_intensity_avg is not None else "CapEx data unavailable"
            ),
            source="Fundsmith — asset-light business model requirement",
            passed=capex_intensity_avg < 0.05 if capex_intensity_avg is not None else None,
            explanation="Capital intensity measures how much of revenue must be reinvested in physical assets. Businesses spending less than 5% on CapEx (software, brands, processes) convert most revenue into free cash. High CapEx businesses (factories, infrastructure) consume the cash that would otherwise compound.",
        )
        rules.append(r5)
        if not r5.passed and capex_intensity_avg is not None and capex_intensity_avg > 0.10:
            red_flags.append(
                f"CapEx intensity of {capex_intensity_avg*100:.1f}% is high — "
                f"capital-intensive business erodes free cash flow generation"
            )

        # ── Rule 6: Reasonable valuation — FCF Yield > 2% — 10 pts ────────
        # Terry Smith is NOT a deep-value investor but avoids extreme overvaluation.
        # He uses FCF yield as a primary valuation check (prefers 3–5%+).
        market_cap = data.market_cap
        fcf_series = data.free_cash_flow_series
        fcf_yield = None
        if fcf_series and market_cap and market_cap > 0:
            fcf_latest = fcf_series[-1]
            if fcf_latest > 0:
                fcf_yield = (fcf_latest / market_cap) * 100

        r6 = self._make_rule(
            name="FCF Yield > 2% (don't overpay)",
            value=fcf_yield,
            threshold=2.0,
            points_possible=10.0,
            description=(
                f"FCF yield = {fcf_yield:.1f}%"
                if fcf_yield is not None else "FCF yield unavailable"
            ),
            source="Fundsmith — 'don't overpay' pillar",
            explanation="Free Cash Flow Yield (latest FCF ÷ Market Cap) is Terry Smith's valuation check. He isn't a deep-value investor but requires at least 2% FCF yield to ensure the quality premium is not absurdly extreme. Below 1% means you are paying 100x+ FCF — almost no room for error.",
        )
        rules.append(r6)
        if not r6.passed and fcf_yield is not None and fcf_yield < 1.0:
            red_flags.append(
                f"FCF yield of {fcf_yield:.1f}% is extremely low — "
                f"even Terry Smith's quality-tolerant valuation filter rejects this price"
            )

        return self._build_result(rules, red_flags)
