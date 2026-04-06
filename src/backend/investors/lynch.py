"""
Peter Lynch scoring module.

Rules based on:
- "One Up on Wall Street" by Peter Lynch (1989)
- "Beating the Street" by Peter Lynch (1993)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# Lynch company categories and their score weights
CATEGORY_SCORES = {
    "Fast Grower": 15,
    "Stalwart": 11,
    "Turnaround": 9,
    "Asset Play": 8,
    "Slow Grower": 4,
    "Cyclical": 4,
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
            points_possible=20.0,
            description=(
                f"PEG = {peg:.2f} — {'attractive' if peg and peg < 1 else 'expensive'}"
                if peg is not None
                else "PEG unavailable (no growth estimate)"
            ),
            source="One Up on Wall Street, Lynch Ch.13",
            passed=peg < 1.0 if peg is not None else None,
            explanation="The PEG Ratio divides the P/E multiple by the annual EPS growth rate. A PEG below 1.0 means the valuation is cheaper than the growth rate justifies — Lynch's key indicator that you are not overpaying for a growth company's future earnings.",
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
            threshold=11.0,  # Stalwart threshold
            points_awarded=float(category_pts),
            points_possible=15.0,
            description=f"Classified as '{category}' based on EPS growth rate",
            source="One Up on Wall Street, Lynch Ch.3 — Six Categories",
            explanation="Lynch classified companies into 6 types: Fast Growers (20%+ EPS growth), Stalwarts (10-20%), Slow Growers, Cyclicals, Turnarounds, and Asset Plays. Fast Growers and Stalwarts are his preferred types for long-term compounding.",
        )
        rules.append(r2)

        # ── Rule 3: Insider buying signal — 15 pts ─────────────────────────
        # "There's no better tip-off to the probable success of a stock than that
        #  people in the company are buying it." — One Up on Wall Street
        # Threshold scales with market cap: a flat % is unrealistic for mega-caps.
        insider_own = data.insider_ownership_pct
        mkt_cap = data.info.get("marketCap")
        if mkt_cap is not None and mkt_cap > 100e9:
            insider_threshold = 0.001   # > $100B: 0.1%
        elif mkt_cap is not None and mkt_cap > 20e9:
            insider_threshold = 0.005   # $20B–$100B: 0.5%
        elif mkt_cap is not None and mkt_cap > 2e9:
            insider_threshold = 0.01    # $2B–$20B: 1%
        else:
            insider_threshold = 0.02    # < $2B: 2%
        insider_pass = None
        insider_desc = "Insider ownership data unavailable"
        if insider_own is not None:
            insider_pass = insider_own >= insider_threshold
            insider_desc = (
                f"Insider ownership = {insider_own*100:.2f}% "
                f"(threshold {insider_threshold*100:.1f}% for this market cap)"
            )
        r3 = self._make_rule(
            name="Insider ownership (market-cap scaled)",
            value=insider_own * 100 if insider_own is not None else None,
            threshold=insider_threshold * 100,
            points_possible=10.0,
            description=insider_desc,
            source="One Up on Wall Street, Lynch",
            passed=insider_pass,
            explanation="Lynch: insiders buying their own stock is the clearest positive signal. Threshold scales with market cap — 1% is meaningful for a $1B company but unachievable for a $200B one where 0.1% still represents hundreds of millions at stake.",
        )
        rules.append(r3)

        # ── Rule 4: Net cash position (cash > debt) — 5 pts ───────────────
        # Lynch liked companies that could survive adversity without diluting shareholders.
        cash_eq = data.cash_and_equivalents
        total_debt = data.total_debt
        net_cash_val: float | None = None
        net_cash_pass: bool | None = None
        net_cash_desc = "Cash / debt data unavailable"
        if cash_eq is not None and total_debt is not None:
            net_cash_val = cash_eq - total_debt
            net_cash_pass = net_cash_val > 0
            net_cash_desc = (
                f"Net cash ${net_cash_val/1e9:.1f}B "
                f"(cash ${cash_eq/1e9:.1f}B − debt ${total_debt/1e9:.1f}B)"
            )
        r4 = self._make_rule(
            name="Net cash position (cash > debt)",
            value=net_cash_val,
            threshold=0.0,
            points_possible=10.0,
            description=net_cash_desc,
            source="One Up on Wall Street, Lynch — financial strength",
            passed=net_cash_pass,
            explanation="Lynch favoured companies with more cash than debt — they can survive recessions, fund growth internally, and avoid dilutive equity raises. A net cash position is a meaningful margin of safety that lets management focus on the business rather than the balance sheet.",
        )
        rules.append(r4)

        # ── Rule 4b: Revenue growth consistency (5yr CAGR > 10%, stdev < 20%) — 5 pts
        # Lynch's GARP core: growth must be real and predictable, not lumpy.
        rev_s = data.revenue_series
        rev_cagr_pass: bool | None = None
        rev_cagr_pts = 0.0
        rev_cagr_desc = "Insufficient revenue history"
        if len(rev_s) >= 4:
            n = min(len(rev_s), 6)
            cagr = self._cagr(rev_s, window=n)
            yoy = [
                (rev_s[i] - rev_s[i - 1]) / rev_s[i - 1]
                for i in range(len(rev_s) - n + 1, len(rev_s))
                if rev_s[i - 1] > 0
            ]
            stdev_pct = statistics.stdev(yoy) * 100 if len(yoy) >= 2 else None
            if cagr is not None and stdev_pct is not None:
                rev_cagr_pass = cagr >= 0.10 and stdev_pct < 20.0
                rev_cagr_pts = 15.0 if rev_cagr_pass else 0.0
                rev_cagr_desc = (
                    f"Revenue 5yr CAGR = {cagr*100:.1f}%, "
                    f"growth stdev = {stdev_pct:.1f}%"
                )
        rules.append(Rule(
            name="Revenue growth consistent > 10% (stdev < 20%)",
            passed=rev_cagr_pass or False,
            value=None,
            threshold=10.0,
            points_awarded=rev_cagr_pts,
            points_possible=15.0,
            description=rev_cagr_desc,
            source="One Up on Wall Street, Lynch — GARP",
            explanation="Lynch's GARP thesis requires growth to be real and consistent — not just a lucky year. Revenue CAGR above 10% with low volatility (stdev < 20%) confirms the business has a durable growth engine, making future earnings predictable enough to value reliably.",
        ))

        # ── Rule 4c: Gross margin trend (expanding) — 5 pts ────────────────
        # Lynch specifically noted improving margins as a sign of pricing power gain.
        gm_s = data.gross_margin_series
        gm_trend_pass: bool | None = None
        gm_trend_pts = 0.0
        gm_trend_desc = "Insufficient gross margin history"
        if len(gm_s) >= 6:
            first_avg = statistics.mean(gm_s[:3])
            last_avg = statistics.mean(gm_s[-3:])
            gm_trend_pass = last_avg > first_avg
            gm_trend_pts = 10.0 if gm_trend_pass else 0.0
            gm_trend_desc = (
                f"Gross margin {first_avg*100:.1f}% → {last_avg*100:.1f}% "
                f"({'expanding' if gm_trend_pass else 'contracting'})"
            )
        elif len(gm_s) >= 3:
            gm_trend_pass = gm_s[-1] > gm_s[0]
            gm_trend_pts = 10.0 if gm_trend_pass else 0.0
            gm_trend_desc = (
                f"Gross margin {gm_s[0]*100:.1f}% → {gm_s[-1]*100:.1f}% "
                f"({'expanding' if gm_trend_pass else 'contracting'})"
            )
        rules.append(Rule(
            name="Gross margin expanding",
            passed=gm_trend_pass or False,
            value=gm_s[-1] * 100 if gm_s else None,
            threshold=0.0,
            points_awarded=gm_trend_pts,
            points_possible=10.0,
            description=gm_trend_desc,
            source="Beating the Street, Lynch — improving margins",
            explanation="Lynch noted that expanding gross margins signal a business gaining pricing power — either raising prices or reducing costs faster than revenue grows. Sustained margin expansion is one of the most reliable early indicators of a strengthening competitive position.",
        ))

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
            explanation="Lynch checked for years where EPS dropped more than 30% — 'earnings disasters' that destroy investor confidence and often signal deeper problems. A clean EPS history with no disasters confirms stable, predictable profitability.",
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
            points_possible=5.0,
            description=inv_desc,
            source="One Up on Wall Street, Lynch — inventory warning signs",
            passed=inv_score == 1.0 if inv_score is not None else None,
            explanation="Inventory turnover (Revenue ÷ Inventory) measures how quickly a company converts stock into sales. For manufacturing and retail companies, slow turnover (below 4x) may signal weak demand, pricing problems, or excess production — early warning signs of trouble.",
        )
        rules.append(r6)
        if is_inventory_sector and inv_score == 0.0:
            red_flags.append("Slow inventory turnover — potential demand problem or overproduction")

        return self._build_result(rules, red_flags)

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
