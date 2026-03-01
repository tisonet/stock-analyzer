"""
Red Flag Score module — forensic distress and competitive-decay detector.

The mirror image of MoatInvestor: detects warning signals across 12 criteria
rather than confirming competitive strengths. Higher score = cleaner company.

Scoring semantics (intentionally inverted from normal investors):
- Rules PASS when the company is CLEAN on that metric (no red flag).
- Rules FAIL when a red flag IS present.
- total_score 0–100: higher = safer; lower = more distress signals.

Pillars and point allocations (total = 100 pts):
  Pillar 1 — Financial Health & Solvency (40 pts):
    1. Altman Z-Score              (15 pts)  Z >= 1.8
    2. Interest Coverage           (10 pts)  EBIT / interest >= 1.5x
    3. Liquidity (Current Ratio)   ( 8 pts)  current_ratio >= 1.0
    4. FCF Sustainability          ( 7 pts)  FCF negative in <= 1 of last 3 years

  Pillar 2 — Earnings Quality (25 pts):
    5. Beneish M-Score             (15 pts)  M-Score <= -1.78
    6. Accruals Quality            ( 5 pts)  (NI - OCF) / avg_assets <= 0.10
    7. Receivables Quality         ( 5 pts)  rec_growth / rev_growth <= 1.5x

  Pillar 3 — Capital Allocation (15 pts):
    8. ROIC vs Cost of Capital     (10 pts)  avg ROIC (3yr) >= 8%
    9. Asset Base Investment       ( 5 pts)  CapEx / Depreciation >= 0.75x

  Pillar 4 — Business Deterioration (20 pts):
   10. Gross Margin Stability      (10 pts)  (gm_latest - gm_3y_ago) >= -3pp
   11. Revenue Trend               ( 5 pts)  <= 1 year of negative YoY growth in last 3
   12. Debt Load                   ( 5 pts)  Total Debt / EBITDA <= 5x

Verdict labels (danger severity, inverted from normal):
  >= 80 -> "Clean"     (no significant red flags)
  >= 60 -> "Watch"     (minor warning signs)
  >= 40 -> "Caution"   (notable red flags present)
  >= 20 -> "Danger"    (serious distress signals)
   < 20 -> "Critical"  (severe, potentially terminal signals)

Weight in consensus aggregator: 0 (analytical lens, not a buy/sell signal).
Display: (100 - total_score) / 10 = danger score 0.0–10.0.

Sources:
- Altman, E.I., "Financial Ratios, Discriminant Analysis and the Prediction of
  Corporate Bankruptcy" (Journal of Finance, 1968)
- Beneish, M.D., "The Detection of Earnings Manipulation" (Financial Analysts
  Journal, 1999)
- Mauboussin, "Measuring the Moat" (Credit Suisse, 2013) — ROIC vs WACC
- Graham, "The Intelligent Investor" (1949) — liquidity & debt discipline
- Sloan, R., "Do Stock Prices Fully Reflect Information in Accruals and Cash
  Flows About Future Earnings?" (Accounting Review, 1996) — accruals quality
"""
from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.investors.base_investor import BaseInvestor, InvestorScore, Rule

logger = logging.getLogger(__name__)


