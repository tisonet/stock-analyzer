"""
Charlie Munger scoring module.

Rules based on:
- "Poor Charlie's Almanack" by Peter Kaufman (2005)
- "Seeking Wisdom" by Peter Bevelin
- Berkshire Hathaway Annual Meetings and Letters
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class MungerInvestor(BaseInvestor):
    """
    Charlie Munger scoring: qualitative moat, simplicity, skin-in-the-game.
    'Invert, always invert' — fails if multiple risk factors present simultaneously.
    """

    @property
    def name(self) -> str:
        return "Munger"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: Management skin in the game — 10 pts ───────────────────
        # "Show me the incentive and I'll show you the outcome." — Munger
        # Threshold scales with market cap: 5% for small-caps is meaningful;
        # 0.1% for mega-caps still represents hundreds of millions at stake.
        insider_own = data.insider_ownership_pct
        mkt_cap = data.info.get("marketCap")
        if mkt_cap is not None and mkt_cap > 100e9:
            insider_threshold = 0.001   # > $100B: 0.1%
        elif mkt_cap is not None and mkt_cap > 20e9:
            insider_threshold = 0.005   # $20B–$100B: 0.5%
        elif mkt_cap is not None and mkt_cap > 2e9:
            insider_threshold = 0.02    # $2B–$20B: 2%
        else:
            insider_threshold = 0.05    # < $2B: 5%
        insider_passed = insider_own >= insider_threshold if insider_own is not None else None
        insider_pts = 10.0 if insider_passed else 0.0
        insider_desc = (
            f"Insiders own {insider_own*100:.2f}% (threshold {insider_threshold*100:.1f}% for this market cap)"
            if insider_own is not None
            else "Insider ownership data unavailable"
        )
        rules.append(Rule(
            name="Insider ownership (market-cap scaled)",
            passed=insider_passed or False,
            value=insider_own * 100 if insider_own is not None else None,
            threshold=insider_threshold * 100,
            points_awarded=insider_pts,
            points_possible=10.0,
            description=insider_desc,
            source="Poor Charlie's Almanack — incentive alignment",
            explanation="Munger: 'Show me the incentive and I'll show you the outcome.' Insider ownership threshold scales with market cap — 5% is meaningful for a $500M company but impossible for a $200B one. The question is whether management has real money at risk: 0.1% of a $200B company is still $200M.",
        ))
        if insider_own is not None and insider_own < insider_threshold / 5:
            red_flags.append(f"Insiders own {insider_own*100:.2f}% — well below {insider_threshold*100:.1f}% threshold, management poorly aligned")

        # ── Rule 3: Qualitative moat — ROE consistency proxy — 15 pts ──────
        # "The best business to own is one that over an extended period can
        #  employ large amounts of capital at very high rates." — Munger
        # Falls back to ROIC when equity is negative (buyback-heavy companies).
        roe_series = data.roe_series
        return_series = roe_series
        return_label = "ROE"
        if not roe_series:
            roic_s = data.roic_series
            if roic_s:
                return_series = roic_s
                return_label = "ROIC"
        roe_score, roe_desc = self._moat_from_roe(return_series, return_label)
        r3_pts = 15.0 * roe_score if roe_score is not None else 0.0
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Durable economic moat (ROE consistency)",
            passed=roe_score is not None and roe_score >= 0.6,
            value=statistics.mean(return_series) * 100 if return_series else None,
            threshold=15.0,   # 15% avg ROE as moat threshold
            points_awarded=r3_pts,
            points_possible=15.0,
            description=roe_desc,
            source="Seeking Wisdom, Bevelin — Munger on competitive advantages",
            explanation="Return on Equity (ROE) measures how much profit the company earns on shareholders' money. Consistently high ROE across many years implies a durable competitive advantage that competitors cannot erode — Munger's primary quality test. Falls back to ROIC for companies with negative equity (buyback-heavy firms like FICO, MCD, SBUX).",
        ))
        if return_series and statistics.mean(return_series) < 0.08:
            red_flags.append(f"Average {return_label} below 8% — weak or non-existent economic moat")

        # ── Rule 4: Penalise excessive complexity — 15 pts ─────────────────
        # "Munger's inversion: list what would make this business fail.
        #  Complexity + many segments = fragility." — Poor Charlie's Almanack
        complexity_penalty, complexity_desc, inversions = self._complexity_check(data)
        red_flags.extend(inversions)
        simplicity_pts = 15.0 * (1.0 - complexity_penalty)
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Low business complexity (Munger inversion)",
            passed=complexity_penalty < 0.4,
            value=complexity_penalty * 100,   # % complexity score
            threshold=40.0,
            points_awarded=simplicity_pts,
            points_possible=15.0,
            description=complexity_desc,
            source="Poor Charlie's Almanack — Invert, always invert",
            explanation="Munger's 'inversion' principle: instead of asking what could go well, ask what could go wrong. This rule checks four structural failure conditions: (1) weak interest coverage (<5×) — debt burden crushes earnings in downturns; (2) persistent cash burn; (3) eroding gross margins averaged over 3-year windows; (4) capital intensity trap where CapEx+R&D exceeds 15% of revenue, preventing free compounding. Fewer triggered factors means the business is more resilient.",
        ))

        # ── Rule 5: ROIC/ROE consistency — 10 pts ──────────────────────────
        # Prefer ROIC — not distorted by buybacks compressing equity.
        # Fall back to ROE when ROIC is unavailable.
        roic_for_consistency = data.roic_series
        if roic_for_consistency:
            consistency_series = roic_for_consistency
            consistency_label = "ROIC"
        else:
            consistency_series = return_series
            consistency_label = return_label
        roe_consistency_pts = 0.0
        roe_consistency_desc = f"Insufficient {consistency_label} history"
        roe_consistency_pass = None
        if len(consistency_series) >= 4:
            stdev = statistics.stdev(consistency_series) * 100
            avg_ret = statistics.mean(consistency_series) * 100
            roe_consistency_pass = stdev < 10.0 and avg_ret > 12.0
            roe_consistency_pts = 10.0 if roe_consistency_pass else 0.0
            roe_consistency_desc = f"{consistency_label} avg={avg_ret:.1f}%, stdev={stdev:.1f}%"
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="ROIC consistent > 12% (stdev < 10%)",
            passed=roe_consistency_pass or False,
            value=statistics.mean(consistency_series) * 100 if consistency_series else None,
            threshold=12.0,
            points_awarded=roe_consistency_pts,
            points_possible=10.0,
            description=roe_consistency_desc,
            source="Berkshire Hathaway Annual Letters — Munger on business quality",
            explanation="ROIC measures returns on all invested capital and is unaffected by buybacks compressing equity. Consistent ROIC above 12% with low variance (stdev < 10%) indicates stable competitive protection — not just a lucky year. Falls back to ROE when ROIC data is unavailable.",
        ))

        # ── Rule 6: OCF / Net Income ≥ 1.0 (earnings quality) — 15 pts ─────
        # "Owner earnings" — Munger insists profits must be real cash.
        ocf_s = data.operating_cash_flow_series
        ni_s = data.net_income_series
        n6 = min(len(ocf_s), len(ni_s), 5)
        ocf_ni_pass: bool | None = None
        ocf_ni_pts = 0.0
        ocf_ni_val: float | None = None
        ocf_ni_desc = "Insufficient OCF / NI data"
        if n6 >= 2:
            pairs = [(o, ni) for o, ni in zip(ocf_s[-n6:], ni_s[-n6:]) if ni > 0]
            if pairs:
                avg_ratio = statistics.mean(o / ni for o, ni in pairs)
                ocf_ni_val = avg_ratio
                ocf_ni_pass = avg_ratio >= 1.0
                ocf_ni_pts = 15.0 if ocf_ni_pass else 0.0
                ocf_ni_desc = f"avg OCF/NI = {avg_ratio:.2f} over {len(pairs)} years"
        rules.append(Rule(
            name="OCF / Net Income ≥ 1.0 (earnings quality)",
            passed=ocf_ni_pass or False,
            value=ocf_ni_val,
            threshold=1.0,
            points_awarded=ocf_ni_pts,
            points_possible=15.0,
            description=ocf_ni_desc,
            source="Poor Charlie's Almanack — Munger on owner earnings",
            explanation="Munger insists net income must translate to real cash. When operating cash flow consistently meets or exceeds net income, earnings are not dependent on aggressive accounting — depreciation is real, working capital is not ballooning, and profits are genuinely collectible.",
        ))

        # ── Rule 7: Gross margin ≥ 40% sustained — 10 pts ───────────────────
        # Munger: pricing power shows in gross margins first.
        gm = data.gross_margin_series
        gm_w = min(len(gm), 5)
        gm_pass: bool | None = None
        gm_pts = 0.0
        gm_val: float | None = None
        gm_desc = "Insufficient gross margin data"
        if gm_w >= 3:
            gm_recent = gm[-gm_w:]
            avg_gm = statistics.mean(gm_recent)
            above_pct = sum(1 for m in gm_recent if m >= 0.40) / len(gm_recent)
            gm_val = avg_gm * 100
            gm_pass = avg_gm >= 0.40
            gm_pts = 10.0 if gm_pass else 0.0
            gm_desc = f"avg gross margin {avg_gm*100:.1f}% ({above_pct*100:.0f}% of years ≥ 40%)"
        rules.append(Rule(
            name="Gross margin ≥ 40% sustained",
            passed=gm_pass or False,
            value=gm_val,
            threshold=40.0,
            points_awarded=gm_pts,
            points_possible=10.0,
            description=gm_desc,
            source="Seeking Wisdom, Bevelin — Munger on pricing power",
            explanation="Munger believes pricing power is the single most important attribute of a great business. Gross margins above 40% sustained over many years indicate customers cannot easily substitute the product, giving the company the ability to raise prices ahead of costs.",
        ))

        # ── Rule 8: Capital-light (CapEx / Revenue < 5%) — 5 pts ────────────
        # Munger's "toll bridge" ideal: earns freely without constant reinvestment.
        capex_s = data.capex_series
        rev_s = data.revenue_series
        n8 = min(len(capex_s), len(rev_s), 5)
        cap_pass: bool | None = None
        cap_pts = 0.0
        cap_val: float | None = None
        cap_desc = "Insufficient CapEx / Revenue data"
        if n8 >= 2:
            ratios8 = [c / r for c, r in zip(capex_s[-n8:], rev_s[-n8:]) if r > 0]
            if ratios8:
                avg_intensity = statistics.mean(ratios8)
                cap_val = avg_intensity * 100
                cap_pass = avg_intensity < 0.05
                cap_pts = 5.0 if cap_pass else 0.0
                cap_desc = f"avg CapEx/Revenue = {avg_intensity*100:.1f}%"
        rules.append(Rule(
            name="Capital-light (CapEx / Revenue < 5%)",
            passed=cap_pass or False,
            value=cap_val,
            threshold=5.0,
            points_awarded=cap_pts,
            points_possible=5.0,
            description=cap_desc,
            source="Poor Charlie's Almanack — Munger's toll bridge ideal",
            explanation="Munger's ideal business earns like a toll bridge — collecting cash without constantly reinvesting in machinery or equipment. CapEx below 5% of revenue means profits flow freely to shareholders rather than being consumed by maintenance or expansion of physical assets.",
        ))

        # ── Rule 9: EPS CAGR > 8% (predictable compounding) — 10 pts ────────
        # Munger only buys businesses he can predict a decade out.
        eps_cagr = self._cagr(data.eps_series, window=5)
        eps_pass: bool | None = None
        eps_pts = 0.0
        eps_val: float | None = None
        eps_desc = "Insufficient EPS history for CAGR"
        if eps_cagr is not None:
            eps_val = eps_cagr * 100
            eps_pass = eps_cagr >= 0.08
            eps_pts = 10.0 if eps_pass else 0.0
            eps_desc = f"EPS 5yr CAGR = {eps_cagr*100:.1f}%"
        rules.append(Rule(
            name="EPS CAGR > 8% (predictable compounding)",
            passed=eps_pass or False,
            value=eps_val,
            threshold=8.0,
            points_awarded=eps_pts,
            points_possible=10.0,
            description=eps_desc,
            source="Berkshire Hathaway Annual Meetings — Munger on predictability",
            explanation="Munger only buys businesses whose earnings he can predict a decade out. Consistent EPS growth above 8% annually demonstrates the kind of steady, compounding power Munger seeks — not a single lucky year, but a durable upward trend driven by structural advantages.",
        ))

        # ── Rule 10: Interest coverage > 10× — 5 pts ─────────────────────────
        # Munger: excessive interest is a chain that eventually breaks the business.
        # Note: the inversion rule penalises coverage < 5×; this rewards > 10×.
        int_exp = data.interest_expense
        ic_pass: bool | None = None
        ic_pts = 0.0
        ic_val: float | None = None
        ic_desc = "No interest expense — debt-free"
        if int_exp is not None and int_exp > 0 and data.operating_income_series:
            coverage_e = data.operating_income_series[-1] / int_exp
            ic_val = coverage_e
            ic_pass = coverage_e >= 10.0
            ic_pts = 5.0 if ic_pass else 0.0
            ic_desc = f"Interest coverage = {coverage_e:.1f}×"
        else:
            # No interest expense found → debt-free, full points
            ic_pass = True
            ic_pts = 5.0
        rules.append(Rule(
            name="Interest coverage > 10× (financial fortress)",
            passed=ic_pass or False,
            value=ic_val,
            threshold=10.0,
            points_awarded=ic_pts,
            points_possible=5.0,
            description=ic_desc,
            source="Poor Charlie's Almanack — Munger on financial strength",
            explanation="Munger: 'The chains of habit are too light to be felt until they are too heavy to be broken.' Interest coverage above 10× ensures debt is never life-threatening — even a severe earnings downturn leaves the business solvent. Complements the inversion rule which flags dangerous coverage below 5×.",
        ))

        # ── Rule 11: Operating leverage (OI CAGR ≥ 1.2× Revenue CAGR) — 5 pts
        # Munger loves fixed-cost businesses where profits scale faster than revenue.
        oi_s = data.operating_income_series
        rev_ol = data.revenue_series
        n11 = min(len(oi_s), len(rev_ol), 5)
        ol_pass: bool | None = None
        ol_pts = 0.0
        ol_val: float | None = None
        ol_desc = "Insufficient data for operating leverage"
        rev_cagr = self._cagr(rev_ol, window=n11)
        oi_cagr = self._cagr(oi_s, window=n11)
        if rev_cagr is not None and oi_cagr is not None:
            if rev_cagr > 0:
                leverage_ratio = oi_cagr / rev_cagr
                ol_val = leverage_ratio
                ol_pass = leverage_ratio >= 1.2
                # Partial credit: 0 pts at ratio=1.0, full pts at ratio≥1.2
                partial_score = max(0.0, min(1.0, (leverage_ratio - 1.0) / 0.2))
                ol_pts = 5.0 * partial_score
                ol_desc = (
                    f"OI CAGR {oi_cagr*100:.1f}% vs Revenue CAGR {rev_cagr*100:.1f}% "
                    f"(ratio {leverage_ratio:.2f}×)"
                )
            else:
                ol_desc = f"Revenue CAGR {rev_cagr*100:.1f}% — cannot compute leverage ratio"
        rules.append(Rule(
            name="Operating leverage (OI CAGR ≥ 1.2× Revenue CAGR)",
            passed=ol_pass or False,
            value=ol_val,
            threshold=1.2,
            points_awarded=ol_pts,
            points_possible=5.0,
            description=ol_desc,
            source="Poor Charlie's Almanack — Munger on scalable businesses",
            explanation="Munger loves businesses with a fixed cost base where each incremental dollar of revenue drops disproportionately to the bottom line. When operating income grows at least 20% faster than revenue, the business has positive operating leverage — scale compounds value creation.",
        ))

        return self._build_result(rules, red_flags)

    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _cagr(series: list[float], window: int = 5) -> float | None:
        """CAGR over the last `window` elements. Returns None if start/end ≤ 0."""
        n = min(len(series), window)
        if n < 2:
            return None
        start, end = series[-n], series[-1]
        if start <= 0 or end <= 0:
            return None
        return (end / start) ** (1.0 / (n - 1)) - 1

    def _moat_from_roe(
        self, return_series: list[float], label: str = "ROE",
    ) -> tuple[float | None, str]:
        """Score moat quality 0–1 from ROE (or ROIC fallback) series."""
        if not return_series:
            return None, "No ROE data available"
        avg_ret = statistics.mean(return_series) * 100
        years_above_15 = sum(1 for r in return_series if r > 0.15)
        pct_above_15 = years_above_15 / len(return_series)
        score = min(1.0, pct_above_15 * 1.2)  # slightly generous
        suffix = " (ROIC fallback — negative equity)" if label == "ROIC" else ""
        return score, (
            f"Avg {label} = {avg_ret:.1f}%, {years_above_15}/{len(return_series)} years > 15% "
            f"— {'strong moat' if score > 0.7 else 'moderate moat' if score > 0.4 else 'weak moat'}"
            f"{suffix}"
        )

    def _complexity_check(
        self, data: "FinancialData"
    ) -> tuple[float, str, list[str]]:
        """
        Munger inversion: what could go wrong?
        Returns (complexity_fraction 0-1, description, list_of_inversion_red_flags).
        Four failure conditions:
          1. Weak interest coverage (<5×) — debt servicing strains earnings
          2. Persistent cash burn (≥2 of last 5 FCF years negative)
          3. Eroding gross margins (avg last 3 yrs vs avg first 3 yrs)
          4. Capital trap ((CapEx + R&D) / Revenue > 15%) — reinvestment treadmill
        """
        inversions = []
        complexity_factors = 0
        total_factors = 4

        # Factor 1: Interest coverage < 5× (replaces blunt D/E threshold)
        op_income = data.operating_income_series
        interest_exp = data.interest_expense
        if interest_exp is not None and interest_exp > 0 and op_income:
            coverage = op_income[-1] / interest_exp
            if coverage < 5.0:
                complexity_factors += 1
                inversions.append(
                    f"[Munger Inversion] Interest coverage {coverage:.1f}× — debt burden strains earnings in a downturn"
                )
        # No interest expense → debt-free, no penalty

        # Factor 2: Persistent cash burn (unchanged)
        fcf = data.free_cash_flow_series
        if fcf and len(fcf) >= 2:
            negative_years = sum(1 for f in fcf[-5:] if f < 0)
            if negative_years >= 2:
                complexity_factors += 1
                inversions.append(
                    f"[Munger Inversion] {negative_years} years of negative FCF — cash burn risk"
                )

        # Factor 3: Eroding gross margins — compare avg of first 3 vs last 3 years
        margins = data.gross_margin_series
        if len(margins) >= 6:
            first_avg = statistics.mean(margins[:3])
            last_avg = statistics.mean(margins[-3:])
            if last_avg < first_avg - 0.03:  # more than 3pp structural decline
                complexity_factors += 1
                inversions.append(
                    f"[Munger Inversion] Gross margin eroding ({first_avg*100:.1f}% → {last_avg*100:.1f}%) — pricing power weakening"
                )
        elif len(margins) >= 3 and margins[-1] < margins[0] - 0.05:
            complexity_factors += 1
            inversions.append(
                f"[Munger Inversion] Declining gross margins ({margins[0]*100:.1f}% → {margins[-1]*100:.1f}%) — pricing power erosion"
            )

        # Factor 4: Capital trap — (CapEx + R&D) / Revenue > 15%
        capex = data.capex_series
        rd = data.rd_expense_series
        rev = data.revenue_series
        n = min(len(capex), len(rev))
        if n >= 2:
            rd_n = len(rd)
            ratios = [
                (capex[i] + (rd[i] if i < rd_n else 0.0)) / rev[i]
                for i in range(n) if rev[i] > 0
            ]
            if ratios:
                avg_intensity = statistics.mean(ratios)
                if avg_intensity > 0.15:
                    complexity_factors += 1
                    inversions.append(
                        f"[Munger Inversion] Capital intensity {avg_intensity*100:.1f}% of revenue (CapEx+R&D) — reinvestment treadmill limits free compounding"
                    )

        penalty = complexity_factors / total_factors
        desc = (
            f"{complexity_factors}/{total_factors} inversion risk factors triggered — "
            f"{'fragile' if penalty > 0.5 else 'manageable' if penalty > 0.25 else 'robust'} business"
        )
        return penalty, desc, inversions
