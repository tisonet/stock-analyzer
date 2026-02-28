"""
Peter Lynch scoring module.

Rules based on:
- "One Up on Wall Street" by Peter Lynch (1989)
- "Beating the Street" by Peter Lynch (1993)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# Lynch company categories and their score weights
CATEGORY_SCORES = {
    "Fast Grower": 20,
    "Stalwart": 14,
    "Turnaround": 12,
    "Asset Play": 10,
    "Slow Grower": 5,
    "Cyclical": 5,
}

CONSUMER_SECTORS = {
    "Consumer Cyclical", "Consumer Defensive", "Consumer Staples",
    "Communication Services", "Healthcare",
}


class LynchInvestor(BaseInvestor):
    """
    Peter Lynch scoring: growth at a reasonable price (GARP).
    Lynch categorises companies and uses PEG as the primary valuation tool.
    """

    @property
    def name(self) -> str:
        return "Lynch"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: PEG Ratio < 1.0 — 25 pts ──────────────────────────────
        # "The P/E ratio of any company that's fairly priced will equal
        #  its growth rate." — One Up on Wall Street
        peg = data.peg_ratio
        r1 = self._make_rule(
            name="PEG Ratio < 1.0",
            value=peg,
            threshold=1.0,
            points_possible=25.0,
            description=(
                f"PEG = {peg:.2f} — {'attractive' if peg and peg < 1 else 'expensive'}"
                if peg is not None
                else "PEG unavailable (no growth estimate)"
            ),
            source="One Up on Wall Street, Lynch Ch.13",
            passed=peg < 1.0 if peg is not None else None,
        )
        rules.append(r1)
        if peg is not None and peg > 2.5:
            red_flags.append(f"PEG of {peg:.1f} — paying too much for growth")

        # ── Rule 2: Company category — 20 pts ──────────────────────────────
        # Lynch preferred Fast Growers (20-25% annual EPS growth) most
        category, category_pts = self._classify(data)
        r2 = Rule(
            name=f"Company Category: {category}",
            passed=category in ("Fast Grower", "Stalwart"),
            value=float(category_pts),
            threshold=14.0,  # Stalwart threshold
            points_awarded=float(category_pts),
            points_possible=20.0,
            description=f"Classified as '{category}' based on EPS growth rate",
            source="One Up on Wall Street, Lynch Ch.3 — Six Categories",
        )
        rules.append(r2)

        # ── Rule 3: Insider buying signal — 15 pts ─────────────────────────
        # "There's no better tip-off to the probable success of a stock than that
        #  people in the company are buying it." — One Up on Wall Street
        insider_own = data.insider_ownership_pct
        insider_pass = None
        insider_desc = "Insider ownership data unavailable"
        if insider_own is not None:
            insider_pass = insider_own > 0.01  # > 1% = skin in the game
            insider_desc = f"Insider ownership = {insider_own*100:.1f}%"
        r3 = self._make_rule(
            name="Insider Ownership > 1%",
            value=insider_own * 100 if insider_own is not None else None,
            threshold=1.0,
            points_possible=15.0,
            description=insider_desc,
            source="One Up on Wall Street, Lynch",
            passed=insider_pass,
        )
        rules.append(r3)

        # ── Rule 4: Consumer-facing business — 15 pts ──────────────────────
        # Lynch favoured businesses whose products he could observe directly
        # "Buy what you know"
        sector = data.sector
        is_consumer = sector in CONSUMER_SECTORS
        r4 = self._make_rule(
            name="Consumer-facing / 'Buy what you know'",
            value=1.0 if is_consumer else 0.0,
            threshold=1.0,
            points_possible=15.0,
            description=f"Sector: {sector} — {'consumer-facing' if is_consumer else 'institutional/B2B'}",
            source="One Up on Wall Street, Lynch — Buy what you know",
            passed=is_consumer,
        )
        rules.append(r4)

        # ── Rule 5: Revenue/earnings growth consistency — 15 pts ───────────
        # Consistent growth with no earnings disasters in past 5 years
        eps_series = data.eps_series
        growth_consistent = None
        growth_desc = "Insufficient EPS history"
        if len(eps_series) >= 4:
            # Check for any year with EPS decline > 30%
            disasters = 0
            for i in range(1, len(eps_series)):
                if eps_series[i - 1] > 0 and eps_series[i] < eps_series[i - 1] * 0.70:
                    disasters += 1
            growth_consistent = disasters == 0
            growth_rate = data.eps_growth_rate_annual
            if growth_rate is not None:
                growth_desc = f"EPS CAGR = {growth_rate*100:.1f}%, earnings disasters = {disasters}"
            else:
                growth_desc = f"Earnings disasters (>30% drop) = {disasters}"
        r5 = self._make_rule(
            name="Consistent earnings growth (no disasters)",
            value=1.0 if growth_consistent else (0.0 if growth_consistent is not None else None),
            threshold=1.0,
            points_possible=15.0,
            description=growth_desc,
            source="One Up on Wall Street, Lynch Ch.13",
            passed=growth_consistent,
        )
        rules.append(r5)
        if growth_consistent is False:
            red_flags.append("Multiple years of >30% EPS decline — inconsistent earnings")

        # ── Rule 6: Inventory trends (retail/manufacturing) — 10 pts ───────
        # "If inventories are building up, be careful." — One Up on Wall Street
        inv = data.inventory
        rev = data.revenue_series
        inv_score = None
        inv_desc = "Not applicable (non-manufacturing sector) — neutral"
        is_inventory_sector = data.sector in (
            "Consumer Cyclical", "Industrials", "Basic Materials", "Consumer Defensive"
        )
        if is_inventory_sector:
            if inv is not None and len(rev) >= 2 and rev[-1] != 0:
                inv_turnover = rev[-1] / inv if inv > 0 else None
                if inv_turnover:
                    inv_score = 1.0 if inv_turnover > 4 else 0.0
                    inv_desc = f"Inventory turnover = {inv_turnover:.1f}x ({'healthy' if inv_score else 'slow'})"
            else:
                inv_desc = "Inventory data unavailable for this sector"
        else:
            # Not inventory-dependent sector → award neutral points
            inv_score = 1.0
        r6 = self._make_rule(
            name="Healthy inventory turnover",
            value=inv_score,
            threshold=1.0,
            points_possible=10.0,
            description=inv_desc,
            source="One Up on Wall Street, Lynch — inventory warning signs",
            passed=inv_score == 1.0 if inv_score is not None else None,
        )
        rules.append(r6)
        if is_inventory_sector and inv_score == 0.0:
            red_flags.append("Slow inventory turnover — potential demand problem or overproduction")

        return self._build_result(rules, red_flags)

    def _classify(self, data: "FinancialData") -> tuple[str, int]:
        """
        Lynch's 6-category classification based on EPS growth rate.
        Returns (category_name, points).
        """
        growth = data.eps_growth_rate_annual
        if growth is None:
            # Try revenue growth as fallback
            growth = data.info.get("revenueGrowth")

        pe = data.pe_ratio
        bvps = data.book_value_per_share
        pb = data.pb_ratio
        mc = data.market_cap
        total_assets = data.total_assets
        total_liab = data.total_liabilities

        # Asset Play: significant hidden assets (tangible book > 1.5x market cap)
        if (
            bvps is not None
            and pe is not None
            and pb is not None
            and pb < 0.7
        ):
            return "Asset Play", CATEGORY_SCORES["Asset Play"]

        # Turnaround: negative EPS turning positive or major restructuring signal
        eps = data.eps_series
        if eps and len(eps) >= 2 and eps[-2] < 0 and eps[-1] > 0:
            return "Turnaround", CATEGORY_SCORES["Turnaround"]

        if growth is None:
            return "Stalwart", CATEGORY_SCORES["Stalwart"]

        if growth > 0.20:
            return "Fast Grower", CATEGORY_SCORES["Fast Grower"]
        elif growth > 0.10:
            return "Stalwart", CATEGORY_SCORES["Stalwart"]
        elif growth > 0.02:
            return "Slow Grower", CATEGORY_SCORES["Slow Grower"]
        else:
            # Low/no growth → Cyclical or Slow Grower
            sector = data.sector
            if sector in ("Industrials", "Basic Materials", "Energy", "Consumer Cyclical"):
                return "Cyclical", CATEGORY_SCORES["Cyclical"]
            return "Slow Grower", CATEGORY_SCORES["Slow Grower"]
