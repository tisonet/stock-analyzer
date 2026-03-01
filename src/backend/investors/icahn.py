"""
Carl Icahn scoring module.

Rules based on:
- Icahn's public 13D filings and activist campaigns (1980s–present)
- CNBC interviews and public shareholder letters
- "King Icahn" by Mark Stevens (1993)
- Icahn Enterprises LP annual reports

Icahn's core activist thesis:
  1. Find undervalued companies (cheap assets, strong FCF generation)
  2. Identify governance failures (low insider ownership, entrenched management)
  3. Force the catalyst (buybacks, spin-offs, asset sales, CEO replacement)

Key distinction from other investors: Icahn doesn't need a *great* business —
he needs a *fixable* one. Low ROE is an opportunity, not a warning sign.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class IcahnInvestor(BaseInvestor):
    """
    Carl Icahn scoring: find undervalued, mismanaged companies and force change.
    Emphasis on asset discount, FCF generation, clean balance sheet, and
    governance gaps that make an activist campaign viable.
    """

    @property
    def name(self) -> str:
        return "Icahn"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # Compute FCF once — used in Rules 2 and 6
        fcf_series = data.free_cash_flow_series
        market_cap = data.market_cap
        fcf_latest = fcf_series[-1] if fcf_series else None
        fcf_positive = fcf_latest is not None and fcf_latest > 0

        # ── Rule 1: Asset Discount — P/B < 1.5 — 20 pts ──────────────────
        # Icahn targets companies trading at or below book value. He needs to
        # buy assets cheaply to make the activist thesis work even if the
        # campaign takes years. P/B below 1.5 is his stated entry zone.
        # "I look for good assets at a cheap price." — Carl Icahn, CNBC 2013
        pb = self._safe(data.info.get("priceToBook"))
        r1 = self._make_rule(
            name="Asset Discount (P/B < 1.5)",
            value=pb,
            threshold=1.5,
            points_possible=20.0,
            description=(
                f"P/B = {pb:.2f}x — assets available at a discount to book value"
                if pb is not None else "P/B ratio unavailable"
            ),
            source="Icahn 13D filings — 'I look for good assets at a cheap price'",
            passed=pb < 1.5 if pb is not None else None,
            explanation="Price-to-Book ratio compares market cap to net asset value. Below 1.5x means buying the company's assets for less than their stated book value — providing Icahn a floor value even if his activist campaign fails to unlock value. He needs this discount to justify the campaign risk.",
        )
        rules.append(r1)
        if not r1.passed and pb is not None and pb > 3.0:
            red_flags.append(
                f"P/B of {pb:.1f}x is far too expensive for an activist play — "
                f"Icahn needs to buy assets cheaply to make the thesis work"
            )

        # ── Rule 2: FCF Yield > 5% — Buyback Ammunition — 20 pts ─────────
        # Strong FCF proves the underlying business generates real cash.
        # Once Icahn gains board influence, that cash can be returned to
        # shareholders via buybacks or special dividends.
        # "When you have no debt and you're buying back stock at a cheap price,
        #  you're doing something very intelligent." — Carl Icahn
        fcf_yield = None
        if fcf_latest is not None and fcf_positive and market_cap and market_cap > 0:
            fcf_yield = (fcf_latest / market_cap) * 100

        r2 = self._make_rule(
            name="FCF Yield > 5% (buyback ammunition)",
            value=fcf_yield,
            threshold=5.0,
            points_possible=20.0,
            description=(
                f"FCF yield = {fcf_yield:.1f}% — strong cash generation for shareholder returns"
                if fcf_yield is not None else "FCF yield unavailable"
            ),
            source="Icahn CNBC interviews — FCF is the fuel for buybacks and special dividends",
            explanation="Free Cash Flow Yield above 5% proves the underlying business generates real cash. Once Icahn gains board influence, this cash becomes his 'ammunition' for forcing buybacks, special dividends, or debt reduction — returning value to shareholders that undisciplined management was hoarding or wasting.",
        )
        rules.append(r2)
        if not r2.passed and fcf_latest is not None and fcf_latest < 0:
            red_flags.append(
                "Negative FCF — a cash-burning business offers no ammunition for "
                "the buybacks or dividends Icahn would demand from the board"
            )

        # ── Rule 3: Low Leverage (D/E < 1.0) — Balance Sheet Firepower — 15 pts
        # An under-leveraged company has room to lever up and return capital.
        # Icahn explicitly looks for companies with no excuse not to buy back
        # their own stock. High existing debt forecloses that option.
        # Note: yfinance returns debtToEquity as a percentage (82 = 0.82x D/E)
        de_raw = self._safe(data.info.get("debtToEquity"))
        de_ratio = de_raw / 100.0 if de_raw is not None else None
        r3 = self._make_rule(
            name="Low Leverage (D/E < 1.0) — balance sheet firepower",
            value=de_ratio,
            threshold=1.0,
            points_possible=15.0,
            description=(
                f"D/E = {de_ratio:.2f}x — "
                f"{'clean balance sheet with room to return capital' if de_ratio < 1.0 else 'leveraged, limits activist options'}"
                if de_ratio is not None else "Debt/equity ratio unavailable"
            ),
            source="Icahn — 'no excuse not to buy back stock' when balance sheet is clean",
            passed=de_ratio < 1.0 if de_ratio is not None else None,
            explanation="A clean balance sheet with D/E below 1.0 removes management's best excuse for not returning capital. Icahn explicitly looks for companies with 'no excuse not to buy back stock.' High existing debt forecloses this option, weakening his leverage over the board.",
        )
        rules.append(r3)
        if not r3.passed and de_ratio is not None and de_ratio > 2.0:
            red_flags.append(
                f"D/E of {de_ratio:.1f}x — over-leveraged, no balance sheet room "
                f"for the buybacks or special dividends Icahn would force"
            )

        # ── Rule 4: Governance Gap — Insider Ownership < 10% — 15 pts ────
        # Low insider ownership signals management is not eating their own cooking.
        # For Icahn this is an OPPORTUNITY — the CEO isn't aligned with shareholders,
        # a proxy fight is winnable, and board pressure will be effective.
        # "The CEO who doesn't own a lot of stock in his own company —
        #  I always wonder about that guy." — Carl Icahn
        insider_pct = self._safe(data.info.get("heldPercentInsiders"))  # 0.0–1.0
        r4 = self._make_rule(
            name="Governance Gap (Insiders < 10%)",
            value=insider_pct * 100 if insider_pct is not None else None,
            threshold=10.0,
            points_possible=15.0,
            description=(
                f"Insider ownership = {insider_pct * 100:.1f}% — "
                f"{'management not aligned with shareholders (activist opportunity)' if insider_pct < 0.10 else 'management well-aligned, hard to dislodge'}"
                if insider_pct is not None else "Insider ownership data unavailable"
            ),
            source="Icahn — low insider ownership = governance gap = winnable proxy fight",
            passed=insider_pct < 0.10 if insider_pct is not None else None,
            explanation="Low insider ownership (below 10%) means management's personal wealth is not tied to the stock price. For Icahn this is an opportunity — management won't vote against him using their own money, making a proxy fight more winnable and governance change more achievable.",
        )
        rules.append(r4)
        if not r4.passed and insider_pct is not None and insider_pct > 0.30:
            red_flags.append(
                f"Insider ownership of {insider_pct * 100:.0f}% — management controls "
                f"enough votes to block any activist campaign; not a viable target"
            )

        # ── Rule 5: Cheap Enterprise Value (EV/EBITDA < 8x) — 15 pts ─────
        # Icahn's stated sweet spot is EV/EBITDA of 6–8x. This ensures he's
        # buying the whole enterprise cheaply — critical when he pushes for an
        # outright sale, since strategic acquirers won't pay more than ~8–10x.
        ev_ebitda = self._safe(data.info.get("enterpriseToEbitda"))
        r5 = self._make_rule(
            name="Cheap Enterprise Value (EV/EBITDA < 8x)",
            value=ev_ebitda,
            threshold=8.0,
            points_possible=15.0,
            description=(
                f"EV/EBITDA = {ev_ebitda:.1f}x — "
                f"{'attractive entry for a potential sale or break-up' if ev_ebitda is not None and 0 < ev_ebitda < 8 else 'too expensive for activist returns'}"
                if ev_ebitda is not None else "EV/EBITDA unavailable"
            ),
            source="Icahn — prefers EV/EBITDA 6–8x; acquirers will not overpay beyond that",
            passed=(ev_ebitda is not None and 0 < ev_ebitda < 8.0),
            explanation="Enterprise Value / EBITDA measures the total cost to acquire the business (market cap + debt - cash) divided by operating earnings. Icahn targets below 8x — the range where strategic acquirers can still pay a meaningful takeover premium and generate returns, making a sale or break-up viable.",
        )
        rules.append(r5)
        if not r5.passed and ev_ebitda is not None and ev_ebitda > 15.0:
            red_flags.append(
                f"EV/EBITDA of {ev_ebitda:.1f}x — too expensive for an activist buyer "
                f"to extract returns via sale or break-up at this valuation"
            )

        # ── Rule 6: ROE Underperformance (0% < ROE < 15%) — Fixable — 15 pts
        # Icahn seeks companies with positive but mediocre ROE — proof that the
        # underlying business is viable but management is leaving returns on the table.
        # A loss-making business is a value trap; an excellent one has no governance
        # gap to exploit. The sweet spot is a profitable but under-managed company.
        # "I look for companies that have good assets but are badly managed.
        #  The combination of the two is very powerful." — Carl Icahn
        roe = self._safe(data.info.get("returnOnEquity"))  # decimal: 0.08 = 8%
        roe_opportunity = (
            roe is not None and 0 < roe < 0.15 and fcf_positive
        )
        r6 = self._make_rule(
            name="ROE Underperformance (0–15%) — management fixable",
            value=roe * 100 if roe is not None else None,
            threshold=15.0,
            points_possible=15.0,
            description=(
                f"ROE = {roe * 100:.1f}% — "
                f"{'positive but below potential; management improvement opportunity' if roe_opportunity else 'ROE outside activist sweet spot (loss-making or already excellent)'}"
                if roe is not None else "ROE unavailable"
            ),
            source="Icahn — 'good assets, badly managed' is the activist formula",
            passed=roe_opportunity,
            explanation="Icahn's activist sweet spot: positive but mediocre Return on Equity. Loss-making companies are value traps; already-excellent ones have no governance gap to exploit. ROE of 0-15% is evidence that management is leaving returns on the table — the exact problem an activist campaign is designed to fix.",
        )
        rules.append(r6)
        if roe is not None and roe < 0:
            red_flags.append(
                f"Negative ROE of {roe * 100:.1f}% — the business is destroying equity "
                f"value; this is a distressed situation, not a governance fix"
            )

        return self._build_result(rules, red_flags)