class AntiMoatInvestor(BaseInvestor):
    """
    Forensic distress and competitive-decay detector.

    Returns InvestorScore with total_score 0-100 where higher = safer.
    Display as danger score: (100 - total_score) / 10 on a 0-10 scale.
    verdict = "Clean" | "Watch" | "Caution" | "Danger" | "Critical".
    Weight in consensus = 0 (analytical, excluded from buy/sell consensus).
    """

    @property
    def name(self) -> str:
        return "Red Flag Score"

    def _verdict(self, score: float) -> str:
        """Override: danger-level labels (inverted — high score = safer)."""
        if score >= 80:
            return "Clean"
        if score >= 60:
            return "Watch"
        if score >= 40:
            return "Caution"
        if score >= 20:
            return "Danger"
        return "Critical"

    def score(self, data: "FinancialData") -> InvestorScore:  # noqa: C901
        rules: list[Rule] = []
        red_flags: list[str] = []

        # ── Pre-compute shared series ─────────────────────────────────────────
        rev = data.revenue_series             # oldest → newest
        gm = data.gross_margin_series         # oldest → newest
        fcf = data.free_cash_flow_series      # oldest → newest
        ni = data.net_income_series           # oldest → newest
        ocf = data.operating_cash_flow_series # oldest → newest
        op_inc = data.operating_income_series # oldest → newest

        # ── Rule 1: Altman Z-Score (15 pts) ──────────────────────────────────
        # Z = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MC/TL) + Rev/TA
        # < 1.8 = distress zone; 1.8-3.0 = grey zone; >= 3.0 = safe
        z_score: Optional[float] = None
        r1_passed = False
        r1_desc = "Insufficient data for Altman Z-Score computation"
        try:
            ta = data.total_assets
            ca = data.current_assets
            cl = data.current_liabilities
            tl = data.total_liabilities
            mc = data.market_cap
            ebit = op_inc[-1] if op_inc else None
            revenue = rev[-1] if rev else None
            retained_e = data._latest(
                data.balance_sheet, "Retained Earnings", "RetainedEarnings"
            )
            if all(v is not None and v != 0 for v in [ta, tl]) and ca is not None and cl is not None:
                wc = ca - cl
                re = retained_e if retained_e is not None else 0.0
                ebit_v = ebit if ebit is not None else 0.0
                mc_v = mc if mc is not None else 0.0
                rev_v = revenue if revenue is not None else 0.0
                z_score = (
                    1.2 * (wc / ta)
                    + 1.4 * (re / ta)
                    + 3.3 * (ebit_v / ta)
                    + 0.6 * (mc_v / tl)
                    + rev_v / ta
                )
                r1_passed = z_score >= 1.8
                zone = (
                    "safe zone" if z_score >= 3.0
                    else "grey zone (watch)" if z_score >= 1.8
                    else "distress zone"
                )
                r1_desc = (
                    f"Altman Z-Score={z_score:.2f} ({zone}) — "
                    + (
                        "no bankruptcy distress signal; financial structure appears sound"
                        if r1_passed
                        else "distress zone: elevated bankruptcy risk within 2 years"
                    )
                )
                if z_score < 1.8:
                    red_flags.append(
                        f"Altman Z-Score {z_score:.2f} — distress zone; "
                        "elevated bankruptcy probability within 2 years"
                    )
                elif z_score < 3.0:
                    red_flags.append(
                        f"Altman Z-Score {z_score:.2f} — grey zone; "
                        "financial health uncertain, monitor closely"
                    )
        except Exception as e:
            logger.debug(f"Altman Z-Score failed: {e}")

        rules.append(self._make_rule(
            name="Altman Z-Score: Z >= 1.8 (out of distress zone)",
            value=round(z_score, 2) if z_score is not None else None,
            threshold=1.8,
            points_possible=15.0,
            passed=r1_passed,
            description=r1_desc,
            source=(
                "Altman, E.I., 'Financial Ratios, Discriminant Analysis and the Prediction "
                "of Corporate Bankruptcy' (Journal of Finance, 1968)"
            ),
            explanation=(
                "The Altman Z-Score combines five financial ratios into a single bankruptcy "
                "predictor. Below 1.8 = distress zone with elevated failure probability; "
                "1.8-3.0 = grey zone; above 3.0 = safe zone. Originally calibrated on "
                "manufacturing firms but broadly applicable as an early-warning signal."
            ),
        ))

        # ── Rule 2: Interest Coverage (10 pts) ───────────────────────────────
        # EBIT / interest expense >= 1.5x; below 1.5x = earnings barely cover debt service
        interest_coverage: Optional[float] = None
        r2_passed = False
        r2_desc = "Insufficient data for interest coverage computation"
        try:
            ebit_v = op_inc[-1] if op_inc else None
            interest = data._latest(
                data.income_stmt,
                "Interest Expense",
                "Interest And Debt Expense",
                "Net Interest Income",  # may be negative for payers
            )
            if ebit_v is not None and interest is not None:
                # yfinance typically reports interest expense as negative
                interest_abs = abs(interest)
                if interest_abs > 0:
                    interest_coverage = ebit_v / interest_abs
                    r2_passed = interest_coverage >= 1.5
                    r2_desc = (
                        f"Interest coverage={interest_coverage:.2f}x "
                        f"(EBIT=${ebit_v/1e9:.1f}B / Interest=${interest_abs/1e9:.1f}B) — "
                        + (
                            "earnings comfortably cover debt service; no liquidity pressure"
                            if r2_passed
                            else "earnings barely cover interest; refinancing or default risk elevated"
                        )
                    )
                    if interest_coverage < 1.0:
                        red_flags.append(
                            f"Interest coverage {interest_coverage:.2f}x — "
                            "EBIT cannot cover interest payments; debt spiral risk"
                        )
                    elif interest_coverage < 1.5:
                        red_flags.append(
                            f"Interest coverage {interest_coverage:.2f}x — "
                            "dangerously thin margin; one earnings miss creates debt-service crisis"
                        )
                else:
                    # No meaningful interest expense — company not leveraged
                    interest_coverage = 99.0
                    r2_passed = True
                    r2_desc = "Negligible interest expense — company effectively unleveraged"
        except Exception as e:
            logger.debug(f"Interest coverage failed: {e}")

        rules.append(self._make_rule(
            name="Interest Coverage: EBIT / interest expense >= 1.5x",
            value=round(interest_coverage, 2) if interest_coverage is not None and interest_coverage < 99 else interest_coverage,
            threshold=1.5,
            points_possible=10.0,
            passed=r2_passed,
            description=r2_desc,
            source=(
                "Graham, 'The Intelligent Investor' (1949) Ch. 14 — bond coverage standards; "
                "Damodaran, 'Corporate Finance' — interest coverage ratio thresholds"
            ),
            explanation=(
                "Interest coverage (EBIT ÷ interest expense) measures how many times operating "
                "earnings can service the company's debt. Below 1.5x, a single bad quarter can "
                "trigger covenant breaches or force distressed refinancing. Below 1.0x, the "
                "company is technically insolvent on an operating basis."
            ),
        ))

        # ── Rule 3: Current Ratio / Liquidity (8 pts) ────────────────────────
        # current_assets / current_liabilities >= 1.0
        cr = data.current_ratio
        r3_passed = cr is not None and cr >= 1.0
        if cr is not None:
            r3_desc = (
                f"Current ratio={cr:.2f}x — "
                + (
                    "short-term obligations covered by current assets; no liquidity crisis"
                    if r3_passed
                    else "current assets < current liabilities; company cannot cover near-term obligations"
                )
            )
            if cr < 1.0:
                red_flags.append(
                    f"Current ratio {cr:.2f}x — cannot cover short-term obligations; "
                    "liquidity crisis risk if credit tightens"
                )
        else:
            r3_desc = "Current ratio data unavailable"

        rules.append(self._make_rule(
            name="Liquidity: Current ratio >= 1.0x",
            value=round(cr, 2) if cr is not None else None,
            threshold=1.0,
            points_possible=8.0,
            passed=r3_passed,
            description=r3_desc,
            source=(
                "Graham, 'The Intelligent Investor' (1949) — liquidity margin of safety; "
                "Damodaran 'Applied Corporate Finance' — current ratio distress thresholds"
            ),
            explanation=(
                "The current ratio (current assets ÷ current liabilities) measures whether "
                "a company can pay its bills due within 12 months. Below 1.0x means the "
                "company has more short-term obligations than liquid assets — a classic "
                "sign of near-term liquidity stress, particularly dangerous when credit "
                "markets tighten."
            ),
        ))

        # ── Rule 4: FCF Sustainability (7 pts) ───────────────────────────────
        # FCF negative in <= 1 of the last 3 years (chronic negativity = burning cash)
        fcf_recent = fcf[-3:] if len(fcf) >= 3 else fcf
        neg_fcf_years = sum(1 for v in fcf_recent if v < 0)
        r4_passed = neg_fcf_years <= 1
        chronic = neg_fcf_years >= 3

        if fcf_recent:
            fcf_str = ", ".join(f"${v/1e9:.1f}B" for v in fcf_recent)
            r4_desc = (
                f"FCF last {len(fcf_recent)} years: [{fcf_str}] — "
                f"{neg_fcf_years} year(s) negative — "
                + (
                    "free cash flow broadly positive; not burning cash"
                    if r4_passed
                    else "chronic FCF burn; company is consuming cash reserves or increasing debt"
                )
            )
            if chronic:
                red_flags.append(
                    f"FCF negative for {neg_fcf_years} of last {len(fcf_recent)} years — "
                    "chronic cash burn; survival dependent on external financing"
                )
            elif neg_fcf_years == 2:
                red_flags.append(
                    "FCF negative in 2 of last 3 years — emerging cash burn pattern; "
                    "watch for acceleration"
                )
        else:
            r4_desc = "FCF data unavailable"

        rules.append(self._make_rule(
            name="FCF Sustainability: FCF negative in <= 1 of last 3 years",
            value=float(neg_fcf_years) if fcf_recent else None,
            threshold=1.0,
            points_possible=7.0,
            passed=r4_passed,
            description=r4_desc,
            source=(
                "Klarman, 'Margin of Safety' (1991) — cash generation as the bedrock of value; "
                "Buffett, Berkshire letters — owner earnings and free cash flow primacy"
            ),
            explanation=(
                "Chronic negative free cash flow (FCF = operating cash flow minus capex) means "
                "the company is burning through its cash reserves or funding operations via "
                "debt — unsustainable without external capital. Three consecutive negative "
                "years is the canonical distress signal, but two in three years warrants "
                "close monitoring."
            ),
        ))

        # ── Rule 5: Beneish M-Score (15 pts) ─────────────────────────────────
        # Earnings manipulation probability indicator.
        # M-Score > -1.78 suggests likely manipulation.
        # Formula: M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
        #              + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
        m_score: Optional[float] = None
        r5_passed = False
        r5_desc = "Insufficient data for Beneish M-Score (requires 2+ years of statements)"
        try:
            m_score = self._beneish_m_score(data)
            if m_score is not None:
                r5_passed = m_score <= -1.78
                manipulation_prob = "likely manipulation" if m_score > -1.78 else "manipulation unlikely"
                r5_desc = (
                    f"Beneish M-Score={m_score:.3f} (threshold=-1.78) — {manipulation_prob}; "
                    + (
                        "earnings quality appears sound across 8 manipulation indices"
                        if r5_passed
                        else "score above -1.78 flags elevated earnings manipulation probability"
                    )
                )
                if m_score > -1.78:
                    red_flags.append(
                        f"Beneish M-Score {m_score:.2f} > -1.78 — "
                        "earnings manipulation signal; financial statements may be inflated"
                    )
        except Exception as e:
            logger.debug(f"Beneish M-Score failed: {e}")

        rules.append(self._make_rule(
            name="Beneish M-Score: M-Score <= -1.78 (manipulation unlikely)",
            value=round(m_score, 3) if m_score is not None else None,
            threshold=-1.78,
            points_possible=15.0,
            passed=r5_passed,
            description=r5_desc,
            source=(
                "Beneish, M.D., 'The Detection of Earnings Manipulation' "
                "(Financial Analysts Journal, 1999)"
            ),
            explanation=(
                "The Beneish M-Score combines 8 financial ratios to detect earnings manipulation. "
                "Scores above -1.78 flag companies with statistical characteristics similar to "
                "confirmed manipulators (Enron, WorldCom scored > -1.78 before collapse). "
                "The eight indices measure: receivables inflation, gross margin deterioration, "
                "asset quality changes, sales growth acceleration, depreciation policy changes, "
                "SGA bloat, leverage increases, and accruals quality."
            ),
        ))

        # ── Rule 6: Accruals Quality (5 pts) ─────────────────────────────────
        # (Net Income - Operating Cash Flow) / Avg Total Assets <= 0.10
        # High accruals = earnings not backed by cash; manipulation or accounting aggressiveness
        accruals_ratio: Optional[float] = None
        r6_passed = False
        r6_desc = "Insufficient data for accruals quality computation"
        try:
            ni_v = ni[-1] if ni else None
            ocf_v = ocf[-1] if ocf else None
            ta_curr = data._latest(data.balance_sheet, "Total Assets")
            ta_series = data._series(data.balance_sheet, "Total Assets")
            avg_ta = (
                statistics.mean(ta_series[-2:]) if len(ta_series) >= 2
                else ta_series[-1] if ta_series else None
            )
            if ni_v is not None and ocf_v is not None and avg_ta is not None and avg_ta != 0:
                accruals_ratio = (ni_v - ocf_v) / avg_ta
                r6_passed = accruals_ratio <= 0.10
                r6_desc = (
                    f"Accruals ratio={(accruals_ratio * 100):.1f}% of assets "
                    f"(NI=${ni_v/1e9:.1f}B, OCF=${ocf_v/1e9:.1f}B) — "
                    + (
                        "earnings closely backed by cash; low accruals indicate real profits"
                        if r6_passed
                        else "high accruals: net income significantly exceeds operating cash — "
                        "quality of earnings is poor"
                    )
                )
                if accruals_ratio > 0.10:
                    red_flags.append(
                        f"Accruals ratio {accruals_ratio * 100:.1f}% of assets — "
                        "net income far exceeds operating cash; earnings quality is suspect"
                    )
        except Exception as e:
            logger.debug(f"Accruals quality failed: {e}")

        rules.append(self._make_rule(
            name="Accruals Quality: (Net Income - OCF) / avg assets <= 10%",
            value=round(accruals_ratio * 100, 1) if accruals_ratio is not None else None,
            threshold=10.0,
            points_possible=5.0,
            passed=r6_passed,
            description=r6_desc,
            source=(
                "Sloan, R., 'Do Stock Prices Fully Reflect Information in Accruals and Cash "
                "Flows About Future Earnings?' (Accounting Review, 1996) — accruals anomaly"
            ),
            explanation=(
                "The accruals ratio measures the gap between net income and operating cash flow, "
                "scaled by assets. Large positive accruals mean the company is booking profits "
                "that never materialise as cash — a classic red flag for aggressive revenue "
                "recognition or inflated asset values. Sloan (1996) showed that high-accrual "
                "companies systematically underperform over the following year."
            ),
        ))

        # ── Rule 7: Receivables Quality (5 pts) ──────────────────────────────
        # Receivables growing > 1.5x faster than revenue = channel stuffing / inflated revenue
        rec_series = data._series(data.balance_sheet, "Receivables", "Accounts Receivable")
        r7_passed = True  # default pass if insufficient data
        r7_value: Optional[float] = None
        r7_desc = "Insufficient receivables history for quality check (need >= 2 years)"
        try:
            if len(rec_series) >= 2 and len(rev) >= 2:
                rec_growth = (rec_series[-1] - rec_series[-2]) / abs(rec_series[-2]) if rec_series[-2] != 0 else None
                rev_growth = (rev[-1] - rev[-2]) / abs(rev[-2]) if rev[-2] != 0 else None
                if rec_growth is not None and rev_growth is not None and abs(rev_growth) > 0.001:
                    ratio = rec_growth / rev_growth if rev_growth > 0 else None
                    if ratio is not None:
                        r7_value = round(ratio, 2)
                        r7_passed = ratio <= 1.5
                        r7_desc = (
                            f"Receivables growth={rec_growth * 100:.1f}% vs "
                            f"Revenue growth={rev_growth * 100:.1f}% "
                            f"(ratio={ratio:.2f}x) — "
                            + (
                                "receivables growing in line with revenue; no channel-stuffing signal"
                                if r7_passed
                                else "receivables growing far faster than revenue; possible channel "
                                "stuffing or premature revenue recognition"
                            )
                        )
                        if ratio > 2.0:
                            red_flags.append(
                                f"Receivables growing {ratio:.1f}x faster than revenue — "
                                "strong channel-stuffing or revenue recognition red flag"
                            )
                        elif ratio > 1.5:
                            red_flags.append(
                                f"Receivables growing {ratio:.1f}x faster than revenue — "
                                "watch for revenue quality deterioration"
                            )
                elif rev_growth is not None and abs(rev_growth) <= 0.001 and rec_growth is not None and rec_growth > 0.10:
                    # Revenue flat but receivables rising
                    r7_passed = False
                    r7_value = rec_growth * 100
                    r7_desc = (
                        f"Revenue flat while receivables grew {rec_growth * 100:.1f}% — "
                        "possible revenue pull-forward or collection problems"
                    )
                    red_flags.append(
                        f"Receivables up {rec_growth * 100:.1f}% while revenue is flat — "
                        "collection quality or revenue recognition concern"
                    )
        except Exception as e:
            logger.debug(f"Receivables quality failed: {e}")

        rules.append(self._make_rule(
            name="Receivables Quality: receivables growth / revenue growth <= 1.5x",
            value=r7_value,
            threshold=1.5,
            points_possible=5.0,
            passed=r7_passed,
            description=r7_desc,
            source=(
                "Beneish, M.D. (1999) — DSRI (Days Sales Receivable Index) component; "
                "Graham & Dodd, 'Security Analysis' — receivables as earnings quality signal"
            ),
            explanation=(
                "When accounts receivable grow significantly faster than revenue, it suggests "
                "the company is booking revenue before customers actually pay — a classic sign "
                "of channel stuffing, premature revenue recognition, or deteriorating customer "
                "credit quality. A 1.5x ratio (receivables growing 50% faster than revenue) "
                "is the commonly used warning threshold."
            ),
        ))

        # ── Rule 8: ROIC vs Cost of Capital (10 pts) ─────────────────────────
        # avg ROIC (last 3 years) >= 8% (proxy for WACC)
        # ROIC < WACC = company destroys value with every dollar reinvested
        roic_s = data.roic_series
        roic_recent = roic_s[-3:] if len(roic_s) >= 3 else roic_s
        roic_avg: Optional[float] = statistics.mean(roic_recent) if roic_recent else None
        r8_passed = roic_avg is not None and roic_avg >= 0.08
        if roic_avg is not None:
            r8_desc = (
                f"Avg ROIC (last {len(roic_recent)} yr)={roic_avg * 100:.1f}% "
                f"(WACC proxy=8%) — "
                + (
                    "ROIC exceeds cost of capital; company creates value with each reinvested dollar"
                    if r8_passed
                    else "ROIC below cost of capital; every reinvested dollar destroys shareholder value"
                )
            )
            if roic_avg < 0:
                red_flags.append(
                    f"ROIC={roic_avg * 100:.1f}% — negative; capital allocation is destroying equity value"
                )
            elif roic_avg < 0.08:
                red_flags.append(
                    f"ROIC={roic_avg * 100:.1f}% < 8% WACC proxy — "
                    "value-destroying reinvestment; growth makes the business worse"
                )
        else:
            r8_desc = "ROIC data unavailable"

        rules.append(self._make_rule(
            name="ROIC vs Cost of Capital: avg ROIC (3yr) >= 8%",
            value=round(roic_avg * 100, 1) if roic_avg is not None else None,
            threshold=8.0,
            points_possible=10.0,
            passed=r8_passed,
            description=r8_desc,
            source=(
                "Mauboussin, 'Measuring the Moat' (Credit Suisse, 2013) — ROIC vs WACC framework; "
                "Koller, Goedhart & Wessels, 'Valuation' (McKinsey, 2015)"
            ),
            explanation=(
                "When Return on Invested Capital (ROIC) falls below the Weighted Average Cost "
                "of Capital (WACC), every dollar the company reinvests destroys shareholder "
                "value — the business is a value trap regardless of revenue growth. An 8% "
                "threshold serves as a simple WACC proxy; companies consistently below this "
                "level are compounding losses even during profitable periods."
            ),
        ))

        # ── Rule 9: Asset Base Investment (5 pts) ─────────────────────────────
        # CapEx / Depreciation >= 0.75x
        # Below 0.75x = company is under-investing in its asset base (harvest mode)
        capex_s = data.capex_series
        capex_v = capex_s[-1] if capex_s else None
        depreciation = self._depreciation_latest(data)
        capex_dep_ratio: Optional[float] = None
        r9_passed = False
        r9_desc = "Insufficient data for asset base investment check"
        try:
            if capex_v is not None and depreciation is not None and depreciation > 0:
                capex_dep_ratio = capex_v / depreciation
                r9_passed = capex_dep_ratio >= 0.75
                r9_desc = (
                    f"CapEx/Depreciation={capex_dep_ratio:.2f}x "
                    f"(CapEx=${capex_v/1e9:.1f}B, D&A=${depreciation/1e9:.1f}B) — "
                    + (
                        "investing at or above asset replacement rate; no harvest-mode signal"
                        if r9_passed
                        else "CapEx/D&A below 0.75x for 3+ years — under-investing; "
                        "asset base is deteriorating (harvest mode)"
                    )
                )
                if capex_dep_ratio < 0.5:
                    red_flags.append(
                        f"CapEx/Depreciation {capex_dep_ratio:.2f}x — severe under-investment; "
                        "company in harvest mode, consuming its asset base"
                    )
                elif capex_dep_ratio < 0.75:
                    red_flags.append(
                        f"CapEx/Depreciation {capex_dep_ratio:.2f}x — "
                        "below replacement rate; long-term competitiveness at risk"
                    )
        except Exception as e:
            logger.debug(f"Asset base investment failed: {e}")

        rules.append(self._make_rule(
            name="Asset Base Investment: CapEx / Depreciation >= 0.75x",
            value=round(capex_dep_ratio, 2) if capex_dep_ratio is not None else None,
            threshold=0.75,
            points_possible=5.0,
            passed=r9_passed,
            description=r9_desc,
            source=(
                "Mauboussin, 'Measuring the Moat' (Credit Suisse, 2013) — maintenance vs. "
                "growth capex distinction; Buffett — distinguishing reinvestment capex from "
                "maintenance capex"
            ),
            explanation=(
                "CapEx divided by depreciation reveals whether a company is investing enough "
                "to maintain its productive asset base. Below 0.75x for multiple years indicates "
                "'harvest mode' — extracting value from existing assets without reinvesting "
                "for the future. This is fine for mature businesses returning cash, but "
                "dangerous for companies that need capital investment to remain competitive."
            ),
        ))

        # ── Rule 10: Gross Margin Stability (10 pts) ──────────────────────────
        # Gross margin NOT declined more than 3pp over the last 3 years
        # Moat erosion signal: competitors are winning on price
        gm_delta: Optional[float] = None
        r10_passed = False
        r10_desc = "Insufficient gross margin history (need >= 4 years)"
        try:
            if len(gm) >= 4:
                gm_3y_ago = gm[-4] if len(gm) >= 4 else gm[0]
                gm_latest = gm[-1]
                gm_delta = gm_latest - gm_3y_ago
                r10_passed = gm_delta >= -0.03
                r10_desc = (
                    f"Gross margin: {gm_3y_ago * 100:.1f}% → {gm_latest * 100:.1f}% "
                    f"(Δ={gm_delta * 100:+.1f}pp over 3 years) — "
                    + (
                        "pricing power intact; gross margin stable or expanding"
                        if r10_passed
                        else f"pricing power eroding: margin compressed {abs(gm_delta) * 100:.1f}pp — "
                        "competitors are winning on price"
                    )
                )
                if gm_delta < -0.05:
                    red_flags.append(
                        f"Gross margin compressed {abs(gm_delta) * 100:.1f}pp over 3 years — "
                        "severe moat erosion; pricing power lost to competition"
                    )
                elif gm_delta < -0.03:
                    red_flags.append(
                        f"Gross margin compressed {abs(gm_delta) * 100:.1f}pp over 3 years — "
                        "competitive pressure mounting on pricing"
                    )
            elif len(gm) >= 2:
                gm_delta = gm[-1] - gm[0]
                r10_passed = gm_delta >= -0.03
                r10_desc = (
                    f"Gross margin: {gm[0] * 100:.1f}% → {gm[-1] * 100:.1f}% "
                    f"(Δ={gm_delta * 100:+.1f}pp over {len(gm) - 1} year(s)) — "
                    + (
                        "margin stable; no pricing erosion signal"
                        if r10_passed
                        else "margin declining — competitive moat may be weakening"
                    )
                )
        except Exception as e:
            logger.debug(f"Gross margin stability failed: {e}")

        rules.append(self._make_rule(
            name="Gross Margin Stability: margin decline <= 3pp over 3 years",
            value=round(gm_delta * 100, 1) if gm_delta is not None else None,
            threshold=-3.0,
            points_possible=10.0,
            passed=r10_passed,
            description=r10_desc,
            source=(
                "Porter, 'Competitive Strategy' (1980) — gross margin as competitive moat proxy; "
                "Mauboussin, 'Measuring the Moat' (2013) — margin compression = moat erosion"
            ),
            explanation=(
                "Gross margin compression of more than 300 basis points over three years is the "
                "single most reliable indicator of competitive moat erosion. It signals that "
                "competitors are forcing price reductions or that input cost inflation cannot "
                "be passed through to customers — both hallmarks of a business losing its "
                "pricing power and economic moat."
            ),
        ))

        # ── Rule 11: Revenue Trend (5 pts) ────────────────────────────────────
        # Not in sustained revenue decline: <= 1 year of negative YoY growth in last 3 years
        yoy_neg_count = 0
        r11_passed = True
        r11_desc = "Insufficient revenue history (need >= 3 years)"
        r11_value: Optional[float] = None
        try:
            if len(rev) >= 3:
                recent_rev = rev[-4:] if len(rev) >= 4 else rev
                yoy_rates_rev = [
                    (recent_rev[i] - recent_rev[i - 1]) / abs(recent_rev[i - 1])
                    for i in range(1, len(recent_rev))
                    if recent_rev[i - 1] != 0
                ]
                yoy_neg_count = sum(1 for r in yoy_rates_rev if r < 0)
                r11_value = float(yoy_neg_count)
                r11_passed = yoy_neg_count <= 1
                rates_str = ", ".join(f"{r * 100:+.1f}%" for r in yoy_rates_rev)
                r11_desc = (
                    f"Revenue YoY growth last {len(yoy_rates_rev)} years: [{rates_str}] — "
                    f"{yoy_neg_count} year(s) of decline — "
                    + (
                        "revenue broadly growing; no sustained decline pattern"
                        if r11_passed
                        else "revenue declining in multiple years; structural demand erosion"
                    )
                )
                if yoy_neg_count >= 3:
                    red_flags.append(
                        "Revenue declining in 3+ consecutive years — structural demand destruction; "
                        "business model may be obsolete"
                    )
                elif yoy_neg_count == 2:
                    red_flags.append(
                        "Revenue declined in 2 of last 3 years — sustained shrinkage pattern; "
                        "growth recovery is not yet evident"
                    )
        except Exception as e:
            logger.debug(f"Revenue trend failed: {e}")

        rules.append(self._make_rule(
            name="Revenue Trend: <= 1 year of negative YoY growth in last 3 years",
            value=r11_value,
            threshold=1.0,
            points_possible=5.0,
            passed=r11_passed,
            description=r11_desc,
            source=(
                "Lynch, 'One Up On Wall Street' (1989) — revenue trend as business health proxy; "
                "Porter, 'Competitive Strategy' (1980) — revenue decline as industry position signal"
            ),
            explanation=(
                "Sustained revenue decline across multiple years signals structural demand "
                "erosion — customers are leaving, markets are shrinking, or the business "
                "model is becoming obsolete. One down year can be cyclical or one-off; "
                "two or more within three years indicates a pattern that management cannot "
                "explain away with transitory factors."
            ),
        ))

        # ── Rule 12: Debt Load (5 pts) ─────────────────────────────────────────
        # Total Debt / EBITDA <= 5x
        # Above 5x is the consensus threshold for over-leveraged distress
        debt = data.total_debt
        dep_for_ebitda = self._depreciation_latest(data)
        ebitda: Optional[float] = None
        debt_ebitda: Optional[float] = None
        r12_passed = False
        r12_desc = "Insufficient data for Debt/EBITDA computation"
        try:
            ebit_for_12 = op_inc[-1] if op_inc else None
            if ebit_for_12 is not None and dep_for_ebitda is not None:
                ebitda = ebit_for_12 + dep_for_ebitda
            if debt is not None and ebitda is not None and ebitda > 0:
                debt_ebitda = debt / ebitda
                r12_passed = debt_ebitda <= 5.0
                r12_desc = (
                    f"Debt/EBITDA={debt_ebitda:.1f}x "
                    f"(Debt=${debt/1e9:.1f}B, EBITDA=${ebitda/1e9:.1f}B) — "
                    + (
                        "leverage manageable; debt load within sustainable range"
                        if r12_passed
                        else "over-leveraged: at > 5x EBITDA, debt refinancing risk is elevated"
                    )
                )
                if debt_ebitda > 8.0:
                    red_flags.append(
                        f"Debt/EBITDA {debt_ebitda:.1f}x — severely over-leveraged; "
                        "covenant breach or restructuring risk is high"
                    )
                elif debt_ebitda > 5.0:
                    red_flags.append(
                        f"Debt/EBITDA {debt_ebitda:.1f}x — over-leveraged; "
                        "limited financial flexibility in a rising rate environment"
                    )
            elif debt is not None and ebitda is not None and ebitda <= 0:
                # Negative EBITDA is itself a red flag
                r12_passed = False
                r12_desc = (
                    f"Debt/EBITDA: EBITDA is negative (${ebitda/1e9:.1f}B) — "
                    "company cannot service debt from operations at all"
                )
                red_flags.append(
                    "Negative EBITDA with positive debt — company cannot service debt "
                    "from operations; survival depends on asset sales or new equity"
                )
        except Exception as e:
            logger.debug(f"Debt load failed: {e}")

        rules.append(self._make_rule(
            name="Debt Load: Total Debt / EBITDA <= 5x",
            value=round(debt_ebitda, 1) if debt_ebitda is not None else None,
            threshold=5.0,
            points_possible=5.0,
            passed=r12_passed,
            description=r12_desc,
            source=(
                "Damodaran, 'Corporate Finance' — debt capacity and coverage ratios; "
                "S&P/Moody's leveraged loan covenant standards — 5x–6x Debt/EBITDA "
                "is the investment-grade / leveraged crossover threshold"
            ),
            explanation=(
                "Total Debt divided by EBITDA measures how many years of operating cash "
                "generation are needed to repay all debt. Above 5x is the broadly accepted "
                "threshold for over-leverage; above 8x is considered severely distressed. "
                "Highly leveraged companies have limited financial flexibility, are vulnerable "
                "to rate rises or earnings misses, and face existential refinancing risk "
                "when debt matures."
            ),
        ))

        return self._build_result(rules, red_flags)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _depreciation_latest(self, data: "FinancialData") -> Optional[float]:
        """
        Extract most recent depreciation & amortization expense.
        Searches income statement first, then cash flow statement.
        Returns absolute value (D&A may be stored as negative).
        """
        try:
            dep = data._latest(
                data.income_stmt,
                "Reconciled Depreciation",
                "Depreciation And Amortization",
                "Depreciation Amortization Depletion",
                "Depreciation",
            )
            if dep is not None:
                return abs(dep)
            # Fallback: cash flow statement
            dep_cf = data._latest(
                data.cash_flow,
                "Depreciation And Amortization",
                "Depreciation Amortization Depletion",
                "Depreciation",
                "Depreciation And Amortization In Income Statement",
            )
            if dep_cf is not None:
                return abs(dep_cf)
        except Exception as e:
            logger.debug(f"Depreciation extraction failed: {e}")
        return None

    def _beneish_m_score(self, data: "FinancialData") -> Optional[float]:
        """
        Compute Beneish M-Score from 8 financial indices.
        Returns None if key inputs are unavailable.

        M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
              + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

        Index thresholds (individual flags):
          DSRI > 1.465  — receivables inflation
          GMI  > 1.193  — gross margin deterioration
          AQI  > 1.254  — asset quality decline
          SGI  > 1.607  — aggressive sales growth
          DEPI > 1.083  — depreciation policy change
          SGAI > 1.041  — SGA bloat
          LVGI > 1.0    — leverage increase
          TATA > 0.031  — total accruals / assets
        """
        try:
            # --- shared series ---
            rev_s = data.revenue_series
            gm_s = data.gross_margin_series
            ni_s = data.net_income_series
            ocf_s = data.operating_cash_flow_series

            if len(rev_s) < 2 or len(gm_s) < 2:
                return None

            rev_t  = rev_s[-1]
            rev_t1 = rev_s[-2]
            gm_t   = gm_s[-1]
            gm_t1  = gm_s[-2]

            # TA series
            ta_s = data._series(data.balance_sheet, "Total Assets")
            if len(ta_s) < 2:
                return None
            ta_t  = ta_s[-1]
            ta_t1 = ta_s[-2]
            if ta_t == 0 or ta_t1 == 0:
                return None

            # Receivables series
            rec_s = data._series(data.balance_sheet, "Receivables", "Accounts Receivable")
            dsri = None
            if len(rec_s) >= 2 and rev_t1 != 0 and rev_t != 0:
                dsr_t  = rec_s[-1] / rev_t
                dsr_t1 = rec_s[-2] / rev_t1
                dsri = dsr_t / dsr_t1 if dsr_t1 != 0 else None

            # GMI: gross margin deterioration
            gmi = gm_t1 / gm_t if gm_t != 0 and gm_t > 0 else None

            # AQI: asset quality index  (1 - (CA + PPE) / TA)
            ca_s = data._series(
                data.balance_sheet, "Current Assets", "Total Current Assets"
            )
            ppe_s = data._series(
                data.balance_sheet,
                "Net PPE",
                "Net Property Plant Equipment",
                "Property Plant Equipment Net",
                "Properties",
            )
            aqi = None
            if len(ca_s) >= 2 and len(ppe_s) >= 2:
                aq_t  = 1 - (ca_s[-1] + ppe_s[-1]) / ta_t
                aq_t1 = 1 - (ca_s[-2] + ppe_s[-2]) / ta_t1
                aqi = aq_t / aq_t1 if aq_t1 != 0 else None

            # SGI: sales growth index
            sgi = rev_t / rev_t1 if rev_t1 != 0 else None

            # DEPI: depreciation index
            dep_s_inc = data._series(
                data.income_stmt,
                "Reconciled Depreciation",
                "Depreciation And Amortization",
                "Depreciation Amortization Depletion",
            )
            if not dep_s_inc:
                dep_s_inc = data._series(
                    data.cash_flow,
                    "Depreciation And Amortization",
                    "Depreciation Amortization Depletion",
                )
            depi = None
            if len(dep_s_inc) >= 2 and len(ppe_s) >= 2:
                dep_t  = abs(dep_s_inc[-1])
                dep_t1 = abs(dep_s_inc[-2])
                ppe_t  = ppe_s[-1]
                ppe_t1 = ppe_s[-2]
                if ppe_t > 0 and ppe_t1 > 0 and dep_t > 0:
                    dep_rate_t  = dep_t  / ppe_t
                    dep_rate_t1 = dep_t1 / ppe_t1
                    depi = dep_rate_t1 / dep_rate_t if dep_rate_t != 0 else None

            # SGAI: SGA index
            sga_s = data._series(
                data.income_stmt,
                "Selling General And Administrative",
                "Selling General Administrative",
                "General And Administrative Expense",
            )
            sgai = None
            if len(sga_s) >= 2 and rev_t != 0 and rev_t1 != 0:
                sga_ratio_t  = abs(sga_s[-1]) / rev_t
                sga_ratio_t1 = abs(sga_s[-2]) / rev_t1
                sgai = sga_ratio_t / sga_ratio_t1 if sga_ratio_t1 != 0 else None

            # LVGI: leverage index
            ltd_s = data._series(data.balance_sheet, "Long Term Debt", "Total Debt")
            cl_s  = data._series(
                data.balance_sheet, "Current Liabilities", "Total Current Liabilities"
            )
            lvgi = None
            if len(ltd_s) >= 2 and len(cl_s) >= 2:
                lev_t  = (ltd_s[-1] + cl_s[-1]) / ta_t
                lev_t1 = (ltd_s[-2] + cl_s[-2]) / ta_t1
                lvgi = lev_t / lev_t1 if lev_t1 != 0 else None

            # TATA: total accruals to total assets
            tata = None
            if ni_s and ocf_s:
                ni_latest  = ni_s[-1]
                ocf_latest = ocf_s[-1]
                tata = (ni_latest - ocf_latest) / ta_t

            # Require at least 5 of 8 indices to compute M-Score
            components = [dsri, gmi, aqi, sgi, depi, sgai, lvgi, tata]
            available = [c for c in components if c is not None]
            if len(available) < 5:
                return None

            # Use 0.0 for unavailable components (conservative — doesn't inflate score)
            dsri_v  = dsri  if dsri  is not None else 1.0
            gmi_v   = gmi   if gmi   is not None else 1.0
            aqi_v   = aqi   if aqi   is not None else 1.0
            sgi_v   = sgi   if sgi   is not None else 1.0
            depi_v  = depi  if depi  is not None else 1.0
            sgai_v  = sgai  if sgai  is not None else 1.0
            lvgi_v  = lvgi  if lvgi  is not None else 1.0
            tata_v  = tata  if tata  is not None else 0.0

            m = (
                -4.84
                + 0.920 * dsri_v
                + 0.528 * gmi_v
                + 0.404 * aqi_v
                + 0.892 * sgi_v
                + 0.115 * depi_v
                - 0.172 * sgai_v
                + 4.679 * tata_v
                - 0.327 * lvgi_v
            )
            return m

        except Exception as e:
            logger.debug(f"Beneish M-Score computation failed: {e}")
            return None
