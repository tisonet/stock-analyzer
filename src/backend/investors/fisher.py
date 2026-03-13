"""
Phil Fisher — Common Stocks and Uncommon Profits scoring module.

Fisher (1907-2004) was a pioneering growth investor who influenced Warren Buffett's
shift from pure value to quality-growth investing. His approach centres on buying and
holding outstanding growth companies for decades, emphasising revenue growth, R&D
commitment, improving profit margins, and management quality.

Core philosophy:
  - Revenue growth is the #1 priority — "sizable sales increases over several years"
  - R&D commitment drives future growth (Points 2 & 3 of his 15-point checklist)
  - Profit margins should be improving, not just high (Points 4 & 5)
  - Growth should be consistent over time, not cyclical spikes (Point 11)
  - Avoid companies that dilute shareholders to fund growth (Point 12)
  - Willing to pay a premium for truly outstanding growth companies
  - "If the job has been correctly done, the time to sell is almost never"

Sources:
  - Fisher, "Common Stocks and Uncommon Profits" (1958), Chapters 3-5
  - Fisher, "Paths to Wealth Through Common Stocks" (1960)
  - Fisher, "Conservative Investors Sleep Well" (1975)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# Sectors where formal R&D spending is not the primary growth driver.
# Fisher acknowledged that not all industries invest through a "Research And
# Development" line item — banks grow through lending, utilities through
# infrastructure, energy through exploration.  For these sectors the R&D rule
# awards a neutral pass rather than penalising the company.
_NON_RD_SECTORS = frozenset({
    "Financial Services",
    "Real Estate",
    "Utilities",
    "Energy",
    "Basic Materials",
})


class FisherInvestor(BaseInvestor):
    """
    Phil Fisher / Common Stocks and Uncommon Profits scoring.
    Seeks outstanding growth companies with strong R&D commitment, improving
    margins, consistent revenue growth, and minimal shareholder dilution.
    Willing to pay a premium for truly superior growth — no valuation rule.
    """

    @property
    def name(self) -> str:
        return "Fisher"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: Revenue Growth CAGR >= 10% — 25 pts ────────────────
        # Fisher's first and most important question: "Does the company have
        # products or services with sufficient market potential to make possible
        # a sizable increase in sales for at least several years?"
        rev_s = data.revenue_series
        rev_cagr: float | None = None
        rev_years = 0
        if len(rev_s) >= 3 and rev_s[0] > 0 and rev_s[-1] > 0:
            rev_years = len(rev_s) - 1
            rev_cagr = float((rev_s[-1] / rev_s[0]) ** (1 / rev_years) - 1)

        r1 = self._make_rule(
            name="Revenue Growth CAGR >= 10%",
            value=rev_cagr * 100 if rev_cagr is not None else None,
            threshold=10.0,
            points_possible=25.0,
            description=(
                f"Revenue CAGR = {rev_cagr * 100:.1f}% over {rev_years} years — "
                f"{'sizable growth demonstrating strong market potential'  if rev_cagr >= 0.10 else 'growth below Fishers bar for outstanding companies'}"
                if rev_cagr is not None
                else "Insufficient revenue data for CAGR calculation"
            ),
            source=(
                "Common Stocks and Uncommon Profits, Ch.3 — Point 1: "
                "'Does the company have products with sufficient market potential "
                "for a sizable increase in sales for at least several years?'"
            ),
            explanation=(
                "Fisher's first and most heavily weighted question. He sought companies "
                "whose products or services could generate substantial, sustained revenue "
                "growth. A 10% annual CAGR demonstrates the kind of market opportunity "
                "that justifies a decades-long hold."
            ),
        )
        rules.append(r1)
        if not r1.passed and rev_cagr is not None and rev_cagr < 0:
            red_flags.append(
                f"Declining revenue (CAGR {rev_cagr * 100:.1f}%) — Fisher requires "
                "sizable sales growth potential; a shrinking topline disqualifies "
                "the investment"
            )

        # ── Rule 2: R&D Commitment (R&D/Revenue >= 5%) — 20 pts ────────
        # Fisher's Points 2 & 3: Does management invest in future growth
        # through new products and processes?  How effective is the R&D?
        rnd_s = data._series(
            data.income_stmt,
            "Research And Development",
            "ResearchAndDevelopment",
        )
        rev_for_rd = data.revenue_series
        n_rd = min(len(rnd_s), len(rev_for_rd))
        rd_ratios: list[float] = []
        for i in range(n_rd):
            if rev_for_rd[i] > 0:
                rd_ratios.append(float(rnd_s[i] / rev_for_rd[i]))
        rd_ratio = statistics.mean(rd_ratios) if rd_ratios else None

        sector = data.sector
        # Sector-aware: non-R&D sectors get a neutral pass
        if rd_ratio is not None:
            r2_value = float(rd_ratio * 100)
            r2_passed = bool(rd_ratio >= 0.05)
            r2_desc = (
                f"R&D/Revenue = {rd_ratio * 100:.1f}% — "
                f"{'strong commitment to future growth through innovation' if r2_passed else 'R&D investment below Fishers 5% threshold'}"
            )
        elif sector in _NON_RD_SECTORS:
            r2_value = 0.0
            r2_passed = True
            r2_desc = (
                f"Non-R&D sector ({sector}) — neutral pass; Fisher acknowledged "
                "growth drivers differ by industry"
            )
        else:
            r2_value = None
            r2_passed = None
            r2_desc = (
                f"R&D data unavailable for {sector} company — "
                "cannot assess commitment to future product development"
            )

        r2 = self._make_rule(
            name="R&D Commitment (R&D/Revenue >= 5%)",
            value=r2_value,
            threshold=5.0,
            points_possible=20.0,
            description=r2_desc,
            source=(
                "Common Stocks and Uncommon Profits, Ch.3 — Points 2 & 3: "
                "'Does management develop new products/processes to continue growth "
                "when current product lines mature?'"
            ),
            passed=r2_passed,
            explanation=(
                "Fisher believed R&D spending was the engine of future growth. "
                "Companies must invest in new products and processes to avoid "
                "obsolescence. R&D above 5% of revenue demonstrates management's "
                "commitment to sustaining growth beyond current product lines."
            ),
        )
        rules.append(r2)
        if (not r2.passed and rd_ratio is not None
                and rd_ratio < 0.02 and sector not in _NON_RD_SECTORS):
            red_flags.append(
                f"Minimal R&D investment ({rd_ratio * 100:.1f}% of revenue) in an "
                "R&D-dependent sector — Fisher would question management's commitment "
                "to future growth"
            )

        # ── Rule 3: Operating Margin Trend (stable or improving) — 15 pts
        # Fisher's Points 4 & 5: "Does the company have a worthwhile profit
        # margin?" and "What is it doing to maintain or improve margins?"
        op_s = data.operating_income_series
        rev_for_margin = data.revenue_series
        n_om = min(len(op_s), len(rev_for_margin))
        op_margins: list[float] = []
        for i in range(n_om):
            if rev_for_margin[i] > 0:
                op_margins.append(float(op_s[i] / rev_for_margin[i]))

        margin_delta: float | None = None
        early_avg: float | None = None
        late_avg: float | None = None
        if len(op_margins) >= 3:
            mid = len(op_margins) // 2
            early_avg = statistics.mean(op_margins[:mid])
            late_avg = statistics.mean(op_margins[mid:])
            margin_delta = late_avg - early_avg

        r3 = self._make_rule(
            name="Operating Margin Trend (stable or improving)",
            value=margin_delta * 100 if margin_delta is not None else None,
            threshold=-2.0,
            points_possible=15.0,
            description=(
                f"Op margin trend: {early_avg * 100:.1f}% → {late_avg * 100:.1f}% "
                f"(Δ{margin_delta * 100:+.1f}pp) — "
                f"{'margins stable or improving as business scales' if margin_delta >= -0.02 else 'deteriorating margins signal competitive erosion'}"
                if margin_delta is not None
                else "Insufficient data for margin trend analysis"
            ),
            source=(
                "Common Stocks and Uncommon Profits, Ch.3 — Points 4 & 5: "
                "'Does the company have a worthwhile profit margin? What is it doing "
                "to maintain or improve profit margins?'"
            ),
            explanation=(
                "Fisher specifically asked about profit margin trends, not just "
                "current levels. He wanted companies where margins were improving "
                "as the business scaled, or at minimum stable. Deteriorating margins "
                "signal competitive erosion or cost inflation outpacing growth."
            ),
        )
        rules.append(r3)
        if not r3.passed and margin_delta is not None and margin_delta < -0.05:
            red_flags.append(
                f"Operating margins declining sharply ({margin_delta * 100:+.1f}pp) — "
                "Fisher would question whether revenue growth is translating to "
                "shareholder value"
            )

        # ── Rule 4: Revenue Growth Consistency (>= 75% of years) — 15 pts
        # Fisher's Point 11: "Does the company have a short-range or
        # long-range outlook in regard to profits?"
        positive_years = 0
        total_years = 0
        if len(rev_s) >= 3:
            for i in range(1, len(rev_s)):
                total_years += 1
                if rev_s[i] > rev_s[i - 1]:
                    positive_years += 1
        consistency_pct = (
            positive_years / total_years * 100 if total_years > 0 else None
        )

        r4 = self._make_rule(
            name="Revenue Growth Consistency (>= 75% of years)",
            value=consistency_pct,
            threshold=75.0,
            points_possible=15.0,
            description=(
                f"Revenue grew in {positive_years}/{total_years} years "
                f"({consistency_pct:.0f}%) — "
                f"{'sustained growth confirms long-range management outlook' if consistency_pct >= 75 else 'inconsistent growth suggests short-range thinking or cyclicality'}"
                if consistency_pct is not None
                else "Insufficient revenue history for consistency analysis"
            ),
            source=(
                "Common Stocks and Uncommon Profits, Ch.3 — Point 11: "
                "'Does the company have a short-range or long-range outlook "
                "in regard to profits?'"
            ),
            explanation=(
                "Fisher sought companies with a long-range outlook — consistent "
                "growth across years, not one-time spikes. Revenue growing in at "
                "least 75% of years demonstrates sustained growth through varying "
                "economic conditions."
            ),
        )
        rules.append(r4)
        if (not r4.passed and consistency_pct is not None
                and consistency_pct < 50):
            red_flags.append(
                f"Revenue grew in only {positive_years}/{total_years} years — "
                "highly inconsistent; Fisher required sustained multi-year growth"
            )

        # ── Rule 5: Earnings Growth Alignment (EPS CAGR >= 8%) — 10 pts ─
        # Fisher expected revenue growth to flow through to earnings.
        # Growth without profit growth was suspicious.
        eps_s = data.eps_series
        eps_cagr: float | None = None
        eps_years = 0
        if len(eps_s) >= 3 and eps_s[0] > 0 and eps_s[-1] > 0:
            eps_years = len(eps_s) - 1
            eps_cagr = float((eps_s[-1] / eps_s[0]) ** (1 / eps_years) - 1)
        if eps_cagr is None:
            fallback = data.eps_growth_rate_annual
            if fallback is not None:
                eps_cagr = fallback

        r5 = self._make_rule(
            name="Earnings Growth Alignment (EPS CAGR >= 8%)",
            value=eps_cagr * 100 if eps_cagr is not None else None,
            threshold=8.0,
            points_possible=10.0,
            description=(
                f"EPS CAGR = {eps_cagr * 100:.1f}% "
                f"{'over ' + str(eps_years) + ' years' if eps_years > 0 else '(analyst estimate)'} — "
                f"{'earnings compounding alongside revenue' if eps_cagr >= 0.08 else 'earnings growth lagging revenue — possible margin compression or dilution'}"
                if eps_cagr is not None
                else "EPS data unavailable"
            ),
            source=(
                "Common Stocks and Uncommon Profits, Fisher — "
                "'Revenue growth without corresponding earnings growth signals "
                "margin compression, rising costs, or dilution'"
            ),
            explanation=(
                "Revenue growth without corresponding earnings growth signals "
                "margin compression, rising costs, or dilution. Fisher expected "
                "profitable growth — EPS should compound alongside the top line. "
                "8% EPS CAGR ensures growth translates into shareholder value."
            ),
        )
        rules.append(r5)
        if (not r5.passed and eps_cagr is not None and eps_cagr < 0
                and rev_cagr is not None and rev_cagr > 0):
            red_flags.append(
                "Revenue growing but earnings declining — Fisher would see this "
                "as a critical disconnect between topline growth and shareholder value"
            )

        # ── Rule 6: Low Share Dilution (<= 2% total growth) — 10 pts ───
        # Fisher's Point 12: "Will the growth of the company require
        # sufficient equity financing so that the larger number of shares
        # will largely cancel the existing stockholders' benefit?"
        shares = data.shares_outstanding_series
        shares_change: float | None = None
        if len(shares) >= 2 and shares[0] > 0:
            shares_change = float(shares[-1] / shares[0] - 1)

        r6 = self._make_rule(
            name="Low Share Dilution (<= 2% total growth)",
            value=shares_change * 100 if shares_change is not None else None,
            threshold=2.0,
            points_possible=10.0,
            description=(
                f"Shares changed {shares_change * 100:+.1f}% over {len(shares)} years — "
                f"{'minimal dilution; growth funded from operations' if shares_change <= 0.02 else 'significant dilution; growth funded by share issuance'}"
                if shares_change is not None
                else "Share count data unavailable"
            ),
            source=(
                "Common Stocks and Uncommon Profits, Ch.3 — Point 12: "
                "'Will growth require equity financing that cancels existing "
                "stockholders benefit?'"
            ),
            passed=(
                bool(shares_change <= 0.02) if shares_change is not None else None
            ),
            explanation=(
                "Fisher explicitly warned about equity dilution. If a company must "
                "issue shares to fund growth, existing shareholders' per-share benefit "
                "is cancelled. Companies that grow without diluting demonstrate the "
                "self-funding quality Fisher required."
            ),
        )
        rules.append(r6)
        if (not r6.passed and shares_change is not None
                and shares_change > 0.10):
            red_flags.append(
                f"Significant equity dilution ({shares_change * 100:+.1f}%) — "
                "Fisher's Point 12: growth funded by share issuance cancels "
                "per-share benefit for existing shareholders"
            )

        # ── Rule 7: Long-term Price Appreciation — 5 pts ───────────────
        # Fisher's buy-and-hold thesis: the market eventually recognises
        # outstanding businesses.  This is a low-weight sanity check.
        long_term_return: float | None = None
        if not data.history.empty and "Close" in data.history.columns:
            prices = data.history["Close"]
            if len(prices) >= 252:
                long_term_return = float(prices.iloc[-1] / prices.iloc[0] - 1)

        r7 = self._make_rule(
            name="Long-term Price Appreciation (positive return)",
            value=long_term_return * 100 if long_term_return is not None else None,
            threshold=0.0,
            points_possible=5.0,
            description=(
                f"Long-term price return = {long_term_return * 100:+.1f}% — "
                f"{'market has validated the growth story' if long_term_return >= 0 else 'negative long-term return raises questions about the growth thesis'}"
                if long_term_return is not None
                else "Insufficient price history"
            ),
            source=(
                "Common Stocks and Uncommon Profits, Fisher — "
                "'If the job has been correctly done when the common stock is "
                "purchased, the time to sell it is — almost never'"
            ),
            explanation=(
                "Fisher believed the stock market eventually recognises outstanding "
                "businesses. A positive long-term return confirms the market has "
                "validated the company's growth story."
            ),
        )
        rules.append(r7)

        return self._build_result(rules, red_flags)
