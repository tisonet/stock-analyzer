"""
Seth Klarman scoring module.

Rules based on:
- "Margin of Safety" by Seth Klarman (1991)
- Baupost Group Letters to Shareholders
- "The Superinvestors of Graham-and-Doddsville" tradition
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class KlarmanInvestor(BaseInvestor):
    """
    Seth Klarman scoring: extreme margin of safety, liquidation value, downside first.
    "The stock market is not always right." — Klarman penalises momentum-driven valuation.
    """

    @property
    def name(self) -> str:
        return "Klarman"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: Margin of Safety ≥ 50% — 30 pts ───────────────────────
        # "The single most important concept in value investing." — Margin of Safety, Ch.1
        # Use FCF-based intrinsic value vs current price
        mos, mos_desc, iv = self._margin_of_safety(data)
        mos_pts = 0.0
        if mos is not None and mos >= 0.50:
            mos_pts = 30.0
        elif mos is not None and mos > 0:
            mos_pts = 30.0 * (mos / 0.50)  # partial credit
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Margin of Safety ≥ 50% (vs intrinsic value)",
            passed=mos is not None and mos >= 0.50,
            value=mos * 100 if mos is not None else None,
            threshold=50.0,
            points_awarded=mos_pts,
            points_possible=30.0,
            description=mos_desc,
            source="Margin of Safety, Klarman Ch.1 — The margin of safety concept",
            explanation="Klarman's core concept: the gap between purchase price and intrinsic value is your cushion against being wrong. Unlike Buffett's 30% bar, Klarman demands 50% — he only buys when the stock is at half price or less versus a conservative DCF estimate, ensuring extreme protection against forecasting errors.",
        ))
        if mos is not None and mos < 0:
            red_flags.append(
                f"Trading {abs(mos)*100:.0f}% ABOVE estimated intrinsic value — Klarman would not buy"
            )

        # ── Rule 2: Net Current Asset Value analysis — 15 pts ──────────────
        # NCAV = Current Assets - Total Liabilities
        # If market cap < 1.5x NCAV → classic Graham net-net (Klarman also uses this)
        ca = data.current_assets
        total_liab = data.total_liabilities
        mc = data.market_cap
        ncav = None
        ncav_ratio = None
        if ca is not None and total_liab is not None:
            ncav = ca - total_liab
        if ncav is not None and mc and mc > 0:
            ncav_ratio = mc / ncav if ncav > 0 else None
        ncav_pass = ncav_ratio is not None and ncav_ratio < 1.5
        r2_value = ncav_ratio
        r2 = self._make_rule(
            name="Market Cap < 1.5× NCAV (net-net territory)",
            value=r2_value,
            threshold=1.5,
            points_possible=15.0,
            description=(
                f"NCAV = ${ncav/1e9:.2f}B, Market Cap/NCAV = {ncav_ratio:.2f}x"
                if ncav_ratio is not None
                else (
                    "NCAV negative (liabilities > current assets)"
                    if ncav is not None and ncav <= 0
                    else "Balance sheet data unavailable"
                )
            ),
            source="Margin of Safety, Klarman — Net asset value analysis",
            passed=ncav_pass,
            explanation="Net Current Asset Value (NCAV) = Current Assets minus All Liabilities. If market cap is less than 1.5× NCAV, you are buying the liquid assets at a discount even before assigning any value to the ongoing business — Graham's famous 'net-net' screen that Klarman also employs.",
        )
        rules.append(r2)

        # ── Rule 3: Liquidation value protection — 25 pts ──────────────────
        # Liquidation value = Cash + 0.75×Receivables + 0.5×Inventory - Total Liabilities
        liq_value, liq_ratio, liq_desc = self._liquidation_value(data)
        liq_pts = 0.0
        if liq_ratio is not None:
            if liq_ratio >= 1.0:
                liq_pts = 25.0
            elif liq_ratio >= 0.5:
                liq_pts = 25.0 * liq_ratio
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Liquidation value > market cap",
            passed=liq_ratio is not None and liq_ratio >= 1.0,
            value=liq_ratio * 100 if liq_ratio is not None else None,
            threshold=100.0,
            points_awarded=liq_pts,
            points_possible=25.0,
            description=liq_desc,
            source="Margin of Safety, Klarman — Asset-based valuation",
            explanation="Liquidation value estimates what investors would recover if the business were wound down: cash at full value, receivables at 75¢, inventory at 50¢, minus all liabilities. Buying below liquidation value means you pay less than physical asset value — the ultimate downside protection floor.",
        ))
        if liq_ratio is not None and liq_ratio < 0.20:
            red_flags.append(
                "Liquidation value << market cap — almost no asset protection if business fails"
            )

        # ── Rule 4: Downside protection score — 20 pts ─────────────────────
        # Klarman: "Focus on not losing money first; profits take care of themselves."
        dd = data.max_drawdown
        dd_pct = abs(dd) * 100 if dd is not None else None
        # Lower drawdown = better protection
        if dd_pct is not None:
            dd_score = max(0.0, 1.0 - (dd_pct - 20) / 60) if dd_pct > 20 else 1.0
        else:
            dd_score = None
        dd_pts = 20.0 * dd_score if dd_score is not None else 0.0
        from src.backend.investors.base_investor import Rule as R
        rules.append(R(
            name="Downside protection (max drawdown < 30%)",
            passed=dd_pct is not None and dd_pct < 30,
            value=dd_pct,
            threshold=30.0,
            points_awarded=dd_pts,
            points_possible=20.0,
            description=(
                f"Max 10yr drawdown = -{dd_pct:.1f}%"
                if dd_pct is not None
                else "Price history unavailable"
            ),
            source="Margin of Safety, Klarman — Capital preservation",
            explanation="Klarman's capital preservation philosophy: never lose money before thinking about gains. The 10-year maximum drawdown measures the worst historical price decline. Stocks with drawdowns below 30% have demonstrated resilience that Klarman requires before evaluating upside potential.",
        ))
        if dd_pct is not None and dd_pct > 60:
            red_flags.append(
                f"Lost {dd_pct:.0f}% at worst — insufficient downside protection for Klarman"
            )

        # ── Rule 5: Momentum penalty — 10 pts ──────────────────────────────
        # "The stock market is not always right. Avoid momentum-driven stocks."
        # Penalise if 12m return > 50% (likely momentum, not value)
        ret_12m = data.price_return_12m
        momentum_driven = ret_12m is not None and ret_12m > 0.50
        r5 = self._make_rule(
            name="Not momentum-driven (12m return < 50%)",
            value=ret_12m * 100 if ret_12m is not None else None,
            threshold=50.0,
            points_possible=10.0,
            description=(
                f"12m return = {ret_12m*100:.1f}% — "
                f"{'momentum-driven, Klarman avoids' if momentum_driven else 'within acceptable range'}"
                if ret_12m is not None
                else "12m return unavailable"
            ),
            source="Margin of Safety, Klarman — Against momentum investing",
            passed=not momentum_driven if ret_12m is not None else None,
            explanation="Stocks up 50%+ in 12 months are typically driven by momentum rather than fundamental value. Klarman explicitly avoids these: the market has already priced in good news, dramatically shrinking the margin of safety. He waits for value to emerge, not chase recent winners.",
        )
        rules.append(r5)
        if momentum_driven:
            red_flags.append(
                f"12m return of {ret_12m*100:.0f}% — market has likely priced in all good news"
            )

        return self._build_result(rules, red_flags)

    # ──────────────────────────────────────────────────────────────────────────

    def _margin_of_safety(
        self, data: "FinancialData"
    ) -> tuple[float | None, str, float | None]:
        """
        Conservative DCF-based MoS using average FCF, 10% discount rate, 2% terminal growth.
        Klarman uses higher discount rates than Buffett for extra safety.
        """
        fcf = data.free_cash_flow_series
        mc = data.market_cap
        shares = data.info.get("sharesOutstanding")
        current_price = data.info.get("currentPrice") or data.info.get("regularMarketPrice")

        if not fcf or not mc or not shares or not current_price:
            return None, "Intrinsic value calculation unavailable", None

        try:
            recent_fcf = sum(fcf[-3:]) / min(3, len(fcf[-3:]))
            if recent_fcf <= 0:
                return None, "Negative FCF — no intrinsic value to compute", None

            discount = 0.10
            terminal_growth = 0.02
            growth = min(0.07, max(0.0, (fcf[-1] / fcf[0]) ** (1 / max(len(fcf) - 1, 1)) - 1)) if len(fcf) > 1 and fcf[0] > 0 else 0.03

            pv = sum(
                recent_fcf * (1 + growth) ** yr / (1 + discount) ** yr
                for yr in range(1, 11)
            )
            terminal = (recent_fcf * (1 + growth) ** 10 * (1 + terminal_growth)) / (
                discount - terminal_growth
            )
            pv_terminal = terminal / (1 + discount) ** 10
            iv_total = pv + pv_terminal
            iv_per_share = iv_total / shares

            mos = (iv_per_share - current_price) / iv_per_share
            return (
                mos,
                f"IV = ${iv_per_share:.2f}, Price = ${current_price:.2f}, MoS = {mos*100:.1f}%",
                iv_per_share,
            )
        except Exception as e:
            logger.warning(f"Klarman MoS calculation failed: {e}")
            return None, "Calculation error", None

    def _liquidation_value(
        self, data: "FinancialData"
    ) -> tuple[float | None, float | None, str]:
        """
        Liquidation value = Cash + 0.75×Receivables + 0.5×Inventory - Total Liabilities
        Returns (liquidation_value, liq/market_cap ratio, description).
        """
        cash = data.cash_and_equivalents
        receivables = data.receivables
        inventory = data.inventory
        total_liab = data.total_liabilities
        mc = data.market_cap

        if cash is None and receivables is None:
            return None, None, "Asset data unavailable"

        liq = (cash or 0) + 0.75 * (receivables or 0) + 0.5 * (inventory or 0) - (total_liab or 0)
        liq_ratio = liq / mc if mc and mc > 0 else None

        desc = (
            f"Liquidation value = ${liq/1e9:.2f}B "
            f"(cash=${(cash or 0)/1e9:.2f}B, "
            f"recv=${(receivables or 0)/1e9:.2f}B×0.75, "
            f"inv=${(inventory or 0)/1e9:.2f}B×0.5, "
            f"liab=-${(total_liab or 0)/1e9:.2f}B)"
        )
        if liq_ratio is not None:
            desc += f" = {liq_ratio*100:.0f}% of market cap"

        return liq, liq_ratio, desc
