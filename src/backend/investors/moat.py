"""
Moat Score module — GuruFocus-inspired economic moat assessment.

Evaluates a company's competitive advantage durability on a 0–10 scale
(internally 0–100, displayed as /10 in the UI) across 9 criteria:

1. Market Leadership & Sustainable Market Share
2. Network Effects & Customer Switching Costs
3. Valuable Intellectual Property
4. Brand Strength & Customer Loyalty
5. Cost Advantages (Operating Leverage)
6. Regulatory Barriers & Exclusive Licenses
7. Superior Distribution Network
8. Strong & Sustainable Pricing Power
9. Consistent Innovation & R&D Payoff

Extensions beyond GuruFocus baseline:
- Sector-calibrated thresholds: gross margin and R&D bars vary by industry
- Moat trend trajectory: Rules 5 and 8 detect strengthening vs. eroding moat
- Claude analytical voice: "competitive strategy analyst" — no buy/sell bias

Weight in consensus aggregator: 0 (analytical lens, not a buy/sell signal).
Display: total_score / 10 = 0.0–10.0 moat score.
Verdict labels: Wide Moat / Narrow Moat / Weak Moat / No Moat.

Sources:
- GuruFocus Moat Score framework (gurufocus.com)
- Morningstar Economic Moat methodology
- Buffett, Berkshire Hathaway shareholder letters (castle-and-moat metaphor)
- Mauboussin, "Measuring the Moat" (Credit Suisse, 2013)
- Dorsey, "The Little Book That Builds Wealth" (2008)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# ── Sector-calibrated thresholds ─────────────────────────────────────────────
# Tuple: (rd_intensity_min, gm_min, op_margin_min)
# rd_intensity_min : minimum R&D / Revenue fraction for IP moat
# gm_min           : minimum gross margin fraction (network effects / switching costs)
# op_margin_min    : minimum operating margin fraction (cost advantage baseline)
SECTOR_THRESHOLDS: dict[str, tuple[float, float, float]] = {
    "Technology":              (0.10, 0.55, 0.18),
    "Healthcare":              (0.08, 0.50, 0.15),
    "Financial Services":      (0.02, 0.45, 0.25),
    "Consumer Defensive":      (0.02, 0.35, 0.12),
    "Consumer Cyclical":       (0.02, 0.30, 0.08),
    "Communication Services":  (0.05, 0.50, 0.20),
    "Industrials":             (0.02, 0.30, 0.12),
    "Energy":                  (0.01, 0.25, 0.10),
    "Utilities":               (0.01, 0.30, 0.20),
    "Real Estate":             (0.00, 0.35, 0.20),
    "Basic Materials":         (0.01, 0.25, 0.08),
    "_default":                (0.03, 0.35, 0.12),
}

# Sectors with structural regulatory protection (barrier to entry)
REGULATED_SECTORS: frozenset[str] = frozenset({
    "Utilities",
    "Financial Services",
    "Healthcare",
    "Communication Services",
})


class MoatInvestor(BaseInvestor):
    """
    Economic moat analyst.

    Returns InvestorScore with total_score 0-100 (display as /10 in UI).
    verdict = "Wide Moat" | "Narrow Moat" | "Weak Moat" | "No Moat".
    Weight in consensus = 0 (analytical, excluded from buy/sell consensus).
    """

    @property
    def name(self) -> str:
        return "Moat Score"

    def _verdict(self, score: float) -> str:
        """Override: moat-specific labels at the same 75/55/40 breakpoints."""
        if score >= 75:
            return "Wide Moat"
        if score >= 55:
            return "Narrow Moat"
        if score >= 40:
            return "Weak Moat"
        return "No Moat"

    def score(self, data: "FinancialData") -> InvestorScore:  # noqa: C901  (complex but by design)
        sector = data.sector or "_default"
        rd_min, gm_min, op_min = SECTOR_THRESHOLDS.get(sector, SECTOR_THRESHOLDS["_default"])
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Pre-compute shared series ─────────────────────────────────────────
        rev = data.revenue_series           # oldest → newest
        gm = data.gross_margin_series       # oldest → newest
        op_margins = self._op_margin_series(data)

        # Revenue CAGR (shared by Rules 1 and 9)
        rev_cagr: Optional[float] = None
        if len(rev) >= 3 and rev[0] > 0 and rev[-1] > 0:
            rev_cagr = (rev[-1] / rev[0]) ** (1.0 / (len(rev) - 1)) - 1

        # ── Rule 1: Market Leadership (11 pts) ───────────────────────────────
        # Sustained revenue CAGR ≥ 8% AND low growth variance = durable leadership
        # vs. one-time beneficiaries or cyclicals.
        # Source: Dorsey, "The Little Book That Builds Wealth" (2008) Ch. 1
        yoy_rates: list[float] = [
            (rev[i] - rev[i - 1]) / rev[i - 1]
            for i in range(1, len(rev))
            if rev[i - 1] > 0
        ]
        growth_stdev: Optional[float] = (
            statistics.stdev(yoy_rates) if len(yoy_rates) >= 2 else None
        )
        cagr_ok = rev_cagr is not None and rev_cagr >= 0.08
        stdev_ok = growth_stdev is None or growth_stdev <= 0.10
        r1_passed = cagr_ok and stdev_ok

        if rev_cagr is not None:
            stdev_part = (
                f", growth stdev={growth_stdev * 100:.1f}pp"
                if growth_stdev is not None
                else ""
            )
            r1_desc = (
                f"Revenue CAGR={rev_cagr * 100:.1f}%{stdev_part} over {len(rev) - 1} yr — "
                + (
                    "consistent market-share gains; CAGR and variance confirm durable leadership"
                    if r1_passed
                    else "below 8% CAGR or growth too volatile; market leadership not yet proven"
                )
            )
        else:
            r1_desc = "Insufficient revenue history (need >= 3 years)"

        r1 = self._make_rule(
            name="Market Leadership: Revenue CAGR >= 8% with stable growth",
            value=rev_cagr * 100 if rev_cagr is not None else None,
            threshold=8.0,
            points_possible=11.0,
            description=r1_desc,
            source=(
                "GuruFocus Moat Score — Criterion 1: Market Leadership & Sustainable Market Share; "
                "Dorsey, 'The Little Book That Builds Wealth' (2008)"
            ),
            passed=r1_passed,
            explanation="Revenue CAGR above 8% with low growth variance distinguishes durable market leaders from cyclical beneficiaries. Consistent market-share gainers show above-average revenue growth with low volatility — as opposed to businesses that spike during booms and shrink in downturns.",
        )
        rules.append(r1)
        if rev_cagr is not None and rev_cagr < 0:
            red_flags.append(
                f"Revenue declining at {rev_cagr * 100:.1f}% CAGR — "
                "a shrinking business cannot maintain market leadership"
            )
        if growth_stdev is not None and growth_stdev > 0.20:
            red_flags.append(
                f"Revenue growth stdev {growth_stdev * 100:.1f}pp — "
                "high cyclicality; the market position is not durable across cycles"
            )

        # ── Rule 2: Network Effects & Switching Costs (11 pts) ───────────────
        # High, stable gross margins are the financial fingerprint of network effects
        # and switching costs. Customers locked into an ecosystem cannot easily defect,
        # allowing the business to sustain premium pricing over the cost of service.
        # Threshold is sector-calibrated (Technology 55%, Grocery 35%, etc.).
        # Source: Mauboussin, "Measuring the Moat" (Credit Suisse, 2013)
        gm_avg: Optional[float] = statistics.mean(gm) if gm else None
        gm_stdev: Optional[float] = statistics.stdev(gm) if len(gm) >= 2 else None
        gm_level_ok = gm_avg is not None and gm_avg >= gm_min
        gm_stable_ok = gm_stdev is None or gm_stdev <= 0.05
        r2_passed = gm_level_ok and gm_stable_ok

        if gm_avg is not None:
            stdev_part2 = (
                f", stdev={gm_stdev * 100:.1f}pp" if gm_stdev is not None else ""
            )
            r2_desc = (
                f"Gross margin={gm_avg * 100:.1f}%{stdev_part2} "
                f"(sector threshold={gm_min * 100:.0f}%) — "
                + (
                    "high stable margins confirm switching costs or network lock-in; customers cannot easily defect"
                    if r2_passed
                    else "margin level or stability below sector threshold; limited switching cost evidence"
                )
            )
        else:
            r2_desc = "Gross margin data unavailable"

        r2 = self._make_rule(
            name=f"Network Effects: Gross margin >= {gm_min * 100:.0f}% and stable (stdev <= 5pp)",
            value=gm_avg * 100 if gm_avg is not None else None,
            threshold=gm_min * 100,
            points_possible=11.0,
            description=r2_desc,
            source=(
                "GuruFocus Moat Score — Criterion 2: Network Effects & Significant Customer Switching Costs; "
                "Mauboussin, 'Measuring the Moat' (Credit Suisse, 2013)"
            ),
            passed=r2_passed,
            explanation="High, stable gross margins are the financial fingerprint of network effects and switching costs. When customers are locked into a product ecosystem, they cannot easily defect, allowing premium pricing. The threshold is sector-calibrated to account for different industry cost structures.",
        )
        rules.append(r2)
        if gm_avg is not None and gm_avg < 0.20:
            red_flags.append(
                f"Gross margin {gm_avg * 100:.1f}% — commodity-like business; "
                "customers can switch to cheaper alternatives with minimal friction"
            )
        if gm_stdev is not None and gm_stdev > 0.08:
            red_flags.append(
                f"Gross margin stdev {gm_stdev * 100:.1f}pp — "
                "volatile margins indicate competitive erosion of the pricing advantage"
            )

        # ── Rule 3: Intellectual Property (11 pts) ───────────────────────────
        # R&D investment creates patents, trade secrets, and proprietary processes.
        # R&D >= sector threshold + ROIC >= 12% proves IP generates real returns.
        # Fallback: if R&D not reported, ROIC >= 15% is used as a proxy.
        # Source: GuruFocus Criterion 3; Mauboussin, "Measuring the Moat"
        rd_series = self._rd_intensity_series(data)
        rd_avg: Optional[float] = statistics.mean(rd_series) if rd_series else None
        roic_s = data.roic_series
        roic_avg: Optional[float] = (
            statistics.mean(roic_s[-min(len(roic_s), 5):]) if roic_s else None
        )

        if rd_avg is not None:
            rd_ok = rd_avg >= rd_min
            roic_ok = roic_avg is not None and roic_avg >= 0.12
            r3_passed = rd_ok and roic_ok
            roic_str = f", ROIC={roic_avg * 100:.1f}%" if roic_avg is not None else ""
            r3_value: Optional[float] = rd_avg * 100
            r3_threshold = rd_min * 100
            r3_name = f"Intellectual Property: R&D >= {rd_min * 100:.0f}% of revenue + ROIC >= 12%"
            r3_desc = (
                f"R&D/Revenue={rd_avg * 100:.1f}%{roic_str} "
                f"(sector min={rd_min * 100:.0f}%) — "
                + (
                    "active innovation pipeline generating real economic returns; IP moat productive"
                    if r3_passed
                    else "R&D or ROIC below threshold; innovation moat not generating sufficient returns"
                )
            )
            r3_source = "GuruFocus Moat Score — Criterion 3: Valuable Intellectual Property & Patents"
        elif roic_avg is not None:
            r3_passed = roic_avg >= 0.15
            r3_value = roic_avg * 100
            r3_threshold = 15.0
            r3_name = "Intellectual Property: ROIC >= 15% proxy (R&D data unavailable)"
            r3_desc = (
                f"ROIC={roic_avg * 100:.1f}% (R&D line not reported by yfinance) — "
                + (
                    "sustained high ROIC suggests proprietary process or product advantage"
                    if r3_passed
                    else "ROIC below 15% proxy threshold; no clear IP moat evidence"
                )
            )
            r3_source = (
                "GuruFocus Moat Score — Criterion 3 (ROIC proxy: R&D data not available from yfinance)"
            )
        else:
            r3_passed = False
            r3_value = None
            r3_threshold = rd_min * 100
            r3_name = "Intellectual Property: R&D intensity (sector-calibrated)"
            r3_desc = "R&D and ROIC data unavailable"
            r3_source = "GuruFocus Moat Score — Criterion 3: Valuable Intellectual Property & Patents"

        r3 = self._make_rule(
            name=r3_name,
            value=r3_value,
            threshold=r3_threshold,
            points_possible=11.0,
            description=r3_desc,
            source=r3_source,
            passed=r3_passed,
            explanation="R&D investment at or above the sector-minimum threshold, combined with ROIC above 12%, proves IP spending generates real economic returns. If R&D data is unavailable, ROIC above 15% serves as a proxy — sustained high returns imply proprietary advantages that competitors cannot easily replicate.",
        )
        rules.append(r3)

        # ── Rule 4: Brand Strength & Customer Loyalty (11 pts) ───────────────
        # Strong brands sustain ROE above the cost of equity over time because
        # customers consistently pay a premium. ROE >= 15% over 3yr confirms this.
        # Falls back to ROIC when equity is negative (buyback-heavy companies).
        # Source: Dorsey, "The Little Book That Builds Wealth" Ch. 4; GuruFocus Criterion 4
        roe_s = data.roe_series
        r4_series = roe_s
        r4_label = "ROE"
        if not roe_s:
            roic_fb = data.roic_series
            if roic_fb:
                r4_series = roic_fb
                r4_label = "ROIC"
        r4_avg: Optional[float] = (
            statistics.mean(r4_series[-min(len(r4_series), 3):]) if r4_series else None
        )
        if r4_avg is not None:
            suffix = " (ROIC fallback — negative equity)" if r4_label == "ROIC" else ""
            r4_desc = (
                f"{r4_label} (3yr avg)={r4_avg * 100:.1f}%{suffix} — "
                + (
                    "sustained above cost of equity; brand loyalty drives recurring premium pricing"
                    if r4_avg >= 0.15
                    else f"{r4_label} below 15%; brand premium insufficient to drive above-average equity returns"
                )
            )
        else:
            r4_desc = "ROE data unavailable"

        r4 = self._make_rule(
            name="Brand Strength: ROE >= 15% (3yr avg)",
            value=r4_avg * 100 if r4_avg is not None else None,
            threshold=15.0,
            points_possible=11.0,
            description=r4_desc,
            source=(
                "GuruFocus Moat Score — Criterion 4: Strong Brand Strength & Deep Customer Loyalty; "
                "Dorsey, 'The Little Book That Builds Wealth' (2008)"
            ),
            explanation="A strong brand enables consistently above-average Return on Equity by commanding premium pricing. ROE above 15% over a 3-year average confirms that brand loyalty translates into sustained financial returns that exceed the cost of equity capital. Falls back to ROIC for companies with negative equity.",
        )
        rules.append(r4)
        if r4_avg is not None and r4_avg < 0:
            red_flags.append(
                f"Negative {r4_label} — business is destroying shareholder equity; no brand loyalty premium"
            )

        # ── Rule 5: Cost Advantages & Operating Leverage (11 pts) ───────────
        # Operating margin expansion = revenue scaling faster than costs.
        # Combined with low CapEx (<=10% of revenue), this confirms durable cost advantage.
        # MOAT TREND: detects whether cost advantages are strengthening or weakening.
        # Source: Mauboussin, "Measuring the Moat"; GuruFocus Criterion 5
        op_expansion: Optional[float] = None
        op_trend_str = ""
        if len(op_margins) >= 4:
            n_half = max(2, len(op_margins) // 2)
            early_avg = statistics.mean(op_margins[:n_half])
            late_avg = statistics.mean(op_margins[n_half:])
            op_expansion = late_avg - early_avg
            if op_expansion > 0.01:
                op_trend_str = f"strengthening (+{op_expansion * 100:.1f}pp)"
            elif op_expansion < -0.01:
                op_trend_str = f"weakening ({op_expansion * 100:.1f}pp)"
            else:
                op_trend_str = "stable"

        capex_s = data.capex_series
        n_cr = min(len(capex_s), len(rev))
        capex_ratios = [
            capex_s[i] / rev[i]
            for i in range(max(0, n_cr - 4), n_cr)
            if rev[i] > 0
        ]
        capex_intensity: Optional[float] = (
            statistics.mean(capex_ratios) if capex_ratios else None
        )

        if op_expansion is not None:
            op_ok = op_expansion >= 0.0
        elif op_margins:
            op_ok = op_margins[-1] >= op_min
        else:
            op_ok = False
        capex_ok = capex_intensity is None or capex_intensity <= 0.10
        r5_passed = op_ok and capex_ok

        op_val = op_margins[-1] * 100 if op_margins else None
        capex_str = (
            f", CapEx/Rev={capex_intensity * 100:.1f}%" if capex_intensity is not None else ""
        )
        trend_str = f", trend: {op_trend_str}" if op_trend_str else ""
        if op_val is not None:
            r5_desc = (
                f"Op margin={op_val:.1f}%{trend_str}{capex_str} — "
                + (
                    "operating leverage evident; costs scaling slower than revenue"
                    if r5_passed
                    else "cost advantages not evident: margins flat/contracting or high capital intensity"
                )
            )
        else:
            r5_desc = "Operating margin data unavailable"

        r5 = self._make_rule(
            name="Cost Advantages: Operating margin expanding + CapEx <= 10% of revenue",
            value=op_val,
            threshold=op_min * 100,
            points_possible=11.0,
            description=r5_desc,
            source=(
                "GuruFocus Moat Score — Criterion 5: Durable Cost Advantages "
                "(economies of scale, proprietary technology)"
            ),
            passed=r5_passed,
            explanation="Operating margin expansion (revenue growing faster than costs) combined with low CapEx intensity (below 10% of revenue) confirms durable cost advantages and operating leverage. The trend direction reveals whether cost advantages are compounding (strengthening) or being eroded by competition (weakening).",
        )
        rules.append(r5)
        if op_expansion is not None and op_expansion < -0.03:
            red_flags.append(
                f"Operating margin contracting {abs(op_expansion) * 100:.1f}pp — "
                "cost advantages are eroding; competitive moat is weakening"
            )
        if capex_intensity is not None and capex_intensity > 0.20:
            red_flags.append(
                f"CapEx/Revenue {capex_intensity * 100:.1f}% — "
                "heavy capital intensity limits the compounding of cost advantages"
            )

        # ── Rule 6: Regulatory Barriers (11 pts) ─────────────────────────────
        # Two routes to passing:
        # (a) Sector-level: regulated industry = structural protection from new entrants.
        # (b) Metric-level: low operating margin stdev (<=5pp) = contractual or stable pricing.
        # Source: GuruFocus Moat Score Criterion 6
        op_margin_stdev: Optional[float] = (
            statistics.stdev(op_margins) if len(op_margins) >= 3 else None
        )
        is_regulated = sector in REGULATED_SECTORS
        stdev_ok_r6 = op_margin_stdev is not None and op_margin_stdev <= 0.05
        r6_passed = is_regulated or stdev_ok_r6

        if op_margin_stdev is not None:
            r6_val: Optional[float] = op_margin_stdev * 100
        elif is_regulated:
            r6_val = 0.0  # regulated sector = structural protection, no stdev concern
        else:
            r6_val = None

        if is_regulated:
            reg_extra = (
                f"; op margin stdev={op_margin_stdev * 100:.1f}pp"
                if op_margin_stdev is not None
                else ""
            )
            r6_desc = (
                f"Sector '{sector}' operates under regulatory oversight — licensing, "
                "compliance barriers, and rate regulation create structural protection "
                "against new entrants" + reg_extra
            )
        elif op_margin_stdev is not None:
            r6_desc = (
                f"Unregulated sector; op margin stdev={op_margin_stdev * 100:.1f}pp — "
                + (
                    "stable margins suggest contractual pricing protection"
                    if stdev_ok_r6
                    else "volatile margins with no regulatory protection; low barriers to entry"
                )
            )
        else:
            r6_desc = "Operating margin data insufficient for regulatory barrier assessment"

        r6 = self._make_rule(
            name="Regulatory Barriers: Regulated sector OR op margin stdev <= 5pp",
            value=r6_val,
            threshold=5.0,
            points_possible=11.0,
            description=r6_desc,
            source="GuruFocus Moat Score — Criterion 6: Significant Regulatory Barriers & Exclusive Licenses",
            passed=r6_passed,
            explanation="Structural entry barriers from regulation (licensing, compliance requirements, rate regulation) provide built-in protection from new competitors. For unregulated sectors, very stable operating margins (stdev ≤ 5pp) imply contractual or sticky pricing that functions as a softer barrier.",
        )
        rules.append(r6)

        # ── Rule 7: Distribution Network (11 pts) ─────────────────────────────
        # Asset turnover measures infrastructure efficiency (revenue per asset dollar).
        # High turnover + FCF margin >= 10% = distribution network generating durable value.
        # Source: GuruFocus Moat Score Criterion 7
        asset_turnover: Optional[float] = None
        ta = data.total_assets
        if ta and ta > 0 and rev and rev[-1] > 0:
            asset_turnover = rev[-1] / ta

        fcf_marg = data.fcf_margin_series
        fcf_avg: Optional[float] = (
            statistics.mean(fcf_marg[-min(len(fcf_marg), 4):]) if fcf_marg else None
        )
        turnover_ok = asset_turnover is not None and asset_turnover >= 0.7
        fcf_dist_ok = fcf_avg is not None and fcf_avg >= 0.10
        r7_passed = turnover_ok and fcf_dist_ok

        fcf_str_r7 = f", FCF margin={fcf_avg * 100:.1f}%" if fcf_avg is not None else ""
        if asset_turnover is not None:
            r7_desc = (
                f"Asset turnover={asset_turnover:.2f}x{fcf_str_r7} — "
                + (
                    "efficient distribution network: strong revenue per asset dollar with healthy cash conversion"
                    if r7_passed
                    else "distribution efficiency or cash conversion below threshold"
                )
            )
        else:
            r7_desc = "Asset turnover data unavailable"

        r7 = self._make_rule(
            name="Distribution Network: Asset turnover >= 0.7x AND FCF margin >= 10%",
            value=asset_turnover,
            threshold=0.7,
            points_possible=11.0,
            description=r7_desc,
            source="GuruFocus Moat Score — Criterion 7: Superior Distribution Network",
            passed=r7_passed,
            explanation="Asset turnover (Revenue ÷ Total Assets) measures how efficiently the distribution infrastructure generates revenue. Above 0.7x combined with FCF margin above 10% confirms the distribution system generates genuine economic value rather than just physical capacity that sits underutilised.",
        )
        rules.append(r7)

        # ── Rule 8: Pricing Power / Moat Trend (12 pts) ───────────────────────
        # Gross margin expansion is the single most reliable pricing power indicator.
        # A business with a real moat can raise prices faster than costs rise.
        # MOAT TREND: detects whether pricing power is strengthening or eroding.
        # Pass: gross margin stable (delta >= -2pp) or expanding.
        # Source: Buffett — "pricing power is the most important factor in evaluating a business"
        gm_delta: Optional[float] = None
        gm_trend_str = ""
        if len(gm) >= 4:
            n_half_gm = max(2, len(gm) // 2)
            gm_early = statistics.mean(gm[:n_half_gm])
            gm_late = statistics.mean(gm[n_half_gm:])
            gm_delta = gm_late - gm_early
            if gm_delta > 0.01:
                gm_trend_str = f"strengthening (+{gm_delta * 100:.1f}pp)"
            elif gm_delta < -0.01:
                gm_trend_str = f"contracting ({gm_delta * 100:.1f}pp)"
            else:
                gm_trend_str = "stable"
        elif len(gm) >= 2:
            gm_delta = gm[-1] - gm[0]
            if abs(gm_delta) < 0.01:
                gm_trend_str = "stable"
            elif gm_delta > 0:
                gm_trend_str = f"expanding (+{gm_delta * 100:.1f}pp)"
            else:
                gm_trend_str = f"contracting ({gm_delta * 100:.1f}pp)"

        gm_latest = gm[-1] if gm else None
        if gm_delta is not None:
            r8_passed = gm_delta >= -0.02   # allow up to 2pp contraction
        elif gm_latest is not None:
            r8_passed = gm_latest >= gm_min
        else:
            r8_passed = False

        trend_str_r8 = f", trend: {gm_trend_str}" if gm_trend_str else ""
        if gm_latest is not None:
            r8_desc = (
                f"Gross margin={gm_latest * 100:.1f}%{trend_str_r8} — "
                + (
                    "pricing power intact: margins stable or expanding"
                    if r8_passed
                    else "pricing power eroding: gross margin contracting beyond acceptable threshold"
                )
            )
        else:
            r8_desc = "Gross margin data unavailable"

        r8 = self._make_rule(
            name="Pricing Power: Gross margin stable or expanding (trend analysis)",
            value=gm_latest * 100 if gm_latest is not None else None,
            threshold=gm_min * 100,
            points_possible=12.0,
            description=r8_desc,
            source=(
                "GuruFocus Moat Score — Criterion 8: Strong & Sustainable Pricing Power; "
                "Buffett, Berkshire letters: 'pricing power is the single most important factor'"
            ),
            passed=r8_passed,
            explanation="The gross margin trend — comparing the first half to the second half of available history — directly measures whether the company can raise prices faster than costs rise. Stable or expanding margins confirm pricing power is intact; contracting margins signal the moat is being eroded by competition.",
        )
        rules.append(r8)
        if gm_delta is not None and gm_delta < -0.03:
            red_flags.append(
                f"Gross margin contracted {abs(gm_delta) * 100:.1f}pp — "
                "pricing power eroding; economic moat is weakening"
            )

        # ── Rule 9: Innovation & R&D Payoff (11 pts) ──────────────────────────
        # Effective innovation shows as EPS growing faster than revenue:
        # R&D is improving profitability, not just adding cost.
        # Source: GuruFocus Moat Score Criterion 9
        eps_cagr = data.eps_growth_rate_annual
        r9_passed = False
        r9_value: Optional[float] = None
        r9_threshold = 0.0
        r9_desc = "EPS or revenue history unavailable for innovation payoff analysis"

        if eps_cagr is not None and rev_cagr is not None:
            delta_pp = (eps_cagr - rev_cagr) * 100
            r9_value = delta_pp
            r9_threshold = 0.0
            r9_passed = eps_cagr >= rev_cagr
            r9_desc = (
                f"EPS CAGR={eps_cagr * 100:.1f}%, Rev CAGR={rev_cagr * 100:.1f}% "
                f"(delta={delta_pp:+.1f}pp) — "
                + (
                    "innovation translating to higher profitability: R&D investment paying off"
                    if r9_passed
                    else "revenue growing faster than EPS; innovation not yet improving unit economics"
                )
            )
        elif eps_cagr is not None:
            r9_value = eps_cagr * 100
            r9_threshold = 8.0
            r9_passed = eps_cagr >= 0.08
            r9_desc = (
                f"EPS CAGR={eps_cagr * 100:.1f}% (revenue CAGR unavailable) — "
                + (
                    "meaningful EPS growth indicates productive innovation"
                    if r9_passed
                    else "EPS growth below 8% standalone threshold"
                )
            )

        r9 = self._make_rule(
            name="Innovation Payoff: EPS CAGR >= Revenue CAGR",
            value=r9_value,
            threshold=r9_threshold,
            points_possible=11.0,
            description=r9_desc,
            source=(
                "GuruFocus Moat Score — Criterion 9: Consistent & Impactful Innovation & R&D"
            ),
            passed=r9_passed,
            explanation="When EPS grows faster than revenue (EPS CAGR > Revenue CAGR), R&D investment is improving profitability — each dollar of revenue is becoming more profitable. This confirms innovation is creating genuine economic value, not just adding cost while growing the top line.",
        )
        rules.append(r9)

        return self._build_result(rules, red_flags)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _rd_intensity_series(self, data: "FinancialData") -> list[float]:
        """
        Extract R&D expense as fraction of revenue (oldest→newest).
        Searches income_stmt index for rows containing 'research' or 'development'.
        Returns empty list if R&D data is not reported by yfinance.
        """
        try:
            rd_rows = [
                r for r in data.income_stmt.index
                if any(
                    k in str(r).lower()
                    for k in ("research", "development", "r&d")
                )
            ]
            if not rd_rows:
                return []
            rd_series = data._series(data.income_stmt, rd_rows[0])
            rev_series = data.revenue_series
            n = min(len(rd_series), len(rev_series))
            return [
                abs(rd_series[i]) / rev_series[i]
                for i in range(n)
                if rev_series[i] > 0
            ]
        except Exception as e:
            logger.debug(f"R&D intensity extraction failed: {e}")
            return []

    def _op_margin_series(self, data: "FinancialData") -> list[float]:
        """Compute operating margin series (oldest→newest)."""
        try:
            op = data.operating_income_series
            rev = data.revenue_series
            n = min(len(op), len(rev))
            return [op[i] / rev[i] for i in range(n) if rev[i] > 0]
        except Exception:
            return []
