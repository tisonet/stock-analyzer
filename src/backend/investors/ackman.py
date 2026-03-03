"""
Bill Ackman — Pershing Square Capital Management scoring module.

Ackman is the founder of Pershing Square Capital Management (est. 2004).
Style: Concentrated activist value investor — 8-12 positions, ~75% in top 6.
Track record: ~16.5% annualised return since inception vs S&P 500 ~10.2%.
Current holdings (Q4 2024): Brookfield Corp, Uber, Amazon, Alphabet, Meta,
Chipotle, Hilton, Restaurant Brands, Howard Hughes Holdings, Nike.

After the Valeant and Herbalife losses (2015-2016) Ackman codified his
investment criteria into 8 commandments, literally engraved on stone tablets
placed on every desk at Pershing Square.

    "When we have veered from these eight principles, we have lost money.
     In each case where we compromised on business quality or complexity,
     we have been harmed."

The 8 Commandments:
  1. Simple and Predictable Business
  2. Free Cash Flow Generative
  3. Dominant Market Position
  4. Large Barriers to Entry (Moat)
  5. High Return on Capital
  6. Limited Extrinsic Risk Exposure
  7. Strong Balance Sheet / No Capital Dependency
  8. Excellent Management and Good Governance

Each commandment is scored 0–10, weighted to produce a 0–100 composite.
Bonus / penalty adjustments (up to ±13 pts) are applied for Ackman's
documented hard triggers: the ideal trifecta, negative FCF, excessive debt,
chronic dilution, value destruction (ROIC < WACC), and the contrarian signal.

Sources:
  - Pershing Square Capital Management annual letters
  - Ackman interviews: Acquire magazine, MOI Global, YIS
  - "Stone tablet principles" codified 2016 after Valeant/Herbalife losses
  - Pershing Square 13-F filings (Q4 2024)
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)

# ── Sector risk (0–10, higher = less extrinsic risk / more predictable) ───────
SECTOR_RISK_MAP: dict[str, int] = {
    "Technology": 7,
    "Communication Services": 7,
    "Consumer Cyclical": 8,       # Ackman sweet spot (Chipotle, Hilton)
    "Consumer Defensive": 9,
    "Healthcare": 5,              # Valeant lesson
    "Financial Services": 4,
    "Industrials": 6,
    "Real Estate": 6,
    "Basic Materials": 3,
    "Energy": 3,
    "Utilities": 5,
}

# ── Industry commodity / input cost sensitivity (0–10, higher = less sensitive)
COMMODITY_SENSITIVITY_MAP: dict[str, int] = {
    "Software—Infrastructure": 10,
    "Software—Application": 10,
    "Internet Content & Information": 9,
    "Restaurants": 6,
    "Lodging": 7,
    "Specialty Retail": 7,
    "Home Improvement Retail": 6,
    "Aerospace & Defense": 5,
    "Auto Manufacturers": 4,
    "Oil & Gas E&P": 2,
    "Oil & Gas Integrated": 2,
    "Airlines": 2,
    "Gold": 1,
    "Other Industrial Metals & Mining": 1,
}
_DEFAULT_COMMODITY_SCORE = 5

# ── Sector business-simplicity proxy (single-segment → 10) ────────────────────
SECTOR_SIMPLICITY_MAP: dict[str, int] = {
    "Consumer Defensive": 10,
    "Consumer Cyclical": 9,
    "Real Estate": 8,
    "Utilities": 7,
    "Industrials": 7,
    "Communication Services": 7,
    "Technology": 6,
    "Healthcare": 5,
    "Financial Services": 4,
    "Energy": 3,
    "Basic Materials": 3,
}


class AckmanInvestor(BaseInvestor):
    """
    Bill Ackman / Pershing Square Capital Management scoring.

    Implements the 8 Commandments framework with proportional pillar scoring:
    each commandment is scored 0–10 and contributes weighted points to the
    0–100 composite. Bonus / penalty adjustments are applied last.
    """

    # Commandment weights — must sum to 100
    _PILLAR_WEIGHTS: dict[str, int] = {
        "simple":    10,
        "fcf":       18,
        "dominant":  12,
        "moat":      14,
        "roc":       16,
        "extrinsic":  8,
        "balance":   12,
        "mgmt":      10,
    }

    @property
    def name(self) -> str:
        return "Ackman"

    # ──────────────────────────────────────────────────── public entry point ──

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Run all 8 commandment pillars ────────────────────────────────────
        p1_score, p1_desc = self._pillar_simple(data)
        p2_score, p2_desc = self._pillar_fcf(data)
        p3_score, p3_desc = self._pillar_dominant(data)
        p4_score, p4_desc = self._pillar_moat(data)
        p5_score, p5_desc = self._pillar_roc(data)
        p6_score, p6_desc = self._pillar_extrinsic(data)
        p7_score, p7_desc = self._pillar_balance(data)
        p8_score, p8_desc = self._pillar_mgmt(data)

        rules.extend([
            self._pillar_rule(
                "1. Simple & Predictable Business", p1_score, "simple", p1_desc,
                "Ackman: 'If we can't predict the cash flows, we don't know what it's worth.'",
                "Revenue and earnings Coefficient of Variation (lower = more predictable), "
                "FCF consistency (% of years positive), and sector simplicity. Predictable "
                "businesses allow the high-conviction, concentrated modelling that is the "
                "foundation of Ackman's approach.",
            ),
            self._pillar_rule(
                "2. Free Cash Flow Generation", p2_score, "fcf", p2_desc,
                "Ackman: 'Fundamentally, what you're looking for is how much cash the business "
                "can generate on a recurring basis over a very long period of time.'",
                "FCF margin TTM, 5-year FCF CAGR, FCF yield (FCF/EV), FCF quality (FCF/NI), "
                "and cumulative FCF vs CapEx. Ackman weights FCF highest — it is the only metric "
                "that cannot be manipulated by accounting choices.",
            ),
            self._pillar_rule(
                "3. Dominant Market Position", p3_score, "dominant", p3_desc,
                "Ackman: Companies 'where competitors have a significant barrier to entry and "
                "which operate in domains where it would be tough for another company to compete.'",
                "Company scale (market cap), gross margin level (pricing power proxy), revenue "
                "growth rate, and operating margin stability across cycles. Dominant businesses "
                "defend margins through downturns — the hallmark of structural advantage.",
            ),
            self._pillar_rule(
                "4. Barriers to Entry / Economic Moat", p4_score, "moat", p4_desc,
                "Ackman: 'Companies where it would be tough for another company to put them out "
                "of business.' Stone tablet: 'Large barriers to entry.'",
                "Gross margin level and multi-year trend (pricing power), R&D + CapEx investment "
                "intensity (barrier spending), and SG&A efficiency trend (operating leverage). "
                "These proxy the four classic moat sources: intangibles, switching costs, "
                "network effects, and cost advantage.",
            ),
            self._pillar_rule(
                "5. High Return on Capital", p5_score, "roc", p5_desc,
                "Ackman: 'The company must be good at making money on the capital invested.'",
                "ROIC TTM and 5-year average, ROIC consistency (std dev), ROE, and ROIC trend. "
                "High sustained ROIC is the financial proof of a moat — it demonstrates the "
                "business earns materially above its cost of capital on incremental investments.",
            ),
            self._pillar_rule(
                "6. Limited Extrinsic Risk", p6_score, "extrinsic", p6_desc,
                "Ackman: 'Limited exposure to extrinsic risk we can't control.' "
                "Stone tablet commandment learned from Valeant.",
                "Sector macro-predictability, market beta, geographic concentration (domestic "
                "focus), and commodity / input cost sensitivity. Ackman avoids businesses where "
                "external factors — regulatory, commodity, geopolitical — can overwhelm quality.",
            ),
            self._pillar_rule(
                "7. Strong Balance Sheet / Capital Independence", p7_score, "balance", p7_desc,
                "Ackman rule of thumb: debt payable from FCF in under 3 years. "
                "'We don't want a company that has to constantly raise money.'",
                "Debt/FCF ratio, Net Debt/EBITDA, interest coverage, current ratio, and 5-year "
                "share dilution. A robust balance sheet allows survival through downturns, "
                "strategy execution, and capital return without diluting shareholders.",
            ),
            self._pillar_rule(
                "8. Excellent Management & Governance", p8_score, "mgmt", p8_desc,
                "Ackman: 'The company must be run by management that you trust.' "
                "'Our job is to make sure management is doing the right thing.'",
                "Insider ownership (skin in the game), institutional sponsorship, buyback track "
                "record, dividend payout sustainability, and revenue-per-employee growth. These "
                "quantify management alignment with shareholders and capital allocation quality.",
            ),
        ])

        # ── Bonus / penalty adjustments ──────────────────────────────────────
        fcf_s  = data.free_cash_flow_series
        rev_s  = data.revenue_series
        roic_s = data.roic_series

        fcf_ttm  = fcf_s[-1]  if fcf_s  else None
        rev_ttm  = rev_s[-1]  if rev_s  else None
        roic_ttm = roic_s[-1] if roic_s else None

        fcf_margin_ttm = (
            fcf_ttm / rev_ttm
            if fcf_ttm is not None and rev_ttm and rev_ttm > 0
            else None
        )
        roic_avg = statistics.mean(roic_s) if roic_s else None

        # Debt/FCF for bonus check
        ltd     = data.total_debt
        fcf5    = fcf_s[-5:] if len(fcf_s) >= 5 else fcf_s
        avg_fcf = statistics.mean(fcf5) if fcf5 else None
        debt_fcf = (
            ltd / avg_fcf
            if ltd is not None and avg_fcf is not None and avg_fcf > 0
            else None
        )

        bonus = 0.0

        # +5: Ackman trifecta — the ideal business in one line
        if (
            fcf_margin_ttm is not None and fcf_margin_ttm > 0.20
            and roic_ttm is not None and roic_ttm > 0.20
            and debt_fcf is not None and debt_fcf < 2.0
        ):
            bonus += 5.0
            red_flags.append(
                "BONUS +5: Ackman trifecta — FCF margin >20%, ROIC >20%, and Debt/FCF <2× "
                "simultaneously; 'this is the kind of business we want to own forever'"
            )

        # -10: Negative TTM FCF — hard disqualifier
        if fcf_ttm is not None and fcf_ttm < 0:
            bonus -= 10.0
            red_flags.append(
                f"PENALTY -10: Negative TTM free cash flow (${fcf_ttm / 1e9:.1f}B) — "
                "Ackman's most important criterion; a business that consumes cash cannot be "
                "valued by DCF and cannot return capital to shareholders"
            )

        # -8: Debt excess — violates capital independence
        if debt_fcf is not None and debt_fcf > 5.0:
            bonus -= 8.0
            red_flags.append(
                f"PENALTY -8: Debt/FCF of {debt_fcf:.1f}× — would take 5+ years of FCF to "
                "retire total debt; violates the '3-year payback' capital independence rule"
            )

        # -5: Chronic dilution — destroys per-share value
        shares_s = data.shares_outstanding_series
        if len(shares_s) >= 2:
            ref = shares_s[-5] if len(shares_s) >= 5 else shares_s[0]
            if ref > 0:
                shares_chg_5yr = (shares_s[-1] / ref) - 1
                if shares_chg_5yr > 0.10:
                    bonus -= 5.0
                    red_flags.append(
                        f"PENALTY -5: Share count grew {shares_chg_5yr * 100:.1f}% over 5 years — "
                        "chronic dilution destroys per-share intrinsic value and indicates "
                        "management that does not prioritise shareholder returns"
                    )

        # -5: Value destroyer — ROIC below estimated cost of capital
        if roic_avg is not None and roic_avg < 0.08:
            bonus -= 5.0
            red_flags.append(
                f"PENALTY -5: ROIC avg {roic_avg * 100:.1f}% — below estimated cost of "
                "capital (~8%); incremental investment is destroying shareholder value "
                "on a risk-adjusted basis"
            )

        # +3: Contrarian signal — dislocated high-quality business
        ret_12m = data.price_return_12m
        if ret_12m is not None and ret_12m < -0.30:
            bonus += 3.0
            red_flags.append(
                f"BONUS +3: Contrarian signal — stock down {abs(ret_12m) * 100:.1f}% over "
                "12 months; Ackman actively targets quality businesses dislocated by "
                "temporary events for activist re-rating"
            )

        # Valuation overlay (informational, separate from commandments)
        val_flag = self._valuation_flag(data)
        if val_flag:
            red_flags.append(val_flag)

        # ── Build final InvestorScore ─────────────────────────────────────────
        pillar_total = sum(r.points_awarded for r in rules)
        total_score  = max(0.0, min(100.0, pillar_total + bonus))

        passed = [r for r in rules if r.passed]
        failed = [r for r in rules if not r.passed]

        return InvestorScore(
            investor=self.name,
            total_score=total_score,
            verdict=self._verdict(total_score),
            rules_passed=passed,
            rules_failed=failed,
            key_insight="",  # filled by engine after Claude call
            red_flags=red_flags,
        )

    # ─────────────────────────────────────────────────── pillar methods ───────

    def _pillar_simple(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 1: Simple, predictable, understandable business."""
        rev = data.revenue_series[-5:]           if len(data.revenue_series)           >= 5 else data.revenue_series
        op  = data.operating_income_series[-5:]  if len(data.operating_income_series)  >= 5 else data.operating_income_series
        fcf = data.free_cash_flow_series[-5:]    if len(data.free_cash_flow_series)    >= 5 else data.free_cash_flow_series

        # SP-1: Revenue coefficient of variation (lower = more predictable)
        rev_cov = self._cov(rev)
        if   rev_cov is None:   sp1 = 5.0
        elif rev_cov < 0.10:    sp1 = 10.0
        elif rev_cov < 0.20:    sp1 = 7.0
        elif rev_cov < 0.35:    sp1 = 4.0
        else:                   sp1 = 1.0

        # SP-2: Operating income coefficient of variation
        op_cov = self._cov(op)
        if   op_cov is None:    sp2 = 5.0
        elif op_cov < 0.15:     sp2 = 10.0
        elif op_cov < 0.25:     sp2 = 7.0
        elif op_cov < 0.40:     sp2 = 4.0
        else:                   sp2 = 1.0

        # SP-3: FCF consistency — % of last 5 years with positive FCF
        pct_pos: Optional[float] = None
        if fcf:
            pct_pos = sum(1 for f in fcf if f > 0) / len(fcf)
            if   pct_pos == 1.0:  sp3 = 10.0
            elif pct_pos >= 0.8:  sp3 = 7.0
            elif pct_pos >= 0.6:  sp3 = 4.0
            else:                 sp3 = 1.0
        else:
            sp3 = 5.0

        # SP-4: Sector simplicity proxy (single-product sectors score higher)
        sector = data.sector
        sp4 = float(SECTOR_SIMPLICITY_MAP.get(sector, 5))

        score = sp1 * 0.30 + sp2 * 0.30 + sp3 * 0.25 + sp4 * 0.15

        parts = []
        if rev_cov is not None:
            parts.append(f"Rev CoV={rev_cov:.2f} (→{sp1:.0f}/10)")
        if op_cov is not None:
            parts.append(f"OpInc CoV={op_cov:.2f} (→{sp2:.0f}/10)")
        if pct_pos is not None:
            parts.append(f"FCF positive {pct_pos * 100:.0f}% of {len(fcf)} yrs (→{sp3:.0f}/10)")
        parts.append(f"Sector '{sector}' simplicity={sp4:.0f}/10")

        return score, "; ".join(parts)

    def _pillar_fcf(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 2: Free cash flow generative business."""
        fcf_s   = data.free_cash_flow_series
        rev_s   = data.revenue_series
        ni_s    = data.net_income_series
        capex_s = data.capex_series

        # FCF-1: FCF Margin TTM
        fcf_ttm = fcf_s[-1] if fcf_s else None
        rev_ttm = rev_s[-1] if rev_s else None
        fcf_margin: Optional[float] = (
            fcf_ttm / rev_ttm if fcf_ttm is not None and rev_ttm and rev_ttm > 0 else None
        )
        if   fcf_margin is None:    fcf1 = 5.0
        elif fcf_margin > 0.20:     fcf1 = 10.0
        elif fcf_margin > 0.15:     fcf1 = 8.0
        elif fcf_margin > 0.10:     fcf1 = 6.0
        elif fcf_margin > 0.05:     fcf1 = 4.0
        elif fcf_margin > 0.0:      fcf1 = 2.0
        else:                       fcf1 = 0.0

        # FCF-2: FCF 5-year CAGR
        fcf5     = fcf_s[-5:] if len(fcf_s) >= 5 else fcf_s
        fcf_cagr: Optional[float] = None
        if len(fcf5) >= 2 and fcf5[0] > 0 and fcf5[-1] > 0:
            fcf_cagr = (fcf5[-1] / fcf5[0]) ** (1 / (len(fcf5) - 1)) - 1
        if   fcf_cagr is None:  fcf2 = 5.0
        elif fcf_cagr > 0.15:   fcf2 = 10.0
        elif fcf_cagr > 0.10:   fcf2 = 8.0
        elif fcf_cagr > 0.05:   fcf2 = 6.0
        elif fcf_cagr > 0.0:    fcf2 = 4.0
        else:                   fcf2 = 1.0

        # FCF-3: FCF Yield (FCF / Enterprise Value)
        ev = data.info.get("enterpriseValue")
        fcf_yield: Optional[float] = (
            fcf_ttm / ev if fcf_ttm is not None and ev and ev > 0 else None
        )
        if   fcf_yield is None:     fcf3 = 5.0
        elif fcf_yield > 0.08:      fcf3 = 10.0
        elif fcf_yield > 0.06:      fcf3 = 8.0
        elif fcf_yield > 0.04:      fcf3 = 6.0
        elif fcf_yield > 0.02:      fcf3 = 4.0
        else:                       fcf3 = 2.0

        # FCF-4: FCF / Net Income (earnings quality check)
        n_fn = min(len(fcf_s), len(ni_s))
        fn_ratios = [fcf_s[i] / ni_s[i] for i in range(n_fn) if ni_s[i] > 0]
        fn_ratio: Optional[float] = statistics.mean(fn_ratios) if fn_ratios else None
        if   fn_ratio is None:  fcf4 = 5.0
        elif fn_ratio > 1.2:    fcf4 = 10.0
        elif fn_ratio > 1.0:    fcf4 = 8.0
        elif fn_ratio > 0.8:    fcf4 = 6.0
        elif fn_ratio > 0.5:    fcf4 = 4.0
        else:                   fcf4 = 1.0

        # FCF-5: Cumulative 5yr FCF vs cumulative 5yr CapEx
        fcf5yr  = fcf_s[-5:]   if len(fcf_s)   >= 5 else fcf_s
        cap5yr  = capex_s[-5:] if len(capex_s) >= 5 else capex_s
        n5 = min(len(fcf5yr), len(cap5yr))
        cum_fcf = sum(fcf5yr[:n5])
        cum_cap = sum(cap5yr[:n5])
        if cum_cap <= 0:
            fcf5 = 7.0  # essentially zero CapEx — excellent
        else:
            ratio_fc = cum_fcf / cum_cap
            if   ratio_fc > 3.0:    fcf5 = 10.0
            elif ratio_fc > 2.0:    fcf5 = 7.0
            elif ratio_fc > 1.0:    fcf5 = 4.0
            else:                   fcf5 = 1.0

        score = fcf1 * 0.25 + fcf2 * 0.20 + fcf3 * 0.25 + fcf4 * 0.15 + fcf5 * 0.15

        parts = []
        if fcf_margin is not None:
            parts.append(f"FCF margin={fcf_margin * 100:.1f}% TTM (→{fcf1:.0f}/10)")
        if fcf_cagr is not None:
            parts.append(f"FCF CAGR={fcf_cagr * 100:.1f}% (→{fcf2:.0f}/10)")
        if fcf_yield is not None:
            parts.append(f"FCF yield={fcf_yield * 100:.1f}% (→{fcf3:.0f}/10)")
        if fn_ratio is not None:
            parts.append(f"FCF/NI={fn_ratio:.2f}× (→{fcf4:.0f}/10)")
        if n5 > 0:
            parts.append(f"Cum FCF/CapEx={cum_fcf / max(cum_cap, 1):.1f}× (→{fcf5:.0f}/10)")

        return score, "; ".join(parts) or "Insufficient FCF data"

    def _pillar_dominant(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 3: Dominant market position."""
        gm_s  = data.gross_margin_series[-5:] if len(data.gross_margin_series) >= 5 else data.gross_margin_series
        op_s  = data.operating_income_series[-5:] if len(data.operating_income_series) >= 5 else data.operating_income_series
        rev_s = data.revenue_series[-5:] if len(data.revenue_series) >= 5 else data.revenue_series

        # DMP-1: Market cap scale as proxy for market rank
        mc = data.market_cap
        if   mc is None:        dmp1 = 5.0
        elif mc > 100e9:        dmp1 = 10.0
        elif mc > 50e9:         dmp1 = 8.0
        elif mc > 20e9:         dmp1 = 6.0
        elif mc > 5e9:          dmp1 = 4.0
        else:                   dmp1 = 2.0

        # DMP-2: Gross margin level (pricing power indicator)
        gm_avg: Optional[float] = statistics.mean(gm_s) if gm_s else None
        if   gm_avg is None:    dmp2 = 5.0
        elif gm_avg > 0.60:     dmp2 = 10.0
        elif gm_avg > 0.45:     dmp2 = 8.0
        elif gm_avg > 0.30:     dmp2 = 6.0
        elif gm_avg > 0.15:     dmp2 = 4.0
        else:                   dmp2 = 2.0

        # DMP-3: Revenue CAGR (growth demonstrates competitive momentum)
        rev_cagr: Optional[float] = None
        if len(rev_s) >= 3 and rev_s[0] > 0 and rev_s[-1] > 0:
            rev_cagr = (rev_s[-1] / rev_s[0]) ** (1 / (len(rev_s) - 1)) - 1
        if   rev_cagr is None:  dmp3 = 5.0
        elif rev_cagr > 0.15:   dmp3 = 10.0
        elif rev_cagr > 0.10:   dmp3 = 8.0
        elif rev_cagr > 0.05:   dmp3 = 6.0
        elif rev_cagr > 0.0:    dmp3 = 4.0
        else:                   dmp3 = 2.0

        # DMP-4: Operating margin stability — minimum op margin across 5yr
        op_margins = [
            op_s[i] / rev_s[i]
            for i in range(min(len(op_s), len(rev_s)))
            if rev_s[i] > 0
        ]
        om_min: Optional[float] = min(op_margins) if op_margins else None
        if   om_min is None:    dmp4 = 5.0
        elif om_min > 0.15:     dmp4 = 10.0
        elif om_min > 0.10:     dmp4 = 7.0
        elif om_min > 0.05:     dmp4 = 4.0
        else:                   dmp4 = 1.0

        score = dmp1 * 0.25 + dmp2 * 0.30 + dmp3 * 0.20 + dmp4 * 0.25

        parts = []
        if mc:
            parts.append(f"Market cap ${mc / 1e9:.0f}B (→{dmp1:.0f}/10)")
        if gm_avg is not None:
            parts.append(f"Gross margin avg {gm_avg * 100:.1f}% (→{dmp2:.0f}/10)")
        if rev_cagr is not None:
            parts.append(f"Rev CAGR {rev_cagr * 100:.1f}% (→{dmp3:.0f}/10)")
        if om_min is not None:
            parts.append(f"Min op margin {om_min * 100:.1f}% (→{dmp4:.0f}/10)")

        return score, "; ".join(parts) or "Insufficient market position data"

    def _pillar_moat(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 4: Large barriers to entry / economic moat."""
        gm_s  = data.gross_margin_series
        rev_s = data.revenue_series
        cap_s = data.capex_series

        # MOA-2: Gross margin level (proxy for pricing power / intangible advantage)
        gm_recent = gm_s[-3:] if len(gm_s) >= 3 else gm_s
        gm_avg: Optional[float] = statistics.mean(gm_recent) if gm_recent else None
        if   gm_avg is None:    moa2 = 5.0
        elif gm_avg > 0.60:     moa2 = 10.0
        elif gm_avg > 0.45:     moa2 = 8.0
        elif gm_avg > 0.30:     moa2 = 6.0
        elif gm_avg > 0.15:     moa2 = 4.0
        else:                   moa2 = 1.0

        # MOA-3: Gross margin trend (expanding = widening moat)
        gm_delta: Optional[float] = None
        if len(gm_s) >= 3:
            mid = max(1, len(gm_s) // 2)
            gm_early = statistics.mean(gm_s[:mid])
            gm_late  = statistics.mean(gm_s[mid:])
            gm_delta = gm_late - gm_early
            if   gm_delta > 0.02:   moa3 = 10.0
            elif gm_delta >= -0.02: moa3 = 7.0
            else:                   moa3 = 3.0
        else:
            moa3 = 5.0

        # MOA-4: R&D + CapEx intensity — investment building barriers
        rnd_s = data._series(data.income_stmt, "Research And Development")
        rev_ttm = rev_s[-1] if rev_s else None
        cap_ttm = cap_s[-1] if cap_s else None
        rnd_ttm = rnd_s[-1] if rnd_s else None
        barrier_pct: Optional[float] = None
        if rev_ttm and rev_ttm > 0:
            barrier = (rnd_ttm or 0.0) + (cap_ttm or 0.0)
            barrier_pct = barrier / rev_ttm
        if   barrier_pct is None:           moa4 = 5.0
        elif 0.05 <= barrier_pct <= 0.15:   moa4 = 10.0  # sweet spot
        elif barrier_pct > 0.15:            moa4 = 8.0   # high but capital-hungry
        else:                               moa4 = 6.0   # low investment

        # MOA-5: SG&A efficiency trend — declining share = operating leverage
        sga_s = data._series(
            data.income_stmt,
            "Selling General And Administration",
            "Selling General Administrative",
            "Selling And Marketing Expense",
        )
        sga_margins = [
            abs(sga_s[i]) / rev_s[i]
            for i in range(min(len(sga_s), len(rev_s)))
            if rev_s[i] > 0
        ]
        sga_delta: Optional[float] = None
        if len(sga_margins) >= 3:
            mid = len(sga_margins) // 2
            early_sga = statistics.mean(sga_margins[:mid])
            late_sga  = statistics.mean(sga_margins[mid:])
            sga_delta = late_sga - early_sga
            if   sga_delta < -0.02: moa5 = 10.0
            elif sga_delta <= 0.02: moa5 = 7.0
            else:                   moa5 = 3.0
        else:
            moa5 = 5.0

        # MOA-1 (MoatInvestor score) unavailable here — redistribute its 30%
        # equally: MOA-2: 27.5%, MOA-3: 22.5%, MOA-4: 22.5%, MOA-5: 27.5%
        score = moa2 * 0.275 + moa3 * 0.225 + moa4 * 0.225 + moa5 * 0.275

        parts = []
        if gm_avg is not None:
            parts.append(f"Gross margin {gm_avg * 100:.1f}% (→{moa2:.0f}/10)")
        if gm_delta is not None:
            parts.append(f"GM trend Δ{gm_delta * 100:+.1f}pp (→{moa3:.0f}/10)")
        if barrier_pct is not None:
            parts.append(f"R&D+CapEx/Rev={barrier_pct * 100:.1f}% (→{moa4:.0f}/10)")
        if sga_delta is not None:
            parts.append(f"SG&A/Rev trend Δ{sga_delta * 100:+.1f}pp (→{moa5:.0f}/10)")

        return score, "; ".join(parts) or "Insufficient moat data"

    def _pillar_roc(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 5: High return on capital."""
        roic_s = data.roic_series
        roe_s  = data.roe_series

        # ROC-1: ROIC TTM
        roic_ttm = roic_s[-1] if roic_s else None
        if   roic_ttm is None:  roc1 = 5.0
        elif roic_ttm > 0.25:   roc1 = 10.0
        elif roic_ttm > 0.20:   roc1 = 8.0
        elif roic_ttm > 0.15:   roc1 = 7.0
        elif roic_ttm > 0.10:   roc1 = 5.0
        elif roic_ttm > 0.08:   roc1 = 3.0
        else:                   roc1 = 0.0

        # ROC-2: ROIC 5-year average
        roic5 = roic_s[-5:] if len(roic_s) >= 5 else roic_s
        roic_avg: Optional[float] = statistics.mean(roic5) if roic5 else None
        if   roic_avg is None:  roc2 = 5.0
        elif roic_avg > 0.20:   roc2 = 10.0
        elif roic_avg > 0.15:   roc2 = 8.0
        elif roic_avg > 0.12:   roc2 = 6.0
        elif roic_avg > 0.08:   roc2 = 4.0
        else:                   roc2 = 1.0

        # ROC-3: ROIC consistency — lower std dev = more reliable moat
        roic_std: Optional[float] = statistics.stdev(roic5) if len(roic5) >= 2 else None
        if   roic_std is None:  roc3 = 5.0
        elif roic_std < 0.03:   roc3 = 10.0
        elif roic_std < 0.05:   roc3 = 7.0
        elif roic_std < 0.08:   roc3 = 4.0
        else:                   roc3 = 1.0

        # ROC-4: ROE TTM (leveraged return, secondary check)
        roe_ttm = roe_s[-1] if roe_s else None
        if   roe_ttm is None:   roc4 = 5.0
        elif roe_ttm > 0.25:    roc4 = 10.0
        elif roe_ttm > 0.20:    roc4 = 8.0
        elif roe_ttm > 0.15:    roc4 = 6.0
        elif roe_ttm > 0.10:    roc4 = 4.0
        else:                   roc4 = 1.0

        # ROC-5: ROIC trend (current 3yr avg vs earlier base)
        if len(roic_s) >= 3:
            roic_3yr  = statistics.mean(roic_s[-3:])
            roic_base = statistics.mean(roic_s[:-3]) if len(roic_s) > 3 else roic_s[0]
            roic_trend = roic_3yr - roic_base
            if   roic_trend > 0.02:     roc5 = 10.0
            elif roic_trend >= -0.02:   roc5 = 7.0
            else:                       roc5 = 3.0
        else:
            roc5 = 5.0

        score = roc1 * 0.30 + roc2 * 0.25 + roc3 * 0.20 + roc4 * 0.10 + roc5 * 0.15

        parts = []
        if roic_ttm is not None:
            parts.append(f"ROIC TTM={roic_ttm * 100:.1f}% (→{roc1:.0f}/10)")
        if roic_avg is not None:
            parts.append(f"ROIC 5yr avg={roic_avg * 100:.1f}% (→{roc2:.0f}/10)")
        if roic_std is not None:
            parts.append(f"ROIC std={roic_std * 100:.1f}pp (→{roc3:.0f}/10)")
        if roe_ttm is not None:
            parts.append(f"ROE={roe_ttm * 100:.1f}% (→{roc4:.0f}/10)")

        return score, "; ".join(parts) or "Insufficient ROIC / ROE data"

    def _pillar_extrinsic(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 6: Limited exposure to extrinsic risk."""
        sector   = data.sector
        industry = data.industry

        # EXT-1: Sector macro-predictability
        ext1 = float(SECTOR_RISK_MAP.get(sector, 5))

        # EXT-2: Market beta
        beta = data.beta
        if   beta is None:  ext2 = 5.0
        elif beta < 0.8:    ext2 = 10.0
        elif beta < 1.0:    ext2 = 8.0
        elif beta < 1.2:    ext2 = 6.0
        elif beta < 1.5:    ext2 = 4.0
        else:               ext2 = 1.0

        # EXT-3: Geographic concentration heuristic
        country = data.country
        global_sectors = {"Technology", "Communication Services", "Consumer Cyclical"}
        if country == "United States" and sector not in global_sectors:
            ext3 = 8.0   # primarily domestic
        elif country == "United States":
            ext3 = 6.0   # US-listed but likely global revenues
        else:
            ext3 = 5.0   # international HQ — higher FX / geopolitical exposure

        # EXT-4: Commodity / input cost sensitivity
        ext4 = float(COMMODITY_SENSITIVITY_MAP.get(industry, _DEFAULT_COMMODITY_SCORE))

        score = ext1 * 0.25 + ext2 * 0.30 + ext3 * 0.20 + ext4 * 0.25

        parts = [
            f"Sector '{sector}' risk={ext1:.0f}/10",
            f"Beta={beta:.2f} (→{ext2:.0f}/10)" if beta is not None else "Beta=N/A",
            f"Country '{country}' geo={ext3:.0f}/10",
            f"Industry '{industry}' commodity={ext4:.0f}/10",
        ]

        return score, "; ".join(parts)

    def _pillar_balance(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 7: Strong balance sheet / capital independence."""
        fcf_s   = data.free_cash_flow_series
        op_s    = data.operating_income_series
        shares_s = data.shares_outstanding_series
        ltd     = data.total_debt
        cash    = data.cash_and_equivalents
        cr      = data.current_ratio

        fcf5    = fcf_s[-5:] if len(fcf_s) >= 5 else fcf_s
        avg_fcf: Optional[float] = statistics.mean(fcf5) if fcf5 else None

        # BAL-1: Debt / avg FCF — Ackman's "3-year payback" rule
        debt_fcf_val: Optional[float] = None
        if ltd is not None and avg_fcf is not None and avg_fcf > 0:
            debt_fcf_val = ltd / avg_fcf
        if   debt_fcf_val is None:  bal1 = 5.0
        elif debt_fcf_val < 1.0:    bal1 = 10.0
        elif debt_fcf_val < 2.0:    bal1 = 8.0
        elif debt_fcf_val < 3.0:    bal1 = 6.0
        elif debt_fcf_val < 5.0:    bal1 = 3.0
        else:                       bal1 = 0.0

        # BAL-2: Net Debt / EBITDA
        ebitda  = data.info.get("ebitda")
        net_debt = (ltd - cash) if ltd is not None and cash is not None else None
        nd_ebitda: Optional[float] = None
        if net_debt is not None and ebitda is not None and ebitda > 0:
            nd_ebitda = net_debt / ebitda
        if   nd_ebitda is None:     bal2 = 5.0
        elif nd_ebitda < 0:         bal2 = 10.0  # net cash
        elif nd_ebitda < 1.0:       bal2 = 8.0
        elif nd_ebitda < 2.0:       bal2 = 6.0
        elif nd_ebitda < 3.0:       bal2 = 4.0
        else:                       bal2 = 1.0

        # BAL-3: Interest coverage (EBIT / |Interest Expense|)
        int_s   = data._series(data.income_stmt, "Interest Expense")
        ebit    = op_s[-1]       if op_s  else None
        int_exp = abs(int_s[-1]) if int_s else None
        coverage: Optional[float] = None
        if ebit is not None and int_exp is not None and int_exp > 0:
            coverage = ebit / int_exp
        if   coverage is None:  bal3 = 7.0   # no interest = excellent
        elif coverage > 15:     bal3 = 10.0
        elif coverage > 10:     bal3 = 8.0
        elif coverage > 5:      bal3 = 6.0
        elif coverage > 3:      bal3 = 4.0
        else:                   bal3 = 1.0

        # BAL-4: Current ratio
        if   cr is None:    bal4 = 5.0
        elif cr > 2.0:      bal4 = 10.0
        elif cr > 1.5:      bal4 = 8.0
        elif cr > 1.2:      bal4 = 6.0
        elif cr > 1.0:      bal4 = 4.0
        else:               bal4 = 1.0

        # BAL-5: 5-year share dilution
        shares_chg: Optional[float] = None
        if len(shares_s) >= 2:
            ref = shares_s[-5] if len(shares_s) >= 5 else shares_s[0]
            if ref > 0:
                shares_chg = (shares_s[-1] / ref) - 1
        if   shares_chg is None:    bal5 = 5.0
        elif shares_chg < -0.05:    bal5 = 10.0
        elif shares_chg < 0.0:      bal5 = 8.0
        elif shares_chg < 0.05:     bal5 = 6.0
        else:                       bal5 = 0.0

        score = bal1 * 0.30 + bal2 * 0.25 + bal3 * 0.20 + bal4 * 0.10 + bal5 * 0.15

        parts = []
        if debt_fcf_val is not None:
            parts.append(f"Debt/FCF={debt_fcf_val:.1f}× (→{bal1:.0f}/10)")
        if nd_ebitda is not None:
            parts.append(f"NetDebt/EBITDA={nd_ebitda:.1f}× (→{bal2:.0f}/10)")
        if coverage is not None:
            parts.append(f"Interest cov={coverage:.1f}× (→{bal3:.0f}/10)")
        if cr is not None:
            parts.append(f"Current ratio={cr:.2f} (→{bal4:.0f}/10)")
        if shares_chg is not None:
            parts.append(f"Shares 5yr {shares_chg * 100:+.1f}% (→{bal5:.0f}/10)")

        return score, "; ".join(parts) or "Insufficient balance sheet data"

    def _pillar_mgmt(self, data: "FinancialData") -> tuple[float, str]:
        """Commandment 8: Excellent management and good governance."""
        info    = data.info
        rev_s   = data.revenue_series
        fcf_s   = data.free_cash_flow_series
        ni_s    = data.net_income_series

        # MGT-1: Insider ownership (skin in the game)
        insider = data.insider_ownership_pct
        if   insider is None:   mgt1 = 5.0
        elif insider > 0.10:    mgt1 = 10.0
        elif insider > 0.05:    mgt1 = 8.0
        elif insider > 0.02:    mgt1 = 6.0
        elif insider > 0.005:   mgt1 = 4.0
        else:                   mgt1 = 2.0

        # MGT-2: Institutional ownership (40–80% = ideal sponsorship)
        institutional = info.get("heldPercentInstitutions")
        if   institutional is None:         mgt2 = 5.0
        elif 0.40 <= institutional <= 0.80: mgt2 = 10.0
        elif institutional > 0.80:          mgt2 = 7.0
        else:                               mgt2 = 5.0

        # MGT-3: Buyback yield (5yr avg absolute repurchases / market cap)
        rep_s = data._series(
            data.cash_flow,
            "Repurchase Of Capital Stock",
            "Common Stock Repurchased",
        )
        mc = data.market_cap
        rep5 = rep_s[-5:] if len(rep_s) >= 5 else rep_s
        buyback_yield: Optional[float] = None
        if rep5 and mc and mc > 0:
            avg_buyback  = statistics.mean([abs(r) for r in rep5])
            buyback_yield = avg_buyback / mc
        if   buyback_yield is None: mgt3 = 5.0
        elif buyback_yield > 0.03:  mgt3 = 10.0
        elif buyback_yield > 0.02:  mgt3 = 8.0
        elif buyback_yield > 0.01:  mgt3 = 6.0
        elif buyback_yield > 0.0:   mgt3 = 4.0
        else:                       mgt3 = 1.0

        # MGT-4: Dividend payout ratio (sustainable 20–50% = best)
        payout: Optional[float] = info.get("payoutRatio")
        if payout is None:
            div_s = data._series(
                data.cash_flow,
                "Common Stock Dividend Paid",
                "Payment Of Dividends",
                "Cash Dividends Paid",
            )
            n_dn   = min(len(div_s), len(ni_s))
            payouts = [abs(div_s[i]) / ni_s[i] for i in range(n_dn) if ni_s[i] > 0]
            payout = statistics.mean(payouts) if payouts else None
        if   payout is None:                    mgt4 = 5.0
        elif 0.20 <= payout <= 0.50:            mgt4 = 10.0
        elif 0.50 < payout <= 0.70:             mgt4 = 7.0
        elif payout < 0.20 or payout <= 0.90:   mgt4 = 5.0
        else:                                   mgt4 = 2.0

        # MGT-5: Revenue-per-employee growth (3yr proxy using revenue CAGR)
        rev_per_emp_growth: Optional[float] = None
        if len(rev_s) >= 4 and rev_s[-4] > 0:
            rev_per_emp_growth = (rev_s[-1] / rev_s[-4]) ** (1 / 3) - 1
        if   rev_per_emp_growth is None:    mgt5 = 5.0
        elif rev_per_emp_growth > 0.05:     mgt5 = 10.0
        elif rev_per_emp_growth > 0.0:      mgt5 = 7.0
        else:                               mgt5 = 2.0

        score = mgt1 * 0.30 + mgt2 * 0.15 + mgt3 * 0.25 + mgt4 * 0.15 + mgt5 * 0.15

        parts = []
        if insider is not None:
            parts.append(f"Insider {insider * 100:.1f}% (→{mgt1:.0f}/10)")
        if institutional is not None:
            parts.append(f"Institutional {institutional * 100:.1f}% (→{mgt2:.0f}/10)")
        if buyback_yield is not None:
            parts.append(f"Buyback yield {buyback_yield * 100:.1f}% (→{mgt3:.0f}/10)")
        if payout is not None:
            parts.append(f"Payout ratio {payout * 100:.0f}% (→{mgt4:.0f}/10)")
        if rev_per_emp_growth is not None:
            parts.append(f"Rev growth {rev_per_emp_growth * 100:.1f}%/yr (→{mgt5:.0f}/10)")

        return score, "; ".join(parts) or "Insufficient governance data"

    # ───────────────────────────────────────── valuation overlay (informational)

    def _valuation_flag(self, data: "FinancialData") -> Optional[str]:
        """FCF yield + forward P/E valuation summary — not scored, informational only."""
        info    = data.info
        ev      = info.get("enterpriseValue")
        fcf_s   = data.free_cash_flow_series
        fcf_ttm = fcf_s[-1] if fcf_s else None

        signals:   list[str] = []
        attractive = 0
        expensive  = 0

        if fcf_ttm is not None and ev and ev > 0:
            fcf_yield = fcf_ttm / ev
            if fcf_yield > 0.06:
                attractive += 1
                signals.append(f"FCF yield {fcf_yield * 100:.1f}% (attractive >6%)")
            elif fcf_yield < 0.03:
                expensive += 1
                signals.append(f"FCF yield {fcf_yield * 100:.1f}% (expensive <3%)")
            else:
                signals.append(f"FCF yield {fcf_yield * 100:.1f}% (fair 3–6%)")

        fwd_pe = info.get("forwardPE")
        if fwd_pe:
            if fwd_pe < 15:
                attractive += 1
                signals.append(f"Fwd P/E {fwd_pe:.1f}× (attractive <15×)")
            elif fwd_pe > 25:
                expensive += 1
                signals.append(f"Fwd P/E {fwd_pe:.1f}× (expensive >25×)")
            else:
                signals.append(f"Fwd P/E {fwd_pe:.1f}× (fair 15–25×)")

        if not signals:
            return None

        if   expensive > attractive:    verdict = "Expensive"
        elif attractive > expensive:    verdict = "Attractive"
        else:                           verdict = "Fair Value"

        return f"VALUATION: {verdict} — " + "; ".join(signals)

    # ─────────────────────────────────────────────────────────── helpers ──────

    def _pillar_rule(
        self,
        name: str,
        score_0_10: float,
        pillar_key: str,
        description: str,
        source: str,
        explanation: str,
    ) -> Rule:
        """Build a proportionally-scored pillar Rule (points_awarded = score/10 × possible)."""
        possible = float(self._PILLAR_WEIGHTS[pillar_key])
        awarded  = (score_0_10 / 10.0) * possible
        passed   = score_0_10 >= 6.0
        return Rule(
            name=name,
            passed=passed,
            value=round(score_0_10, 2),
            threshold=6.0,
            points_awarded=round(awarded, 2),
            points_possible=possible,
            description=description,
            source=source,
            explanation=explanation,
        )

    @staticmethod
    def _cov(values: list[float]) -> Optional[float]:
        """Coefficient of Variation = stdev / |mean|. None if insufficient data."""
        if len(values) < 2:
            return None
        mean = statistics.mean(values)
        if mean == 0:
            return None
        return statistics.stdev(values) / abs(mean)
