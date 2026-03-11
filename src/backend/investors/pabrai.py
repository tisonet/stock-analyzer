"""
Mohnish Pabrai scoring module.

Rules based on:
- "The Dhandho Investor" by Mohnish Pabrai (2007)
- "Mosaic: Perspectives on Investing" by Mohnish Pabrai (2004)
- Pabrai Investment Funds annual letters and public lectures
- Uber Cannibals framework (Pabrai's original contribution)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# Pabrai uses a simple back-of-envelope DCF: 10% discount rate, 10x FCF exit
DCF_DISCOUNT_RATE = 0.10
DCF_EXIT_MULTIPLE = 10


class PabraiInvestor(BaseInvestor):
    """
    Mohnish Pabrai scoring: Dhandho framework — low risk, high uncertainty,
    few bets, big bets, infrequent bets.

    Core philosophy: "Heads I win, tails I don't lose much."
    Emphasis on minimal leverage, high FCF yield, share cannibalism,
    and buying simple businesses at deep discounts.
    """

    @property
    def name(self) -> str:
        return "Pabrai"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: Low Leverage (D/E < 0.3) — 20 pts ───────────────────
        # "The single biggest reason why investments don't work out is leverage."
        # — Pabrai, Columbia Business School lecture
        # His checklist dedicates ~30% of questions to leverage risk.
        de = data.debt_to_equity
        if de is not None and de > 10:
            de = de / 100
        de_pts = 0.0
        if de is not None:
            if de <= 0.0:
                de_pts = 20.0  # zero debt = perfect
            elif de <= 0.3:
                de_pts = 20.0
            elif de <= 0.5:
                de_pts = 12.0  # acceptable but not ideal
            else:
                de_pts = 0.0
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Low Leverage (D/E < 0.3)",
            passed=de is not None and de <= 0.3,
            value=de,
            threshold=0.3,
            points_awarded=de_pts,
            points_possible=20.0,
            description=(
                f"D/E = {de:.2f}"
                + (" — zero debt, Pabrai's ideal" if de is not None and de <= 0 else "")
                if de is not None else "D/E unavailable"
            ),
            source="The Dhandho Investor, Ch.2 — Minimize downside risk",
            explanation=(
                "Pabrai identifies leverage as the #1 reason investments fail. "
                "His checklist dedicates ~30% of questions to leverage risk. "
                "Zero debt is ideal; D/E below 0.3 provides strong downside protection."
            ),
        ))
        if de is not None and de > 1.0:
            red_flags.append(
                f"D/E = {de:.1f} — leverage is Pabrai's top risk factor"
            )

        # ── Rule 2: High ROIC (10yr avg > 15%) — 15 pts ─────────────────
        # "A classic definition of a great business is high returns on equity
        #  with no use of leverage." — Pabrai
        # Capital-light businesses with high ROIC are his "holy grail."
        roic_series = data.roic_series
        roic_avg = statistics.mean(roic_series) if roic_series else None
        r2 = self._make_rule(
            name="ROIC > 15% (10yr avg)",
            value=roic_avg * 100 if roic_avg is not None else None,
            threshold=15.0,
            points_possible=15.0,
            description=(
                f"10yr avg ROIC = {roic_avg*100:.1f}%"
                if roic_avg is not None else "No ROIC data"
            ),
            source="The Dhandho Investor — Capital-light businesses",
            explanation=(
                "Pabrai seeks capital-light businesses with high returns on invested capital. "
                "A business's ROIC caps your investment return — he looks for businesses "
                "that can grow at 15%+ per year with minimal capital reinvestment."
            ),
        )
        rules.append(r2)
        if not r2.passed and roic_avg is not None and roic_avg < 0.08:
            red_flags.append("ROIC below 8% — not a capital-efficient business")

        # ── Rule 3: FCF Yield > 8% — 15 pts ─────────────────────────────
        # "Heads I win, tails I don't lose much" — strong FCF = downside protection
        # Pabrai's portfolio trades at ~11x P/E implying high earnings/FCF yield.
        market_cap = data.market_cap
        fcf = data.free_cash_flow_series
        fcf_yield = None
        if fcf and market_cap and market_cap > 0:
            fcf_yield = (fcf[-1] / market_cap) * 100
        r3 = self._make_rule(
            name="FCF Yield > 8%",
            value=fcf_yield,
            threshold=8.0,
            points_possible=15.0,
            description=(
                f"FCF Yield = {fcf_yield:.1f}%"
                if fcf_yield is not None else "FCF/market cap unavailable"
            ),
            source="The Dhandho Investor, Ch.3 — Heads I win, tails I don't lose much",
            explanation=(
                "Free cash flow yield (FCF / market cap) measures how much cash the business "
                "generates relative to its price. Pabrai targets asymmetric payoffs — "
                "a high FCF yield means rapid payback and limited downside if things go wrong."
            ),
        )
        rules.append(r3)
        if fcf_yield is not None and fcf_yield < 2:
            red_flags.append("FCF yield < 2% — paying too much for the cash flow stream")

        # ── Rule 4: Low P/E (< 15) — 15 pts ─────────────────────────────
        # Pabrai's portfolio trades at a trailing P/E around 11, vs S&P 500 avg ~20.
        # "If you need to run a spreadsheet, that's a red flag — take a pass."
        pe = data.pe_ratio
        pe_pts = 0.0
        if pe is not None and pe > 0:
            if pe <= 11:
                pe_pts = 15.0  # Pabrai's sweet spot
            elif pe <= 15:
                pe_pts = 10.0
            elif pe <= 20:
                pe_pts = 5.0
            else:
                pe_pts = 0.0
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Low P/E (< 15)",
            passed=pe is not None and 0 < pe <= 15,
            value=pe,
            threshold=15.0,
            points_awarded=pe_pts,
            points_possible=15.0,
            description=(
                f"P/E = {pe:.1f}x"
                + (" — in Pabrai's sweet spot" if pe is not None and 0 < pe <= 11 else "")
                if pe is not None else "P/E unavailable"
            ),
            source="Pabrai Investment Funds Letters — Portfolio avg P/E ~11",
            explanation=(
                "Pabrai's portfolio historically trades at a trailing P/E around 11 — "
                "far below market average. A low P/E provides a large margin of safety "
                "and ensures the 'heads I win' payoff if the business performs adequately."
            ),
        ))
        if pe is not None and pe > 30:
            red_flags.append(f"P/E = {pe:.0f} — far above Pabrai's valuation threshold")

        # ── Rule 5: Share Cannibalism (Uber Cannibals) — 10 pts ──────────
        # Pabrai's original framework: companies aggressively buying back
        # shares at fair or cheap prices. Uber Cannibal criteria include
        # declining share count + P/S < 2.5.
        shares = data.shares_outstanding_series
        rev = data.revenue_series
        ps_ratio = None
        if rev and market_cap and market_cap > 0 and rev[-1] > 0:
            ps_ratio = market_cap / rev[-1]

        cannibal = False
        cannibal_desc = "Share count history unavailable"
        if len(shares) >= 3:
            share_declining = shares[-1] < shares[0]
            if share_declining:
                reduction_pct = (1 - shares[-1] / shares[0]) * 100
                if ps_ratio is not None and ps_ratio < 2.5:
                    cannibal = True
                    cannibal_desc = (
                        f"Shares down {reduction_pct:.1f}% + P/S = {ps_ratio:.1f}x "
                        f"— buying back at reasonable valuations"
                    )
                elif ps_ratio is not None:
                    cannibal_desc = (
                        f"Shares down {reduction_pct:.1f}% but P/S = {ps_ratio:.1f}x > 2.5 "
                        f"— buybacks at expensive prices"
                    )
                else:
                    cannibal_desc = f"Shares down {reduction_pct:.1f}% (P/S unavailable)"
            else:
                growth_pct = (shares[-1] / shares[0] - 1) * 100
                cannibal_desc = f"Shares UP {growth_pct:.1f}% — diluting shareholders"
        r5 = self._make_rule(
            name="Uber Cannibal (buybacks at fair price)",
            value=1.0 if cannibal else 0.0,
            threshold=1.0,
            points_possible=10.0,
            description=cannibal_desc,
            source="Pabrai's Uber Cannibals Framework",
            passed=cannibal,
            explanation=(
                "Pabrai's Uber Cannibals are companies aggressively reducing share count "
                "at reasonable valuations (P/S < 2.5). The formula: Earnings Growth x "
                "(100 / share % left) x Multiple Expansion. This screen returned 15.5% "
                "annualized (1992-2016) vs 9.2% for the S&P 500."
            ),
        )
        rules.append(r5)

        # ── Rule 6: Margin of Safety (Simple DCF) — 15 pts ──────────────
        # "Buy a dollar bill for forty cents, thirty cents, or maybe twenty cents."
        # Pabrai uses back-of-envelope DCF: average FCF x exit multiple,
        # discounted at 10%. No spreadsheets needed.
        mos, mos_desc = self._simple_dcf(data)
        mos_pts = 0.0
        if mos is not None:
            if mos >= 0.33:
                mos_pts = 15.0  # 33%+ margin = full points
            elif mos > 0:
                mos_pts = 15.0 * (mos / 0.33)  # partial credit
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Margin of Safety ≥ 33% (simple DCF)",
            passed=mos is not None and mos >= 0.33,
            value=mos * 100 if mos is not None else None,
            threshold=33.0,
            points_awarded=mos_pts,
            points_possible=15.0,
            description=mos_desc,
            source="The Dhandho Investor, Ch.4 — Buying dollar bills for far less",
            explanation=(
                "Pabrai's simple DCF: average FCF x 10x exit multiple, discounted at 10%. "
                "He wants to buy 'a dollar bill for forty cents' — a 33%+ margin of safety "
                "ensures the asymmetric payoff central to the Dhandho framework."
            ),
        ))
        if mos is not None and mos < -0.30:
            red_flags.append(
                f"Trading {abs(mos)*100:.0f}% above intrinsic value — no margin of safety"
            )

        # ── Rule 7: Simple, Predictable Business — 10 pts ────────────────
        # "Buy simple businesses in industries with ultra-slow rates of change."
        # Revenue growth volatility as a proxy for business predictability.
        rev = data.revenue_series
        growth_stdev = None
        if len(rev) >= 3:
            yoy = []
            for i in range(1, len(rev)):
                if rev[i - 1] > 0:
                    yoy.append((rev[i] - rev[i - 1]) / rev[i - 1])
            if len(yoy) >= 2:
                growth_stdev = statistics.stdev(yoy) * 100
        r7 = self._make_rule(
            name="Simple & Predictable (revenue growth stdev < 15%)",
            value=growth_stdev,
            threshold=15.0,
            points_possible=10.0,
            description=(
                f"Revenue growth stdev = {growth_stdev:.1f}%"
                if growth_stdev is not None else "Insufficient revenue history"
            ),
            source="The Dhandho Investor, Ch.2 — Simple businesses, slow change",
            passed=growth_stdev < 15.0 if growth_stdev is not None else None,
            explanation=(
                "Pabrai only invests in simple businesses in industries with ultra-slow "
                "rates of change — this eliminates ~99% of alternatives. Low revenue growth "
                "volatility (stdev < 15%) signals a predictable, stable business where "
                "back-of-envelope valuation is reliable."
            ),
        )
        rules.append(r7)
        if growth_stdev is not None and growth_stdev > 30:
            red_flags.append(
                "Highly unpredictable revenue — Pabrai avoids businesses he can't model simply"
            )

        return self._build_result(rules, red_flags)

    # ──────────────────────────────────────────────────────────────────────
    def _simple_dcf(
        self, data: "FinancialData"
    ) -> tuple[float | None, str]:
        """
        Pabrai's back-of-envelope DCF: no spreadsheets.
        IV = (avg FCF × exit multiple) discounted at 10% over holding period.
        Plus excess cash on the balance sheet.
        Returns (margin_of_safety_fraction, description).
        """
        fcf = data.free_cash_flow_series
        shares = data.info.get("sharesOutstanding")
        current_price = (
            data.info.get("currentPrice") or data.info.get("regularMarketPrice")
        )
        cash = data.cash_and_equivalents
        total_debt = data.total_debt

        if not fcf or not shares or not current_price or shares == 0:
            return None, "DCF valuation unavailable"

        try:
            # Average of last 3-5 years of FCF
            recent_fcf = statistics.mean(fcf[-5:]) if len(fcf) >= 3 else fcf[-1]
            if recent_fcf <= 0:
                return None, "Negative average FCF — cannot value"

            # Terminal value at year 10 using exit multiple
            iv_total = recent_fcf * DCF_EXIT_MULTIPLE

            # Discount back to present at 10%
            iv_discounted = iv_total / (1 + DCF_DISCOUNT_RATE) ** 5

            # Add net cash (excess cash above debt)
            net_cash = max(0, (cash or 0) - (total_debt or 0))
            iv_discounted += net_cash

            iv_per_share = iv_discounted / shares
            mos = (iv_per_share - current_price) / iv_per_share

            return (
                mos,
                f"Simple IV = ${iv_per_share:.2f}, Price = ${current_price:.2f}, "
                f"MoS = {mos*100:.1f}%",
            )
        except Exception as e:
            logger.warning(f"Pabrai DCF failed: {e}")
            return None, "Calculation error"
