"""
Warren Buffett scoring module.

Rules based on:
- "The Warren Buffett Way" by Robert Hagstrom
- Berkshire Hathaway Annual Letters to Shareholders
- "Security Analysis" by Graham & Dodd (DCF methodology)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# Buffett's conservative DCF discount rate and growth assumptions
DCF_DISCOUNT_RATE = 0.09       # 9% — long-term Treasury + equity premium
DCF_TERMINAL_GROWTH = 0.03    # 3% — conservative perpetual growth
DCF_YEARS = 10


class BuffettInvestor(BaseInvestor):
    """
    Warren Buffett scoring: quality business at a fair price.
    Emphasis on ROIC, FCF consistency, low debt, and intrinsic value.
    """

    @property
    def name(self) -> str:
        return "Buffett"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: ROIC > 15% (10-year average) — 20 pts ─────────────────
        # "The single most important indicator of a wonderful business." — Hagstrom Ch.4
        roic_series = data.roic_series
        roic_avg = statistics.mean(roic_series) if roic_series else None
        r1 = self._make_rule(
            name="ROIC > 15% (10yr avg)",
            value=roic_avg * 100 if roic_avg is not None else None,
            threshold=15.0,
            points_possible=20.0,
            description=(
                f"10yr avg ROIC = {roic_avg*100:.1f}%" if roic_avg else "No ROIC data"
            ),
            source="The Warren Buffett Way, Hagstrom Ch.4",
            explanation="Return on Invested Capital (ROIC) shows how efficiently a business uses its capital to generate profits. A 10-year average above 15% confirms a durable competitive advantage — the business consistently earns well above its cost of capital.",
        )
        rules.append(r1)
        if not r1.passed and roic_avg is not None and roic_avg < 0.10:
            red_flags.append("ROIC below 10% — business earns poor returns on capital")

        # ── Rule 2: Debt/Equity < 0.5 — 15 pts ────────────────────────────
        # "We like businesses that can raise their prices easily, especially
        #  those that aren't burdened by heavy capital requirements." — Berkshire 1992
        de = data.debt_to_equity
        # yfinance sometimes returns D/E as a percentage (e.g., 150 = 1.5x)
        if de is not None and de > 10:
            de = de / 100
        r2 = self._make_rule(
            name="Debt/Equity < 0.5",
            value=de,
            threshold=0.5,
            points_possible=15.0,
            description=f"D/E = {de:.2f}" if de is not None else "D/E unavailable",
            source="Berkshire Hathaway Annual Letters",
            passed=de < 0.5 if de is not None else None,
            explanation="Debt-to-Equity compares total debt to shareholders' equity. A ratio below 0.5 means the company is funded primarily with equity, reducing financial fragility and the risk of distress during economic downturns.",
        )
        rules.append(r2)
        if not r2.passed and de is not None and de > 1.5:
            red_flags.append(f"High leverage (D/E={de:.1f}) — risk during downturns")

        # ── Rule 3: Owner Earnings Yield > 6% — 15 pts ────────────────────
        # Owner Earnings = Net Income + D&A - CapEx (Berkshire 1986 letter)
        # Yield = Owner Earnings / Market Cap
        market_cap = data.market_cap
        ocf = data.operating_cash_flow_series
        capex = data.capex_series
        owner_earnings_yield = None
        if ocf and capex and market_cap and market_cap > 0:
            # Use most recent year
            oe = ocf[-1] - capex[-1] if capex else ocf[-1]
            owner_earnings_yield = (oe / market_cap) * 100
        r3 = self._make_rule(
            name="Owner Earnings Yield > 6%",
            value=owner_earnings_yield,
            threshold=6.0,
            points_possible=15.0,
            description=(
                f"OE Yield = {owner_earnings_yield:.1f}%"
                if owner_earnings_yield is not None
                else "FCF/market cap unavailable"
            ),
            source="Berkshire Hathaway Letter 1986",
            explanation="Owner Earnings (Operating Cash Flow minus maintenance CapEx) represent the real cash a business generates for owners. Dividing by market cap gives an earnings yield — the higher the number, the more cash you receive annually relative to the price paid.",
        )
        rules.append(r3)
        if not r3.passed and owner_earnings_yield is not None and owner_earnings_yield < 2:
            red_flags.append("Owner earnings yield < 2% — paying a very high price")

        # ── Rule 4: FCF Margin Consistency (stdev < 5pp) — 15 pts ─────────
        # Consistent FCF margins signal a durable competitive advantage
        fcf_margins = data.fcf_margin_series
        fcf_stdev = None
        fcf_avg = None
        if len(fcf_margins) >= 3:
            fcf_stdev = statistics.stdev(fcf_margins) * 100
            fcf_avg = statistics.mean(fcf_margins) * 100
        r4 = self._make_rule(
            name="FCF Margin Consistency (stdev < 5%)",
            value=fcf_stdev,
            threshold=5.0,
            points_possible=15.0,
            description=(
                f"FCF margin stdev={fcf_stdev:.1f}%, avg={fcf_avg:.1f}%"
                if fcf_stdev is not None
                else "Insufficient FCF history"
            ),
            source="Berkshire Hathaway Annual Letters",
            passed=fcf_stdev < 5.0 if fcf_stdev is not None else None,
            explanation="Free Cash Flow margin consistency measures how stable the company's cash generation is relative to revenue. Low volatility (stdev < 5%) signals reliable, predictable earnings power — a hallmark of businesses with durable pricing power and competitive insulation.",
        )
        rules.append(r4)
        if not r4.passed and fcf_stdev is not None and fcf_stdev > 15:
            red_flags.append("Highly erratic FCF margins — business lacks pricing power")

        # ── Rule 5: Price < DCF Intrinsic Value — 20 pts ──────────────────
        # Conservative DCF using 10yr FCF average, 9% discount, 3% terminal growth
        iv_score, iv_margin, intrinsic_value = self._dcf_score(data)
        r5_value = iv_margin * 100 if iv_margin is not None else None
        r5 = self._make_rule(
            name="Price < Intrinsic Value (DCF)",
            value=r5_value,
            threshold=0.0,  # positive margin = price below IV
            points_possible=20.0,
            description=(
                f"Margin of safety = {iv_margin*100:.1f}% vs IV ${intrinsic_value:,.0f}"
                if iv_margin is not None and intrinsic_value is not None
                else "DCF valuation unavailable"
            ),
            source="Security Analysis, Graham & Dodd; Berkshire Letters",
            passed=iv_margin > 0 if iv_margin is not None else None,
            partial=min(1.0, max(0, iv_margin / 0.30)) if iv_margin is not None else 1.0,
            explanation="A Discounted Cash Flow (DCF) analysis estimates what future free cash flows are worth in today's dollars, discounted at 9% per year. A positive margin of safety means the stock trades below this intrinsic value estimate — you're paying less than the business is theoretically worth.",
        )
        if r5.passed and iv_margin is not None:
            # Partial credit: scale from 0 to 20 based on margin depth
            from src.backend.investors.base_investor import Rule as R
            pts = min(20.0, 20.0 * (iv_margin / 0.30)) if iv_margin > 0 else 0.0
            rules.append(R(
                name=r5.name,
                passed=r5.passed,
                value=r5.value,
                threshold=r5.threshold,
                points_awarded=pts,
                points_possible=r5.points_possible,
                description=r5.description,
                source=r5.source,
                explanation=r5.explanation,
            ))
        else:
            rules.append(r5)

        if not r5.passed and iv_margin is not None and iv_margin < -0.30:
            red_flags.append(
                f"Trading {abs(iv_margin)*100:.0f}% ABOVE intrinsic value — very expensive"
            )

        # ── Rule 6: Buybacks > Dilution — 10 pts ──────────────────────────
        # "The test of whether retained earnings are being used wisely is
        #  whether shares outstanding decline over time." — Berkshire 1984
        shares = data.shares_outstanding_series
        buyback_positive = None
        if len(shares) >= 3:
            # Negative trend in shares = buybacks winning
            buyback_positive = shares[-1] < shares[0]
        r6 = self._make_rule(
            name="Buybacks > Dilution (shares declining)",
            value=1.0 if buyback_positive else (0.0 if buyback_positive is not None else None),
            threshold=1.0,
            points_possible=10.0,
            description=(
                "Shares declining — management returning capital"
                if buyback_positive
                else (
                    "Shares increasing — diluting shareholders"
                    if buyback_positive is not None
                    else "Share count history unavailable"
                )
            ),
            source="Berkshire Hathaway Letter 1984",
            passed=buyback_positive,
            explanation="Declining share counts mean management is buying back stock, concentrating ownership and increasing per-share earnings. Rising share counts dilute existing shareholders, reducing value per share even if total profits grow.",
        )
        rules.append(r6)
        if buyback_positive is False:
            red_flags.append("Share count rising — management diluting existing shareholders")

        # ── Rule 7: Gross Margin > 40% and Consistent (stdev < 5pp) — 10 pts ─
        # High, stable gross margins signal durable pricing power — a hallmark
        # of Buffett's "wonderful businesses" (See's Candies, Coca-Cola, etc.)
        gm_series = data.gross_margin_series
        gm_avg = None
        gm_stdev = None
        if len(gm_series) >= 3:
            gm_avg = statistics.mean(gm_series) * 100
            gm_stdev = statistics.stdev(gm_series) * 100
        r7_gm_passed = (
            (gm_avg >= 40.0 and gm_stdev < 5.0)
            if (gm_avg is not None and gm_stdev is not None)
            else None
        )
        r7_gm = self._make_rule(
            name="Gross Margin > 40% and Consistent (stdev < 5%)",
            value=gm_avg,
            threshold=40.0,
            points_possible=10.0,
            description=(
                f"Gross margin avg={gm_avg:.1f}%, stdev={gm_stdev:.1f}%"
                if gm_avg is not None
                else "Insufficient gross margin history"
            ),
            source="Berkshire Hathaway Annual Letters; The Warren Buffett Way",
            passed=r7_gm_passed,
            explanation="High, stable gross margins (>40%) indicate the business has durable pricing power and a sustainable competitive moat — customers pay a premium consistently. Volatility above 5% suggests the advantage may be eroding or cyclical.",
        )
        rules.append(r7_gm)
        if not r7_gm_passed and gm_avg is not None and gm_avg < 20.0:
            red_flags.append(f"Gross margin {gm_avg:.1f}% — commodity-like business, no pricing power")

        # ── Rule 8: Low downside volatility (max drawdown penalty) — 5 pts ─
        # "Rule No. 1: Never lose money. Rule No. 2: Never forget rule No. 1."
        max_dd = data.max_drawdown
        dd_pct = abs(max_dd) * 100 if max_dd is not None else None
        r8 = self._make_rule(
            name="Low downside volatility (max drawdown < 40%)",
            value=dd_pct,
            threshold=40.0,
            points_possible=5.0,
            description=(
                f"Max 10yr drawdown = -{dd_pct:.1f}%"
                if dd_pct is not None
                else "Price history unavailable"
            ),
            source='"Rule #1: Never lose money" — Warren Buffett',
            passed=dd_pct < 40.0 if dd_pct is not None else None,
            explanation="Maximum drawdown measures the worst peak-to-trough price decline over 10 years. A drawdown below 40% suggests the stock has historically avoided catastrophic losses — consistent with Buffett's Rule #1: never lose money.",
        )
        rules.append(r8)
        if not r8.passed and dd_pct is not None and dd_pct > 60:
            red_flags.append(
                f"Stock lost {dd_pct:.0f}% at worst — high permanent capital loss risk"
            )

        return self._build_result(rules, red_flags)

    # ──────────────────────────────────────────────────────────────────────────
    def _dcf_score(
        self, data: "FinancialData"
    ) -> tuple[float, float | None, float | None]:
        """
        Conservative DCF: use average of last 5 FCF values, grow at historical
        FCF CAGR (capped at 10%), discount at 9%, terminal growth 3%.
        Returns (score_0_20, margin_of_safety_fraction, intrinsic_value_per_share).
        """
        fcf = data.free_cash_flow_series
        mc = data.market_cap
        shares = data.info.get("sharesOutstanding")

        if not fcf or not mc or not shares or shares == 0:
            return 0.0, None, None

        try:
            recent_fcf = statistics.mean(fcf[-5:]) if len(fcf) >= 5 else statistics.mean(fcf)
            if recent_fcf <= 0:
                return 0.0, None, None

            # Growth rate: historical FCF CAGR capped at 10%
            if len(fcf) >= 3 and fcf[0] > 0:
                n = len(fcf) - 1
                fcf_cagr = (fcf[-1] / fcf[0]) ** (1 / n) - 1
                growth = max(-0.05, min(0.10, fcf_cagr))
            else:
                growth = 0.04  # conservative default

            # 10-year DCF
            pv_fcfs = 0.0
            for year in range(1, DCF_YEARS + 1):
                projected = recent_fcf * (1 + growth) ** year
                pv_fcfs += projected / (1 + DCF_DISCOUNT_RATE) ** year

            # Terminal value (Gordon Growth)
            terminal_fcf = recent_fcf * (1 + growth) ** DCF_YEARS * (1 + DCF_TERMINAL_GROWTH)
            terminal_value = terminal_fcf / (DCF_DISCOUNT_RATE - DCF_TERMINAL_GROWTH)
            pv_terminal = terminal_value / (1 + DCF_DISCOUNT_RATE) ** DCF_YEARS

            intrinsic_total = pv_fcfs + pv_terminal
            intrinsic_per_share = intrinsic_total / shares

            current_price = data.info.get("currentPrice") or data.info.get("regularMarketPrice")
            if not current_price:
                return 0.0, None, intrinsic_per_share

            margin = (intrinsic_per_share - current_price) / intrinsic_per_share
            return 0.0, margin, intrinsic_per_share

        except Exception as e:
            logger.warning(f"DCF calculation failed: {e}")
            return 0.0, None, None
