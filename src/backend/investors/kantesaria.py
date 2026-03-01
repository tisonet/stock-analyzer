"""
Dev Kantesaria — Valley Forge Capital Management scoring module.

Kantesaria runs a highly concentrated portfolio of "compounding machines" —
capital-light businesses with high and stable ROIC (20%+), wide economic moats,
predictable recurring revenue streams, and long runways for reinvestment at
high rates of return. He is comfortable paying seemingly expensive multiples
for genuinely exceptional businesses.

Portfolio archetypes: MSCI, S&P Global, Fair Isaac (FICO), Verisk, Copart.
These share: 20%+ ROIC, 50%+ gross margins, <5% CapEx/Revenue, 25%+ FCF margins,
recurring/contractual revenue with low growth variance.

Core philosophy:
  - High and stable ROIC (ideally 20%+) is the foundational screen
  - Capital-light models: low capex frees cash for reinvestment at those high rates
  - Predictable, recurring/contracted revenue reduces compounding risk
  - Wide moats via network effects, switching costs, regulatory barriers, or scale
  - Comfortable paying high multiples — quality compounders are rarely truly cheap
  - Long runway: high ROIC × meaningful revenue growth = exponential compounding

Sources:
  - Valley Forge Capital Management annual letters
  - Kantesaria, Sohn Conference presentations (2016, 2019)
  - Kantesaria, MOI Global interview (2020)
  - Kantesaria, Invest Like the Best podcast (2020)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class KantesariaInvestor(BaseInvestor):
    """
    Dev Kantesaria / Valley Forge Capital Management scoring.
    Seeks capital-light compounding machines: ROIC consistently above 20%,
    wide-moat gross margins (50%+), asset-light capex (<5% of revenue),
    strong FCF margins (>20%), meaningful and predictable revenue growth.
    """

    @property
    def name(self) -> str:
        return "Kantesaria"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: ROIC > 20% (every year positive, consistent) — 25 pts ──
        # Kantesaria's primary and non-negotiable screen. He targets businesses
        # earning 20%+ ROIC — well above the ~9-10% cost of capital — and demands
        # consistency. A business that earns 30% one year and 5% the next fails
        # his test even if the average is fine, because cyclical ROIC cannot sustain
        # the compounding thesis or justify a premium multiple.
        # The gap between ROIC and cost of capital is the source of all economic value
        # creation; 20%+ sustained compounds faster than any financial engineering.
        # Source: Kantesaria, MOI Global (2020) — "ROIC is the fundamental driver
        # of long-run equity returns; I want to see 20%+ every single year"
        roic_series = data.roic_series
        roic_avg = statistics.mean(roic_series) if roic_series else None
        roic_consistent = (
            roic_avg is not None
            and roic_avg > 0.20
            and all(r > 0 for r in roic_series)
        )
        r1 = self._make_rule(
            name="ROIC > 20% (every year positive)",
            value=roic_avg * 100 if roic_avg is not None else None,
            threshold=20.0,
            points_possible=25.0,
            description=(
                f"ROIC avg = {roic_avg * 100:.1f}% across {len(roic_series)} years — "
                f"{'sustained compounder; capital deployed at rates far above cost of capital' if roic_consistent else 'does not meet the 20%+ bar required for a compounding machine'}"
                if roic_avg is not None
                else "ROIC data unavailable"
            ),
            source=(
                "Kantesaria (MOI Global, 2020) — 'ROIC is the fundamental driver "
                "of long-run equity returns; I need 20%+ consistently, every year'"
            ),
            passed=roic_consistent,
            explanation="Kantesaria's non-negotiable primary screen: ROIC must exceed 20% — more than double the typical cost of capital (~9-10%) — and must be positive every single year. The sustained gap between ROIC and cost of capital is the entire source of long-run value creation; cyclical businesses that occasionally hit 20% do not compound.",
        )
        rules.append(r1)
        if not r1.passed and roic_series and any(r < 0 for r in roic_series):
            red_flags.append(
                "Negative ROIC in at least one year — a business that destroys capital "
                "in adverse conditions cannot be a compounding machine; Kantesaria "
                "requires positive ROIC through the full cycle, not just on average"
            )
        if not r1.passed and roic_avg is not None and roic_avg < 0.12:
            red_flags.append(
                f"ROIC of {roic_avg * 100:.1f}% barely exceeds cost of capital — "
                "there is no meaningful compounding advantage over a passive index at this level"
            )

        # ── Rule 2: Gross Margin > 50% (or Operating Margin > 25%) — 20 pts
        # Gross margin is the most transparent measure of competitive moat.
        # Businesses with network effects, switching costs, or regulatory barriers
        # all register as high and stable gross margins. Kantesaria's portfolio
        # companies (MSCI ~85%, FICO ~75%, S&P Global ~65%, Verisk ~60%) all sit
        # far above the 50% threshold.
        #
        # NOTE — fallback for platform/marketplace companies (e.g. BKNG, EXPE, ABNB):
        # yfinance does not report a "Gross Profit" line for businesses that have no
        # meaningful COGS (their revenue IS essentially gross profit). For these
        # companies we fall back to operating margin > 25% as a quality proxy —
        # a platform earning 25%+ operating margin has the same economic character
        # as a traditional business with 50%+ gross margin.
        # Source: VGC portfolio analysis — all core holdings consistently exceed 50% GM
        gm_series = data.gross_margin_series
        gm_avg = statistics.mean(gm_series) if gm_series else None

        if gm_avg is not None:
            # Gross profit data available — use it directly
            r2_name = "Gross Margin > 50% (moat: pricing power + switching costs)"
            r2_value = gm_avg * 100
            r2_threshold = 50.0
            r2_passed = gm_avg > 0.50
            if r2_passed:
                r2_desc = f"Gross margin avg = {gm_avg * 100:.1f}% — structural advantage: customers pay a durable premium over variable cost"
            else:
                r2_desc = f"Gross margin avg = {gm_avg * 100:.1f}% — insufficient for a moated compounder; VGC minimum is 50%+"
            r2_source = (
                "VGC portfolio — MSCI (~85%), FICO (~75%), S&P Global (~65%), "
                "Verisk (~60%) all sustain >50% gross margins as evidence of deep moat"
            )
        else:
            # No gross profit data (platform/marketplace business with no COGS line)
            # Fall back to operating margin as proxy
            op_s = data.operating_income_series
            rev_proxy = data.revenue_series
            n_op = min(len(op_s), len(rev_proxy))
            op_margins = [op_s[i] / rev_proxy[i] for i in range(n_op) if rev_proxy[i] > 0]
            op_avg = statistics.mean(op_margins) if op_margins else None
            r2_name = "Operating Margin > 25% (proxy: gross profit not reported by yfinance)"
            r2_value = op_avg * 100 if op_avg is not None else None
            r2_threshold = 25.0
            r2_passed = op_avg is not None and op_avg > 0.25
            if op_avg is not None:
                if r2_passed:
                    r2_desc = f"Operating margin avg = {op_avg * 100:.1f}% (gross profit not reported — platform/service business; operating margin used as quality proxy)"
                else:
                    r2_desc = f"Operating margin avg = {op_avg * 100:.1f}% — below 25% proxy threshold (gross profit not reported by yfinance)"
            else:
                r2_desc = "Neither gross profit nor operating margin data available"
            r2_source = (
                "Gross profit not reported by yfinance for this company type (platform/marketplace). "
                "Operating margin > 25% used as equivalent quality signal — VGC portfolio analysis"
            )

        r2 = self._make_rule(
            name=r2_name,
            value=r2_value,
            threshold=r2_threshold,
            points_possible=20.0,
            description=r2_desc,
            source=r2_source,
            passed=r2_passed,
            explanation="Gross margin is Kantesaria's primary moat indicator. Network effects, switching costs, and regulatory barriers all manifest as structurally high gross margins — customers pay a durable premium because they cannot or will not switch. His portfolio archetypes (MSCI ~85%, FICO ~75%) sit far above 50%.",
        )
        rules.append(r2)
        if not r2.passed and gm_avg is not None and gm_avg < 0.30:
            red_flags.append(
                f"Gross margin of {gm_avg * 100:.1f}% signals a commodity-like competitive "
                "position with no structural pricing power — the opposite of Kantesaria's "
                "compounding machine archetype (MSCI, FICO, Verisk)"
            )

        # ── Rule 3: Capital-Light: CapEx / Revenue < 5% — 15 pts ─────────
        # Capital-light models are the mechanical engine of Kantesaria's thesis.
        # If a business must constantly reinvest in physical assets — factories,
        # real estate, distribution infrastructure — to maintain or grow earnings,
        # free cash flow is consumed and cannot be redeployed at 20%+ rates.
        # MSCI and FICO spend <2% of revenue on capex; Verisk <4%. This is what
        # allows them to convert 80-90%+ of operating income into investable cash.
        # A business with >10% capex intensity almost certainly cannot sustain the
        # FCF margins required for the compounding flywheel.
        # Source: Kantesaria — "the capital-light model is what makes the compounding
        # sustainable; you want the business to grow without needing your capital back"
        capex_s = data.capex_series
        rev_s = data.revenue_series
        n_cr = min(len(capex_s), len(rev_s))
        capex_ratios: list[float] = []
        for i in range(max(0, n_cr - 4), n_cr):
            if rev_s[i] > 0:
                capex_ratios.append(capex_s[i] / rev_s[i])
        capex_intensity = statistics.mean(capex_ratios) if capex_ratios else None
        capital_light = capex_intensity is not None and capex_intensity < 0.05

        r3 = self._make_rule(
            name="Capital-Light: CapEx/Revenue < 5%",
            value=capex_intensity * 100 if capex_intensity is not None else None,
            threshold=5.0,
            points_possible=15.0,
            description=(
                f"CapEx/Revenue = {capex_intensity * 100:.1f}% (avg last {len(capex_ratios)} years) — "
                f"{'asset-light engine: minimal reinvestment keeps free cash flow high and redeployable' if capital_light else 'capital intensity too high; significant capex consumes the FCF that should compound'}"
                if capex_intensity is not None
                else "CapEx/Revenue data unavailable"
            ),
            source=(
                "Kantesaria — 'the capital-light model is what makes the compounding "
                "sustainable; MSCI and FICO spend <2% of revenue on capex'"
            ),
            passed=capital_light,
            explanation="Capital-light models are the mechanical engine of compounding. Businesses spending less than 5% of revenue on CapEx (like MSCI and FICO) can grow without returning to shareholders for new capital. High-CapEx businesses consume the free cash flow that should be redeployed at 20%+ rates.",
        )
        rules.append(r3)
        if not r3.passed and capex_intensity is not None and capex_intensity > 0.15:
            red_flags.append(
                f"CapEx/Revenue of {capex_intensity * 100:.1f}% — heavy capital intensity "
                "consumes the free cash flow that a compounding machine should be generating; "
                "this pattern is fundamentally incompatible with 20%+ sustained ROIC"
            )

        # ── Rule 4: FCF Margin > 20% — 15 pts ────────────────────────────
        # FCF margin (FCF / Revenue) is the output measure that proves both the moat
        # (high gross margin) and the asset-light model (low capex) are working in
        # concert. Every dollar of revenue should generate meaningful investable cash.
        # Kantesaria's archetypes produce 25-40% FCF margins:
        #   MSCI: ~35%+, FICO: ~30%+, S&P Global: ~25%+, Verisk: ~25%+
        # This is distinct from AKO's FCF conversion ratio (FCF/Net Income);
        # FCF margin shows absolute cash generation power relative to business scale.
        # A business below 20% FCF margin lacks the cash engine required for the
        # compounding flywheel to operate at Kantesaria's required pace.
        # Source: VGC — high FCF margins are the prerequisite for durable capital allocation
        fcf_s = data.free_cash_flow_series
        rev_s2 = data.revenue_series
        n_fr = min(len(fcf_s), len(rev_s2))
        fcf_margin_list: list[float] = []
        for i in range(max(0, n_fr - 4), n_fr):
            if rev_s2[i] > 0:
                fcf_margin_list.append(fcf_s[i] / rev_s2[i])
        fcf_margin_avg = statistics.mean(fcf_margin_list) if fcf_margin_list else None
        fcf_ok = fcf_margin_avg is not None and fcf_margin_avg > 0.20

        r4 = self._make_rule(
            name="FCF Margin > 20% (cash generation power)",
            value=fcf_margin_avg * 100 if fcf_margin_avg is not None else None,
            threshold=20.0,
            points_possible=15.0,
            description=(
                f"FCF margin avg = {fcf_margin_avg * 100:.1f}% (last {len(fcf_margin_list)} years) — "
                f"{'strong cash engine: moat and capital-light model working in concert' if fcf_ok else 'FCF margin too thin; insufficient cash to compound at the required pace'}"
                if fcf_margin_avg is not None
                else "FCF margin data unavailable"
            ),
            source=(
                "VGC portfolio — MSCI (~35%), FICO (~30%), S&P Global (~25%) deliver "
                "25-40% FCF margins as the combined output of moat + asset-light model"
            ),
            passed=fcf_ok,
            explanation="FCF margin (Free Cash Flow ÷ Revenue) is the combined output of moat and capital-light model working together. It measures how many cents of investable cash are generated per dollar of revenue. Kantesaria's portfolio companies convert 25-40% of revenue into free cash — the prerequisite for the compounding flywheel.",
        )
        rules.append(r4)
        if not r4.passed and fcf_margin_avg is not None and fcf_margin_avg < 0.05:
            red_flags.append(
                f"FCF margin of {fcf_margin_avg * 100:.1f}% — near-zero cash generation "
                "leaves nothing for compounding; Kantesaria requires 20%+ FCF margins "
                "as evidence that the moat and capital-light model are both functional"
            )

        # ── Rule 5: Revenue CAGR > 8% — 15 pts ───────────────────────────
        # High ROIC alone is insufficient for the compounding thesis. A business
        # earning 25% ROIC but growing revenues at 1% per year quickly exhausts its
        # reinvestment opportunities — it becomes a cash cow, not a compounder.
        # Kantesaria seeks businesses where high ROIC AND meaningful revenue growth
        # combine to create exponential compounding over 10+ year holding periods.
        # At 8% revenue CAGR + 25% ROIC, the reinvestment runway produces dramatically
        # better long-run outcomes than either metric alone.
        # Source: Kantesaria — "the runway for reinvestment is the third leg of the stool;
        # without it you get a value stock, not a compounding machine"
        rev_cagr_data = data.revenue_series
        rev_cagr: float | None = None
        if len(rev_cagr_data) >= 3 and rev_cagr_data[0] > 0 and rev_cagr_data[-1] > 0:
            years = len(rev_cagr_data) - 1
            rev_cagr = (rev_cagr_data[-1] / rev_cagr_data[0]) ** (1 / years) - 1
        cagr_ok = rev_cagr is not None and rev_cagr > 0.08

        r5 = self._make_rule(
            name="Revenue CAGR > 8% (reinvestment runway)",
            value=rev_cagr * 100 if rev_cagr is not None else None,
            threshold=8.0,
            points_possible=15.0,
            description=(
                f"Revenue CAGR = {rev_cagr * 100:.1f}% over {len(rev_cagr_data) - 1} years — "
                f"{'meaningful growth runway: high-ROIC reinvestment compounds exponentially over a decade' if cagr_ok else 'growth too slow to generate the compounding the thesis requires'}"
                if rev_cagr is not None
                else "Insufficient revenue history to compute CAGR (need ≥ 3 years)"
            ),
            source=(
                "Kantesaria — 'the third leg: you need both high ROIC and a long "
                "reinvestment runway; without growth, you have a value stock, not a compounder'"
            ),
            passed=cagr_ok,
            explanation="High ROIC alone is insufficient for compounding. Without revenue growth, a high-ROIC business quickly exhausts its reinvestment opportunities and becomes a dividend-paying cash cow, not a compounder. Above 8% revenue CAGR provides the runway to redeploy capital at high rates for a decade or more.",
        )
        rules.append(r5)
        if not r5.passed and rev_cagr is not None and rev_cagr < 0:
            red_flags.append(
                "Negative revenue growth — a contracting business cannot be a compounding "
                "machine; there is no runway to redeploy capital at high rates if the "
                "addressable market is shrinking"
            )

        # ── Rule 6: Revenue Predictability: Growth stdev < 10% — 10 pts ─
        # Kantesaria specifically targets businesses with subscription-like, recurring,
        # or contractually embedded revenue — MSCI's index licensing fees, FICO's
        # score usage royalties, Verisk's data subscriptions, S&P's ratings.
        # The quantitative signature of this recurring revenue model is LOW VARIANCE
        # in year-on-year growth rates. A business growing 15% one year and -5% the
        # next cannot sustain the long-term thesis even if the average looks fine —
        # cyclicality destroys the predictability required for a confident 10-year hold.
        # Stdev of annual growth rates < 10% indicates contracted, sticky, or deeply
        # embedded revenue that compounds reliably through economic cycles.
        # Source: Kantesaria — "recurring revenue is what makes the compounding reliable;
        # variability is the enemy of a concentrated long-term portfolio"
        rev_g = data.revenue_series
        yoy_rates: list[float] = []
        for i in range(1, len(rev_g)):
            if rev_g[i - 1] > 0:
                yoy_rates.append((rev_g[i] - rev_g[i - 1]) / rev_g[i - 1])
        growth_stdev: float | None = (
            statistics.stdev(yoy_rates) if len(yoy_rates) >= 3 else None
        )
        predictable = growth_stdev is not None and growth_stdev < 0.10

        r6 = self._make_rule(
            name="Revenue Predictability: Annual Growth stdev < 10%",
            value=growth_stdev * 100 if growth_stdev is not None else None,
            threshold=10.0,
            points_possible=10.0,
            description=(
                f"Revenue growth stdev = {growth_stdev * 100:.1f}% ({len(yoy_rates)} periods) — "
                f"{'low variance confirms recurring/contracted revenue: reliable compounding through cycles' if predictable else 'high variability suggests cyclicality or weak pricing power; unreliable compounding'}"
                if growth_stdev is not None
                else "Insufficient revenue history for predictability analysis (need ≥ 4 years)"
            ),
            source=(
                "Kantesaria — 'recurring revenue is what makes compounding reliable; "
                "MSCI and Verisk grow at low-variance rates because revenue is contracted'"
            ),
            passed=predictable,
            explanation="Kantesaria specifically targets subscription-like, recurring, or contractually embedded revenue (index licensing fees, score usage royalties, data subscriptions). Low variance (stdev below 10%) in annual growth rates is the quantitative fingerprint of this model — revenue compounds reliably through all economic conditions.",
        )
        rules.append(r6)
        if not r6.passed and growth_stdev is not None and growth_stdev > 0.20:
            red_flags.append(
                f"Revenue growth stdev of {growth_stdev * 100:.1f}% — highly cyclical "
                "revenue makes the compounding thesis unreliable; Kantesaria's concentrated "
                "portfolio requires high visibility into future cash flows"
            )

        return self._build_result(rules, red_flags)
