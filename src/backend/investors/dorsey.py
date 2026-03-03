"""
Pat Dorsey — Dorsey Asset Management scoring module.

Dorsey is the former Director of Equity Research at Morningstar and founder of
Dorsey Asset Management. He authored "The Little Book That Builds Wealth" (2008)
and "The Five Rules for Successful Stock Investing" (2003).

Dorsey's framework rests on four sources of economic moats:
  1. Intangible assets — brands, patents, regulatory licences
  2. Switching costs — embedded software, mission-critical data, high migration cost
  3. Network effects — value grows with user count (exchanges, payment networks)
  4. Cost advantages — structural scale, location, or process edge

His investment process asks three questions in sequence:
  1. Does this business have a durable economic moat?
  2. Does the financial history prove the moat is real? (ROIC > cost of capital)
  3. Is the current price a reasonable margin of safety?

This module focuses on questions 1 and 2 — financial proof of the moat and
reinvestment runway quality. The scoring rules are the quantitative fingerprints
Dorsey identifies as confirming (or denying) genuine competitive advantage.

Dorsey Asset Management runs a concentrated global portfolio (~10 positions),
currently holding Danaher, Meta Platforms, and ASML — all combining wide moats
with meaningful reinvestment runways.

Sources:
  - Dorsey, P. "The Little Book That Builds Wealth" (2008)
  - Dorsey, P. "The Five Rules for Successful Stock Investing" (2003)
  - Dorsey Asset Management: "Maximizing Moats: Reinvestment Runways &
    Capital Allocation" (2023)
  - MOI Global interview (2020), YIS interview
  - Quartr Insights: "Pat Dorsey: Economic Moats and Beyond"
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class DorseyInvestor(BaseInvestor):
    """
    Pat Dorsey / Dorsey Asset Management scoring.

    Seeks businesses with durable economic moats confirmed by sustained high ROIC,
    strong net margins, FCF quality, reinvestment runway, clean earnings, and
    conservative capital structure. Six rules, 100 points total.
    """

    @property
    def name(self) -> str:
        return "Dorsey"

    def score(self, data: "FinancialData") -> InvestorScore:
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Rule 1: ROIC ≥ 15% — financial fingerprint of a moat ────── 25 pts
        # Dorsey's foundational test: sustained ROIC above cost of capital (~9–10%)
        # is the definitive financial proof that an economic moat exists. A business
        # without a moat sees excess returns competed away over time; one with a moat
        # sustains them. 15%+ consistently — not just on average — is required because
        # cyclical peaks do not indicate a structural advantage.
        # Source: "The Little Book That Builds Wealth" Ch.1 — "the financial fingerprint
        # of a moat is ROIC sustainably exceeding the cost of capital"
        roic_s = data.roic_series
        roic_avg = statistics.mean(roic_s) if roic_s else None
        roic_ok = (
            roic_avg is not None
            and roic_avg >= 0.15
            and all(r > 0 for r in roic_s)
        )
        r1 = self._make_rule(
            name="ROIC ≥ 15% (moat's financial fingerprint)",
            value=roic_avg * 100 if roic_avg is not None else None,
            threshold=15.0,
            points_possible=25.0,
            description=(
                f"ROIC avg = {roic_avg * 100:.1f}% across {len(roic_s)} years — "
                f"{'sustained above cost of capital: financial proof of an economic moat' if roic_ok else 'insufficient; excess returns not sustained above cost of capital'}"
                if roic_avg is not None
                else "ROIC data unavailable"
            ),
            source=(
                "Dorsey, 'The Little Book That Builds Wealth' (2008) — "
                "'the financial fingerprint of a moat is ROIC sustainably above the cost of capital'"
            ),
            passed=roic_ok,
            explanation=(
                "ROIC is the acid test of moat existence. A business with a genuine competitive "
                "advantage earns returns on capital that persist as competitors try and fail to erode "
                "them. 15% ROIC is roughly 1.5× the cost of capital — sufficient evidence of a real "
                "structural advantage. Cyclical spikes do not qualify; consistency across years is "
                "the proof Dorsey requires."
            ),
        )
        rules.append(r1)
        if not r1.passed and roic_s and any(r < 0 for r in roic_s):
            red_flags.append(
                "Negative ROIC in at least one year — a business that destroys capital in "
                "adverse conditions does not have the structural advantage Dorsey requires"
            )
        if not r1.passed and roic_avg is not None and roic_avg < 0.08:
            red_flags.append(
                f"ROIC of {roic_avg * 100:.1f}% — at or below cost of capital; "
                "this is the financial signature of a commodity business with no durable moat"
            )

        # ── Rule 2: Net Profit Margin ≥ 15% — structural pricing power ─── 20 pts
        # A business with a true moat — brand, switching costs, network effects — can
        # sustain net margins above 15% because structural pricing power allows it to
        # cover all costs (COGS, SG&A, interest, taxes) with meaningful surplus.
        # Net margin is more holistic than gross margin: it captures operating leverage,
        # cost discipline, and capital structure efficiency simultaneously.
        # Source: "The Five Rules for Successful Stock Investing" (2003) — "sustained
        # net profit margins above 15% are among the clearest indicators of a moat"
        ni_s = data.net_income_series
        rev_s = data.revenue_series
        n_nm = min(len(ni_s), len(rev_s))
        net_margins = [ni_s[i] / rev_s[i] for i in range(n_nm) if rev_s[i] > 0]
        net_margin_avg = statistics.mean(net_margins) if net_margins else None
        nm_ok = net_margin_avg is not None and net_margin_avg >= 0.15

        r2 = self._make_rule(
            name="Net Profit Margin ≥ 15% (structural pricing power)",
            value=net_margin_avg * 100 if net_margin_avg is not None else None,
            threshold=15.0,
            points_possible=20.0,
            description=(
                f"Net margin avg = {net_margin_avg * 100:.1f}% across {n_nm} years — "
                f"{'strong: structural pricing power confirmed; full cost-stack covered with surplus' if nm_ok else 'below threshold; insufficient pricing power for a competitively advantaged business'}"
                if net_margin_avg is not None
                else "Net margin data unavailable"
            ),
            source=(
                "Dorsey, 'The Five Rules for Successful Stock Investing' (2003) — "
                "'sustained net margins above 15% are among the clearest indicators of competitive advantage'"
            ),
            passed=nm_ok,
            explanation=(
                "Net profit margin (net income ÷ revenue) captures the full economics of a business after "
                "all costs — COGS, SG&A, interest, taxes. A company consistently converting 15%+ of "
                "revenue to profit has structural pricing power: it charges enough to cover all costs with "
                "meaningful surplus. Commodity businesses and capital-intensive companies cannot maintain "
                "these margins across full economic cycles."
            ),
        )
        rules.append(r2)
        if not r2.passed and net_margins and any(m < 0 for m in net_margins):
            red_flags.append(
                "Negative net margins in at least one year — unprofitable operations signal "
                "an absence of pricing power and structural competitive advantage"
            )

        # ── Rule 3: FCF/Sales ≥ 5% — cash generation quality ─────────── 15 pts
        # Dorsey identifies FCF-to-sales as a key quality metric: it tests whether the
        # business converts revenue to usable cash rather than merely reporting accounting
        # profits. Moated businesses (Oracle, Visa, Danaher) generate FCF margins well
        # above 5% because their advantages allow high operating leverage and minimal
        # capital requirements. Low FCF/sales signals either margin problems (competitive
        # industry) or capex intensity consuming the cash that should compound.
        # Source: "The Five Rules" — "FCF/sales above 5% is the quality threshold; it
        # shows the business converts revenue to real, investable cash"
        fcf_margin_s = data.fcf_margin_series
        fcf_margin_avg = statistics.mean(fcf_margin_s) if fcf_margin_s else None
        fcf_ok = fcf_margin_avg is not None and fcf_margin_avg >= 0.05

        r3 = self._make_rule(
            name="FCF/Sales ≥ 5% (cash generation quality)",
            value=fcf_margin_avg * 100 if fcf_margin_avg is not None else None,
            threshold=5.0,
            points_possible=15.0,
            description=(
                f"FCF/Sales avg = {fcf_margin_avg * 100:.1f}% across {len(fcf_margin_s)} years — "
                f"{'quality cash generator: revenue converts to real cash above the 5% quality bar' if fcf_ok else 'below threshold; accounting profits may exceed cash reality'}"
                if fcf_margin_avg is not None
                else "FCF/Sales data unavailable"
            ),
            source=(
                "Dorsey, 'The Five Rules for Successful Stock Investing' (2003) — "
                "'FCF to sales above 5% is the quality threshold; it confirms revenue "
                "converts to real, investable cash'"
            ),
            passed=fcf_ok,
            explanation=(
                "FCF/Sales separates cash-generating businesses from those reporting accounting profits "
                "that never materialise as cash. A moated business grows with minimal incremental capital "
                "investment, translating a high share of revenue directly to free cash flow. Below 5% "
                "often signals heavy capital requirements, intense competition, or earnings quality risk."
            ),
        )
        rules.append(r3)
        if not r3.passed and fcf_margin_avg is not None and fcf_margin_avg < 0:
            red_flags.append(
                "Negative FCF/Sales — the business consumes cash rather than generating it; "
                "this is incompatible with Dorsey's moat-and-reinvestment framework"
            )

        # ── Rule 4: Revenue CAGR ≥ 8% — reinvestment runway ────────── 20 pts
        # Dorsey's central thesis in "Maximizing Moats" (2023): the value of a competitive
        # advantage is maximised when a business can reinvest capital at high incremental
        # ROIC over many years. A wide moat without a reinvestment runway is a cash cow,
        # not a compounder. 8% CAGR provides sufficient growth to meaningfully compound
        # a high-ROIC business over a full investment cycle. Dorsey's holdings —
        # Meta Platforms, ASML, Danaher — all combine moat depth with meaningful growth.
        # Source: Dorsey Asset Management, "Maximizing Moats" (2023) — "the value of
        # competitive advantage is maximised when reinvestment at high ROIC can continue
        # for an extended period of time"
        rev_cagr_s = data.revenue_series
        rev_cagr: float | None = None
        if len(rev_cagr_s) >= 3 and rev_cagr_s[0] > 0 and rev_cagr_s[-1] > 0:
            years = len(rev_cagr_s) - 1
            rev_cagr = (rev_cagr_s[-1] / rev_cagr_s[0]) ** (1 / years) - 1
        cagr_ok = rev_cagr is not None and rev_cagr >= 0.08

        r4 = self._make_rule(
            name="Revenue CAGR ≥ 8% (reinvestment runway)",
            value=rev_cagr * 100 if rev_cagr is not None else None,
            threshold=8.0,
            points_possible=20.0,
            description=(
                f"Revenue CAGR = {rev_cagr * 100:.1f}% over {len(rev_cagr_s) - 1} years — "
                f"{'long reinvestment runway: moat + growth compounds equity value over decades' if cagr_ok else 'insufficient growth; moat functions as a cash cow, not a compounder'}"
                if rev_cagr is not None
                else "Insufficient revenue history for CAGR (≥ 3 years required)"
            ),
            source=(
                "Dorsey Asset Management, 'Maximizing Moats: Reinvestment Runways & "
                "Capital Allocation' (2023) — 'the value of competitive advantage is "
                "maximised when reinvestment at high ROIC can continue for an extended period'"
            ),
            passed=cagr_ok,
            explanation=(
                "A wide moat without a reinvestment runway is a dividend stock, not a compounder. "
                "Dorsey argues that compounding power depends on (a) the ROIC advantage and (b) how "
                "long the business can reinvest at those rates. 8% revenue CAGR represents sufficient "
                "growth to deploy capital at above-average returns through a full investment cycle. "
                "Dorsey Asset Management's core holdings combine moat depth with this kind of runway."
            ),
        )
        rules.append(r4)
        if not r4.passed and rev_cagr is not None and rev_cagr < 0:
            red_flags.append(
                "Declining revenue — a shrinking business has no reinvestment runway; "
                "Dorsey requires growth to compound the moat advantage over time"
            )

        # ── Rule 5: Earnings Quality — OCF / Net Income ≥ 0.85 ──────── 10 pts
        # Dorsey explicitly flags: "if earnings consistently outpace cash flow over time,
        # investigate the accounting." The OCF/NI ratio tests whether reported profits are
        # backed by actual cash. A ratio below 0.85 means roughly 15%+ of reported earnings
        # never materialised as cash — which can indicate aggressive revenue recognition,
        # capitalised costs, or channel stuffing. Only years with positive net income are
        # used (the ratio is undefined when NI is negative).
        # Source: "The Five Rules for Successful Stock Investing" (2003)
        ocf_s = data.operating_cash_flow_series
        ni_s2 = data.net_income_series
        n_eq = min(len(ocf_s), len(ni_s2))
        eq_ratios = [
            ocf_s[i] / ni_s2[i]
            for i in range(n_eq)
            if ni_s2[i] > 0
        ]
        eq_ratio = statistics.mean(eq_ratios) if eq_ratios else None
        eq_ok = eq_ratio is not None and eq_ratio >= 0.85

        r5 = self._make_rule(
            name="Earnings Quality: OCF/Net Income ≥ 0.85",
            value=eq_ratio,
            threshold=0.85,
            points_possible=10.0,
            description=(
                f"OCF/Net Income avg = {eq_ratio:.2f}x "
                f"({len(eq_ratios)} years with positive NI) — "
                f"{'high-quality earnings: cash flow tracks reported profits closely' if eq_ok else 'quality concern: reported profits materially exceed cash generation'}"
                if eq_ratio is not None
                else "Earnings quality unavailable (no years with positive net income)"
            ),
            source=(
                "Dorsey, 'The Five Rules for Successful Stock Investing' (2003) — "
                "'if earnings consistently outpace cash flow, investigate the accounting "
                "before trusting the earnings number'"
            ),
            passed=eq_ok,
            explanation=(
                "Operating cash flow divided by net income measures earnings quality. Below 1.0 means "
                "some reported profit never became cash; below 0.85 suggests a meaningful, potentially "
                "structural gap. Dorsey flags this as an accounting red flag: aggressive revenue "
                "recognition, capitalised costs, or working capital deterioration can all cause earnings "
                "to run persistently ahead of the cash they claim to represent."
            ),
        )
        rules.append(r5)
        if not r5.passed and eq_ratio is not None and eq_ratio < 0.50:
            red_flags.append(
                f"OCF/Net Income of {eq_ratio:.2f}x — less than half of reported earnings are "
                "backed by operating cash flow; aggressive accrual accounting is a likely explanation"
            )

        # ── Rule 6: Capital Structure — D/E ≤ 1.0 and Coverage ≥ 3× ── 10 pts
        # Dorsey warns that high leverage (a) inflates ROE, masking absent moats,
        # (b) destroys moats in recessions when credit tightens and growth must pause,
        # and (c) creates permanent capital impairment risk. D/E ≤ 1.0 is his outer bound
        # for non-financial businesses. Interest coverage ≥ 3× confirms the business
        # services debt comfortably through cycles. A genuine moat earns adequate returns
        # without requiring leverage — excessive debt is a compensating factor, not a feature.
        # Source: "The Five Rules" — "high leverage inflates ROE and destroys moats in
        # downturns; a true moat should never require debt to earn adequate returns"
        raw_de = data.debt_to_equity
        # yfinance info sometimes reports D/E as a percentage (e.g. 82 = 0.82×)
        de = raw_de / 100.0 if (raw_de is not None and raw_de > 10) else raw_de

        # Interest coverage = EBIT (latest) / |Interest Expense| (latest)
        op_inc_s = data.operating_income_series
        int_exp_s = data._series(data.income_stmt, "Interest Expense")
        ebit_latest = op_inc_s[-1] if op_inc_s else None
        int_exp_latest = abs(int_exp_s[-1]) if int_exp_s else None
        coverage: float | None = None
        if ebit_latest is not None and int_exp_latest is not None and int_exp_latest > 0:
            coverage = ebit_latest / int_exp_latest

        de_ok = de is not None and de <= 1.0
        # No debt (no interest expense) → coverage check not applicable → pass
        coverage_ok = coverage is None or coverage >= 3.0
        cap_ok = de_ok and coverage_ok

        if de is not None and coverage is not None:
            if cap_ok:
                cap_tail = "conservative: leverage not masking moat absence"
            else:
                parts = []
                if not de_ok:
                    parts.append(f"D/E {de:.2f}x exceeds 1.0x limit")
                if not coverage_ok:
                    parts.append(f"coverage {coverage:.1f}x below 3x minimum")
                cap_tail = "; ".join(parts)
            cap_desc = (
                f"D/E = {de:.2f}x, Interest Coverage = {coverage:.1f}x — {cap_tail}"
            )
        elif de is not None:
            cap_tail = "within Dorsey's 1.0x limit" if de_ok else f"D/E {de:.2f}x exceeds 1.0x limit"
            cap_desc = f"D/E = {de:.2f}x (interest coverage unavailable) — {cap_tail}"
        else:
            cap_desc = "Capital structure data unavailable"

        r6 = self._make_rule(
            name="Capital Structure: D/E ≤ 1.0 and Interest Coverage ≥ 3×",
            value=de,
            threshold=1.0,
            points_possible=10.0,
            description=cap_desc,
            source=(
                "Dorsey, 'The Five Rules for Successful Stock Investing' (2003) — "
                "'high leverage inflates ROE and destroys moats in downturns; "
                "a true moat should never require debt to earn adequate returns'"
            ),
            passed=cap_ok,
            explanation=(
                "Dorsey warns that leverage is the great distorter: it artificially inflates ROE, "
                "masking the absence of a real moat, and adds fragility in recessions. A business with "
                "a genuine competitive advantage can fund growth from operating cash flows without heavy "
                "debt. D/E above 1.0 warrants additional scrutiny of whether the apparent returns on "
                "equity reflect a true structural advantage or simply financial engineering."
            ),
        )
        rules.append(r6)
        if not r6.passed and de is not None and de > 2.0:
            red_flags.append(
                f"D/E of {de:.2f}x — leverage of this magnitude can mask an absent moat by "
                "inflating ROE, and creates permanent impairment risk in a downturn"
            )
        if not r6.passed and coverage is not None and coverage < 1.5:
            red_flags.append(
                f"Interest coverage of {coverage:.1f}x — earnings barely cover interest expense; "
                "one revenue downturn away from a debt servicing crisis"
            )

        return self._build_result(rules, red_flags)
