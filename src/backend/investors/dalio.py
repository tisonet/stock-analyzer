"""
Ray Dalio scoring module.

Rules based on:
- "Principles" by Ray Dalio (2017)
- "Principles for Navigating Big Debt Crises" by Ray Dalio (2018)
- Bridgewater Associates All-Weather Portfolio concept
- "Big Debt Crises" framework
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class DalioInvestor(BaseInvestor):
    """
    Ray Dalio scoring: macro-aware, balanced risk, debt cycle positioning.
    Dalio focuses on diversification, economic machine, and risk parity.
    """

    @property
    def name(self) -> str:
        return "Dalio"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: Leverage cycle positioning — 20 pts ────────────────────
        # "Debt/income ratio is the key indicator of where we are in the cycle."
        # Proxy: company D/E relative to sector norms
        de = data.debt_to_equity
        if de is not None and de > 10:
            de = de / 100
        lev_score, lev_desc = self._leverage_score(de, data.sector)
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Sustainable debt/leverage level",
            passed=lev_score >= 0.6,
            value=de if de is not None else None,
            threshold=0.5,
            points_awarded=20.0 * lev_score,
            points_possible=20.0,
            description=lev_desc,
            source="Principles for Navigating Big Debt Crises, Dalio",
            explanation="Dalio evaluates debt levels relative to sector norms, not a universal threshold. Financial companies naturally operate with more leverage than tech companies. D/E is scored against an industry-specific tolerance to determine whether borrowing is conservative, elevated, or excessive for the sector.",
        ))
        if de is not None and de > 2.0:
            red_flags.append(f"D/E of {de:.1f} — company may struggle in a debt deleveraging cycle")

        # ── Rule 2: Geographic diversification — 15 pts ────────────────────
        # Dalio: "Don't have your eggs in one basket; diversify across geographies."
        country = data.country
        is_global = self._is_globally_diversified(data)
        geo_score = 1.0 if is_global else 0.5
        geo_desc = (
            f"Country: {country}. Global revenue diversification detected."
            if is_global
            else f"Country: {country}. Concentrated geographic exposure."
        )
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Geographic revenue diversification",
            passed=is_global,
            value=1.0 if is_global else 0.0,
            threshold=1.0,
            points_awarded=15.0 * geo_score,
            points_possible=15.0,
            description=geo_desc,
            source="Principles, Dalio — diversification as risk management",
            explanation="Dalio's All-Weather philosophy seeks assets resilient across geographies and economic regimes. Companies earning revenue globally are less vulnerable to single-country recessions, currency crises, or geopolitical disruptions — providing natural risk diversification.",
        ))

        # ── Rule 3: Inflation sensitivity (pricing power) — 15 pts ─────────
        # All-Weather portfolio needs assets that work in inflationary environments.
        # Proxy: gross margin trend (rising margins = pricing power = inflation hedge)
        margins = data.gross_margin_series
        pricing_power, pp_desc = self._pricing_power(margins)
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Pricing power (inflation protection)",
            passed=pricing_power >= 0.6,
            value=margins[-1] * 100 if margins else None,
            threshold=30.0,  # 30% gross margin threshold
            points_awarded=15.0 * pricing_power,
            points_possible=15.0,
            description=pp_desc,
            source="Bridgewater All-Weather concept — inflation-hedging assets",
            explanation="In inflationary environments, companies with pricing power can raise prices to protect margins. Gross margin level and trend serve as a proxy: high, stable, or expanding gross margins indicate the ability to pass rising costs to customers — a natural inflation hedge.",
        ))
        if margins and margins[-1] < 0.15:
            red_flags.append(
                f"Gross margin of {margins[-1]*100:.1f}% — vulnerable to cost inflation"
            )

        # ── Rule 4: Earnings stability across economic conditions — 20 pts ──
        # All-Weather: "How does this asset perform in rising/falling growth & inflation?"
        # Proxy: revenue growth consistency (stdev / mean of revenue growth rates)
        rev = data.revenue_series
        stability_score, stability_desc = self._earnings_stability(rev)
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Revenue stability (all-weather resilience)",
            passed=stability_score >= 0.6,
            value=stability_score * 100,
            threshold=60.0,
            points_awarded=20.0 * stability_score,
            points_possible=20.0,
            description=stability_desc,
            source="Bridgewater All-Weather Portfolio framework",
            explanation="Dalio designs for resilience across four economic environments (rising/falling growth, rising/falling inflation). Low coefficient of variation in revenue growth rates proves the business generates stable returns regardless of the economic cycle.",
        ))

        # ── Rule 5: Beta / systematic risk — 15 pts ────────────────────────
        # Dalio prefers uncorrelated returns: lower beta = better for diversified portfolio
        beta = data.beta
        beta_score, beta_desc = self._beta_score(beta)
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Moderate market beta (0.5–1.2)",
            passed=beta_score >= 0.6,
            value=beta,
            threshold=1.2,
            points_awarded=15.0 * beta_score,
            points_possible=15.0,
            description=beta_desc,
            source="Bridgewater risk parity principles",
            explanation="Beta measures stock sensitivity to broad market movements. Beta = 1.0 moves in line with the market. Dalio's risk parity framework favors moderate beta (0.5–1.2): not so defensive it offers no growth, not so cyclical it amplifies portfolio drawdowns in bear markets.",
        ))
        if beta is not None and beta > 1.8:
            red_flags.append(
                f"Beta of {beta:.1f} — highly cyclical; poor in economic downturns"
            )

        # ── Rule 6: Currency/country risk — 15 pts ─────────────────────────
        # Non-US domicile or heavy USD revenue in a weak-$ environment = risk
        currency_score, currency_desc = self._currency_risk(data)
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Low currency concentration risk",
            passed=currency_score >= 0.6,
            value=currency_score * 100,
            threshold=60.0,
            points_awarded=15.0 * currency_score,
            points_possible=15.0,
            description=currency_desc,
            source="Principles for Navigating Big Debt Crises, Dalio — currency risk",
            explanation="Currency exposure is a macro risk factor Dalio monitors carefully. Large multinationals earning revenue in many currencies have natural hedges; domestic companies or those with heavy single-currency exposure face concentrated risk that can erode returns for investors.",
        ))

        return self._build_result(rules, red_flags)

    # ──────────────────────────────────────────────────────────────────────────

    def _leverage_score(self, de: float | None, sector: str) -> tuple[float, str]:
        sector_tolerances = {
            "Financial Services": 3.0, "Real Estate": 2.0,
            "Utilities": 1.5, "Industrials": 1.0,
        }
        tolerance = sector_tolerances.get(sector, 0.8)
        if de is None:
            return 0.5, "D/E unavailable — neutral score"
        normalised = de / tolerance
        score = max(0.0, 1.0 - normalised * 0.5)
        return min(1.0, score), (
            f"D/E={de:.2f} (sector tolerance={tolerance:.1f}) — "
            f"{'conservative' if score > 0.7 else 'elevated' if score > 0.4 else 'excessive'} leverage"
        )

    def _is_globally_diversified(self, data: "FinancialData") -> bool:
        """Heuristic: US-listed companies with large market caps tend to be global."""
        mc = data.market_cap
        sector = data.sector
        # Large-cap non-financial companies tend to have global revenue
        global_sectors = {
            "Technology", "Communication Services", "Consumer Cyclical",
            "Healthcare", "Industrials", "Consumer Defensive",
        }
        return (
            mc is not None
            and mc > 10e9  # > $10B market cap
            and sector in global_sectors
        )

    def _pricing_power(self, margins: list[float]) -> tuple[float, str]:
        if not margins:
            return 0.5, "Gross margin data unavailable — neutral"
        current = margins[-1]
        if len(margins) >= 3:
            trend = (margins[-1] - margins[0]) / max(abs(margins[0]), 0.01)
            trend_bonus = min(0.2, max(-0.2, trend))
        else:
            trend_bonus = 0.0
        score = min(1.0, max(0.0, current / 0.50 + trend_bonus))
        return score, (
            f"Gross margin = {current*100:.1f}% "
            f"({'expanding' if trend_bonus > 0 else 'contracting' if trend_bonus < 0 else 'stable'} trend)"
        )

    def _earnings_stability(self, rev: list[float]) -> tuple[float, str]:
        if len(rev) < 3:
            return 0.5, "Insufficient revenue history — neutral"
        growth_rates = [
            (rev[i] - rev[i - 1]) / abs(rev[i - 1])
            for i in range(1, len(rev))
            if rev[i - 1] != 0
        ]
        if not growth_rates:
            return 0.5, "Cannot compute revenue growth rates"
        avg_g = statistics.mean(growth_rates)
        std_g = statistics.stdev(growth_rates) if len(growth_rates) > 1 else 0
        # Coefficient of variation: lower = more stable
        cv = std_g / max(abs(avg_g), 0.01)
        score = max(0.0, 1.0 - cv * 0.5)
        return min(1.0, score), (
            f"Revenue CAGR={avg_g*100:.1f}%, volatility={std_g*100:.1f}% — "
            f"{'stable' if score > 0.7 else 'moderate' if score > 0.4 else 'volatile'}"
        )

    def _beta_score(self, beta: float | None) -> tuple[float, str]:
        if beta is None:
            return 0.5, "Beta unavailable — neutral"
        # Ideal: 0.5–1.2. Penalise extremes.
        if 0.5 <= beta <= 1.2:
            score = 1.0
        elif beta < 0.5:
            score = 0.7  # too defensive = low return potential
        elif beta <= 1.5:
            score = 0.6
        elif beta <= 2.0:
            score = 0.3
        else:
            score = 0.0
        return score, f"Beta = {beta:.2f} — {'balanced' if score > 0.7 else 'high market sensitivity'}"

    def _currency_risk(self, data: "FinancialData") -> tuple[float, str]:
        country = data.country
        mc = data.market_cap
        # Large US multinationals with diversified revenue = lower single-currency risk
        if country in ("United States", "US"):
            if mc and mc > 50e9:
                return 0.85, "Large US multinational — natural currency diversification"
            return 0.65, "US-domiciled, domestic revenue focus"
        elif country in ("Switzerland", "Netherlands", "United Kingdom"):
            return 0.70, f"{country}-domiciled — some currency risk for USD investors"
        else:
            return 0.50, f"{country}-domiciled — elevated currency risk for USD investors"
