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

        # ── Rule 1: Simple, understandable business — 20 pts ───────────────
        # "Munger's #1 rule: if you can't understand it, don't own it."
        # Proxy: length & complexity of business description + number of segments
        simplicity_score, simplicity_desc = self._business_simplicity(data)
        r1 = self._make_rule(
            name="Simple, understandable business model",
            value=simplicity_score,
            threshold=0.6,   # 0–1 scale
            points_possible=20.0,
            description=simplicity_desc,
            source="Poor Charlie's Almanack, Kaufman — Munger's mental models",
            passed=simplicity_score >= 0.6 if simplicity_score is not None else None,
            partial=simplicity_score if simplicity_score is not None else 0.0,
        )
        # Override points with partial credit
        from src.backend.investors.base_investor import Rule as R
        if simplicity_score is not None:
            rules.append(R(
                name=r1.name, passed=r1.passed, value=r1.value,
                threshold=r1.threshold,
                points_awarded=20.0 * simplicity_score,
                points_possible=r1.points_possible,
                description=r1.description, source=r1.source,
                explanation="Munger only invests in businesses simple enough to understand fully. This rule proxies simplicity via the length of the business description: concise descriptions suggest a focused, understandable business; long complex ones suggest hard-to-analyze conglomerates.",
            ))
        else:
            rules.append(r1)

        # ── Rule 2: Management skin in the game (insider ownership > 5%) — 20 pts
        # "Show me the incentive and I'll show you the outcome." — Munger
        insider_own = data.insider_ownership_pct
        r2 = self._make_rule(
            name="Insider Ownership > 5%",
            value=insider_own * 100 if insider_own is not None else None,
            threshold=5.0,
            points_possible=20.0,
            description=(
                f"Insiders own {insider_own*100:.1f}% of company"
                if insider_own is not None
                else "Insider ownership data unavailable"
            ),
            source="Poor Charlie's Almanack — incentive alignment",
            explanation="When executives own significant equity, their personal wealth rises and falls with shareholder returns, aligning incentives. Insider ownership above 5% is evidence of 'skin in the game' — management has a personal financial stake in the company's success.",
        )
        rules.append(r2)
        if insider_own is not None and insider_own < 0.01:
            red_flags.append("Insiders own < 1% — management not aligned with shareholders")

        # ── Rule 3: Qualitative moat — ROE consistency proxy — 25 pts ──────
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
        r3_pts = 25.0 * roe_score if roe_score is not None else 0.0
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Durable economic moat (ROE consistency)",
            passed=roe_score is not None and roe_score >= 0.6,
            value=statistics.mean(return_series) * 100 if return_series else None,
            threshold=15.0,   # 15% avg ROE as moat threshold
            points_awarded=r3_pts,
            points_possible=25.0,
            description=roe_desc,
            source="Seeking Wisdom, Bevelin — Munger on competitive advantages",
            explanation="Return on Equity (ROE) measures how much profit the company earns on shareholders' money. Consistently high ROE across many years implies a durable competitive advantage that competitors cannot erode — Munger's primary quality test. Falls back to ROIC for companies with negative equity (buyback-heavy firms like FICO, MCD, SBUX).",
        ))
        if return_series and statistics.mean(return_series) < 0.08:
            red_flags.append(f"Average {return_label} below 8% — weak or non-existent economic moat")

        # ── Rule 4: Penalise excessive complexity — 20 pts ─────────────────
        # "Munger's inversion: list what would make this business fail.
        #  Complexity + many segments = fragility." — Poor Charlie's Almanack
        complexity_penalty, complexity_desc, inversions = self._complexity_check(data)
        red_flags.extend(inversions)
        simplicity_pts = 20.0 * (1.0 - complexity_penalty)
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Low business complexity (Munger inversion)",
            passed=complexity_penalty < 0.4,
            value=complexity_penalty * 100,   # % complexity score
            threshold=40.0,
            points_awarded=simplicity_pts,
            points_possible=20.0,
            description=complexity_desc,
            source="Poor Charlie's Almanack — Invert, always invert",
            explanation="Munger's 'inversion' principle: instead of asking what could go well, ask what could go wrong. This rule checks four failure conditions: high leverage, cash burn, declining margins, extreme valuation. Fewer triggered factors means the business is more resilient.",
        ))

        # ── Rule 5: Return on Equity consistency — 15 pts ──────────────────
        # Low variance in ROE = pricing power = moat
        # Falls back to ROIC when equity is negative.
        roe_consistency_pts = 0.0
        roe_consistency_desc = f"Insufficient {return_label} history"
        roe_consistency_pass = None
        if len(return_series) >= 4:
            stdev = statistics.stdev(return_series) * 100
            avg_ret = statistics.mean(return_series) * 100
            roe_consistency_pass = stdev < 5.0 and avg_ret > 12.0
            roe_consistency_pts = 15.0 if roe_consistency_pass else 0.0
            roe_consistency_desc = f"{return_label} avg={avg_ret:.1f}%, stdev={stdev:.1f}%"
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="ROE consistent > 12% (stdev < 5%)",
            passed=roe_consistency_pass or False,
            value=statistics.mean(return_series) * 100 if return_series else None,
            threshold=12.0,
            points_awarded=roe_consistency_pts,
            points_possible=15.0,
            description=roe_consistency_desc,
            source="Berkshire Hathaway Annual Letters — Munger on business quality",
            explanation="Low variance in Return on Equity (standard deviation below 5%) combined with a strong average (above 12%) indicates a business with stable, predictable returns. This consistency reflects genuine competitive protection — not just a lucky year. Falls back to ROIC for companies with negative equity.",
        ))

        return self._build_result(rules, red_flags)

    # ──────────────────────────────────────────────────────────────────────────

    def _business_simplicity(self, data: "FinancialData") -> tuple[float | None, str]:
        """
        Score 0–1: simpler = higher score.
        Heuristics: description word count (< 100 words = simple),
        number of distinct sectors mentioned.
        """
        summary = data.business_summary
        if not summary:
            return 0.5, "Business description unavailable — neutral score"
        words = len(summary.split())
        # Simple businesses have shorter, clearer descriptions
        if words < 80:
            score = 1.0
            desc = f"Concise business description ({words} words) — easily understood"
        elif words < 150:
            score = 0.75
            desc = f"Moderate description length ({words} words)"
        elif words < 250:
            score = 0.50
            desc = f"Complex description ({words} words) — harder to understand"
        else:
            score = 0.25
            desc = f"Very complex description ({words} words) — Munger would likely avoid"
        return score, desc

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
        """
        inversions = []
        complexity_factors = 0
        total_factors = 4

        de = data.debt_to_equity
        if de is not None and de > 1.0:
            complexity_factors += 1
            inversions.append(
                f"[Munger Inversion] High leverage (D/E={de:.1f}) could amplify losses in a downturn"
            )

        fcf = data.free_cash_flow_series
        if fcf and len(fcf) >= 2:
            negative_years = sum(1 for f in fcf[-5:] if f < 0)
            if negative_years >= 2:
                complexity_factors += 1
                inversions.append(
                    f"[Munger Inversion] {negative_years} years of negative FCF — cash burn risk"
                )

        margins = data.gross_margin_series
        if len(margins) >= 3 and margins[-1] < margins[0]:
            complexity_factors += 1
            inversions.append(
                "[Munger Inversion] Declining gross margins — pricing power erosion"
            )

        pe = data.pe_ratio
        if pe is not None and pe > 40:
            complexity_factors += 1
            inversions.append(
                f"[Munger Inversion] P/E of {pe:.0f}x — tiny valuation error destroys the investment"
            )

        penalty = complexity_factors / total_factors
        desc = (
            f"{complexity_factors}/{total_factors} inversion risk factors triggered — "
            f"{'fragile' if penalty > 0.5 else 'manageable' if penalty > 0.25 else 'robust'} business"
        )
        return penalty, desc, inversions
