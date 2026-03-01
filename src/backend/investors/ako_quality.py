"""
AKO Capital — Quality Investing scoring module.

Based on "Quality Investing: Owning the Best Companies for the Long Term"
by Lawrence Cunningham, Torkell Eide & Patrick Hargreaves (Harriman House, 2016).

AKO Capital's core thesis — the virtuous circle:
  Strong cash generation → Reinvested at high ROIC → More cash → Repeat

Three pillars (all must hold):
  1. Strong, predictable cash generation
  2. Sustainably high returns on capital (ROIC/ROCE consistently >15%)
  3. Attractive reinvestment opportunities at those high rates

Key distinctions from other quality investors:
  - Quality first, price second (best margin of safety = depth of moat, not low price)
  - Consistency of ROIC matters more than the average
  - Prefers CROCI (cash-based) over accounting ROIC
  - Industry structure matters: oligopoly or better required
  - Three hard pitfalls to avoid: cyclicality, tech disruption, dependency

Sources:
  - Cunningham, Eide & Hargreaves (2016) — "Quality Investing", Harriman House
  - AKO Capital investment approach (akocapital.com)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class AKOQualityInvestor(BaseInvestor):
    """
    AKO Capital / Quality Investing scoring.
    Measures the three pillars: high sustained ROIC, predictable cash generation,
    strong margins as evidence of competitive advantage, and revenue consistency.
    """

    @property
    def name(self) -> str:
        return "AKO Quality"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: Sustained ROIC > 15% (consistency required) — 25 pts ──
        # The primary quality signal. AKO stresses that consistency matters more
        # than the average: a company earning 40% one year and -10% the next is
        # rejected despite a 15% mean, because it destroys value in down years.
        # Source: Building Blocks chapter — "Return on Capital"
        roic_series = data.roic_series
        roic_avg = statistics.mean(roic_series) if roic_series else None
        roic_consistent = (
            roic_avg is not None
            and roic_avg > 0.15
            and all(r > 0 for r in roic_series)  # every year must be positive
        )
        r1 = self._make_rule(
            name="Sustained ROIC > 15% (every year positive)",
            value=roic_avg * 100 if roic_avg is not None else None,
            threshold=15.0,
            points_possible=25.0,
            description=(
                f"ROIC avg = {roic_avg * 100:.1f}% across {len(roic_series)} years — "
                f"{'consistent compounder' if roic_consistent else 'inconsistent or below threshold'}"
                if roic_avg is not None else "ROIC data unavailable"
            ),
            source="Cunningham et al. (2016) — 'consistency matters more than the average'",
            passed=roic_consistent,
            explanation="ROIC consistency is AKO's primary quality screen. Every year must be positive: a company earning 40% in good years but destroying capital in bad years is a cyclical business in disguise. The compounding flywheel only works if returns are stable through all conditions.",
        )
        rules.append(r1)
        if not r1.passed and roic_series and any(r < 0 for r in roic_series):
            red_flags.append(
                "Negative ROIC in at least one year — AKO rejects businesses that "
                "destroy capital in downturns regardless of the multi-year average"
            )

        # ── Rule 2: Gross Margin > 40% — 20 pts ───────────────────────────
        # "The purest expression of customer valuation of a product."
        # High, stable gross margins are the primary screen for pricing power and
        # competitive advantage. They reveal whether customers genuinely value the
        # product enough to pay a premium.
        # Source: Building Blocks — "Return on Capital" and competitive moat analysis
        gm_series = data.gross_margin_series
        gm_avg = statistics.mean(gm_series) if gm_series else None
        r2 = self._make_rule(
            name="Gross Margin > 40% (pricing power evidence)",
            value=gm_avg * 100 if gm_avg is not None else None,
            threshold=40.0,
            points_possible=20.0,
            description=(
                f"Gross margin avg = {gm_avg * 100:.1f}% — "
                f"{'strong pricing power and competitive moat' if gm_avg and gm_avg > 0.40 else 'below quality threshold'}"
                if gm_avg is not None else "Gross margin data unavailable"
            ),
            source="Cunningham et al. (2016) — 'gross margin is the purest expression of "
                   "customer valuation'",
            explanation="AKO describes gross margin as 'the purest expression of customer valuation of a product.' When customers consistently pay a large premium over variable production costs, it proves genuine product differentiation. AKO's pattern companies (Hermès, Novo Nordisk, KONE) sustain high gross margins across cycles.",
        )
        rules.append(r2)
        if not r2.passed and gm_avg is not None and gm_avg < 0.20:
            red_flags.append(
                f"Gross margin of {gm_avg * 100:.1f}% signals commodity-like competition "
                f"with no pricing power — the antithesis of a quality compounder"
            )

        # ── Rule 3: FCF Conversion > 80% (FCF / Net Income) — 20 pts ──────
        # AKO prefers CROCI (Cash Return on Capital Invested) over accounting
        # ROIC precisely because cash conversion quality reveals whether reported
        # earnings are real. FCF / Net Income > 80% confirms earnings quality.
        # Source: Building Blocks — "Strong, predictable cash generation"
        fcf_series = data.free_cash_flow_series
        ni_series = data.net_income_series
        fcf_conversion = None
        n = min(len(fcf_series), len(ni_series))
        if n >= 2:
            # Use average of available years, filtering out years with negative net income
            pairs = [
                (fcf_series[i], ni_series[i])
                for i in range(-min(n, 5), 0)
                if ni_series[i] > 0
            ]
            if pairs:
                ratios = [f / ni for f, ni in pairs]
                fcf_conversion = statistics.mean(ratios) * 100  # as %

        r3 = self._make_rule(
            name="FCF Conversion > 80% (earnings quality)",
            value=fcf_conversion,
            threshold=80.0,
            points_possible=20.0,
            description=(
                f"FCF/Net Income = {fcf_conversion:.1f}% — "
                f"{'cash earnings match reported profits' if fcf_conversion and fcf_conversion > 80 else 'accrual gap raises earnings quality concern'}"
                if fcf_conversion is not None else "FCF conversion data unavailable"
            ),
            source="Cunningham et al. (2016) — prefer CROCI over accounting ROIC; "
                   "cash conversion validates earnings quality",
            explanation="AKO prefers CROCI (Cash Return on Capital Invested) over accounting ROIC because reported earnings can be manipulated. FCF as a % of Net Income above 80% confirms the company is collecting actual cash, not just recording receivables or deferrals — the earnings are real and repeatable.",
        )
        rules.append(r3)
        if not r3.passed and fcf_conversion is not None and fcf_conversion < 50:
            red_flags.append(
                f"FCF conversion of {fcf_conversion:.1f}% — large gap between reported "
                f"profits and real cash suggests aggressive accrual accounting"
            )

        # ── Rule 4: Revenue Growth Consistency ≥4/5 years positive — 15 pts
        # Quality companies grow consistently. AKO requires multiple concurrent
        # growth sources (market share + geographic + pricing/mix + market growth).
        # Revenue consistency is the simplest proxy for durable competitive advantage.
        # Source: Building Block 3 — "Multiple Sources of Growth"
        rev_series = data.revenue_series
        growth_years = 0
        total_years = 0
        if len(rev_series) >= 3:
            recent = rev_series[-5:] if len(rev_series) >= 5 else rev_series
            for i in range(1, len(recent)):
                total_years += 1
                if recent[i] > recent[i - 1]:
                    growth_years += 1
        growth_consistent = total_years >= 3 and growth_years >= (total_years - 1)

        r4 = self._make_rule(
            name=f"Consistent Revenue Growth (≥{total_years - 1 if total_years else 4}/{total_years if total_years else 5} years positive)",
            value=float(growth_years) if total_years > 0 else None,
            threshold=float(total_years - 1) if total_years > 0 else 4.0,
            points_possible=15.0,
            description=(
                f"{growth_years}/{total_years} years of revenue growth — "
                f"{'consistent compounder with multiple growth sources' if growth_consistent else 'revenue growth too lumpy for a quality compounder'}"
                if total_years > 0 else "Revenue series too short"
            ),
            source="Cunningham et al. (2016) — Building Block 3: multiple concurrent growth engines",
            passed=growth_consistent if total_years > 0 else None,
            explanation="AKO's 'Multiple Sources of Growth' framework requires concurrent growth drivers: market share gains, geographic expansion, pricing power, and underlying market growth. Consistent annual revenue growth across most years is the simplest proxy for this multi-engine growth model.",
        )
        rules.append(r4)

        # ── Rule 5: Operating Margin > 15% — 10 pts ───────────────────────
        # High operating margins signal scale advantages and efficiency that
        # smaller competitors cannot match. AKO's pattern companies (KONE,
        # Hermès, Novo Nordisk) consistently post operating margins well above
        # their industries. Sustained margin expansion is a strong quality signal.
        # Source: Building Blocks — industry structure and customer benefits
        op_series = data.operating_income_series
        rev_for_margin = data.revenue_series
        op_margins = []
        n_op = min(len(op_series), len(rev_for_margin))
        for i in range(n_op):
            if rev_for_margin[i] > 0:
                op_margins.append(op_series[i] / rev_for_margin[i])
        op_margin_avg = statistics.mean(op_margins) if op_margins else None

        r5 = self._make_rule(
            name="Operating Margin > 15% (scale + efficiency moat)",
            value=op_margin_avg * 100 if op_margin_avg is not None else None,
            threshold=15.0,
            points_possible=10.0,
            description=(
                f"Operating margin avg = {op_margin_avg * 100:.1f}% — "
                f"{'scale and efficiency advantage over competitors' if op_margin_avg and op_margin_avg > 0.15 else 'margins too thin for quality classification'}"
                if op_margin_avg is not None else "Operating margin data unavailable"
            ),
            source="Cunningham et al. (2016) — quality pattern companies sustain high "
                   "operating margins across economic cycles",
            explanation="High operating margins (above 15%) signal that the company has scale advantages and cost efficiency that smaller competitors cannot match. AKO's pattern companies maintain high operating margins throughout economic cycles — proving the advantage is structural rather than a cyclical tailwind.",
        )
        rules.append(r5)
        if not r5.passed and op_margin_avg is not None and op_margin_avg < 0:
            red_flags.append(
                "Negative operating margins — AKO explicitly avoids companies that "
                "cannot sustain profitability through the cycle"
            )

        # ── Rule 6: Low Financial Leverage (D/E < 1.0) — 10 pts ──────────
        # AKO explicitly warns: "substantial financial debt combined with high
        # operational leverage" destroys quality. The compounding effect only works
        # if the business can reinvest and grow without being vulnerable to downturns.
        # Quality companies should not need leverage to generate excellent returns.
        # Source: Pitfalls chapter — financial leverage as a compounding destroyer
        de_raw = self._safe(data.info.get("debtToEquity"))
        de_ratio = de_raw / 100.0 if de_raw is not None else None
        r6 = self._make_rule(
            name="Low Financial Leverage (D/E < 1.0)",
            value=de_ratio,
            threshold=1.0,
            points_possible=10.0,
            description=(
                f"D/E = {de_ratio:.2f}x — "
                f"{'conservative balance sheet supports long-run compounding' if de_ratio < 1.0 else 'leverage creates vulnerability; disrupts the virtuous circle'}"
                if de_ratio is not None else "Debt/equity data unavailable"
            ),
            source="Cunningham et al. (2016) — 'avoid financial debt combined with "
                   "operational leverage; quality companies need no leverage'",
            passed=de_ratio < 1.0 if de_ratio is not None else None,
            explanation="AKO warns explicitly about 'substantial financial debt combined with operational leverage.' Quality compounders should generate returns without needing debt — their model produces the capital required for reinvestment internally. Leverage adds fragility that can break the virtuous compounding circle in downturns.",
        )
        rules.append(r6)
        if not r6.passed and de_ratio is not None and de_ratio > 2.0:
            red_flags.append(
                f"D/E of {de_ratio:.1f}x — high leverage combined with operating exposure "
                f"is AKO's explicit pitfall; it destroys the virtuous compounding circle in downturns"
            )

        return self._build_result(rules, red_flags)
