"""
Unit tests for Bill Ackman / Pershing Square scoring module.

Test archetypes from the plan:
  A. "Chipotle Clone"   — ideal Ackman business, expect 80+
  B. "Valeant Warning"  — high debt, volatile revenue, poor FCF, expect <35
  C. "Alphabet Quality" — high FCF, low debt, strong ROIC, expect 70-85
  D. "Contrarian"       — quality business with 30%+ drawdown, contrarian bonus

Individual pillar tests verify each commandment's sub-metrics independently.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.backend.data.fetcher import FinancialData
from src.backend.investors.ackman import AckmanInvestor
from tests.conftest import (
    _make_balance_sheet,
    _make_cashflow,
    _make_history,
    _make_income_stmt,
)

# ─────────────────────────────────────── helpers ──────────────────────────────

def _make_ackman_data(
    *,
    revs: list,
    op_incs: list,
    net_incs: list,
    gps: list,
    ocf: list,
    capex: list,
    ta: list,
    ca: list,
    cl: list,
    tl: list,
    eq: list,
    debt: list,
    shares: list | None = None,
    cash: list | None = None,
    info: dict | None = None,
    prices: list | None = None,
) -> FinancialData:
    """Build a complete FinancialData fixture for Ackman tests."""
    income   = _make_income_stmt(revs, op_incs, net_incs, gps)
    balance  = _make_balance_sheet(ta, ca, cl, tl, eq, debt, shares, cash)
    cashflow = _make_cashflow(ocf, capex)
    px       = prices or ([100] * 2517)
    history  = _make_history(px[:2517])
    default_info = {
        "marketCap": 50e9,
        "enterpriseValue": 55e9,
        "beta": 0.9,
        "sector": "Consumer Cyclical",
        "industry": "Restaurants",
        "country": "United States",
        "heldPercentInsiders": 0.05,
        "heldPercentInstitutions": 0.65,
        "currentRatio": 1.5,
        "longName": "Test Corp",
        "ebitda": 2e9,
        "forwardPE": 20.0,
    }
    if info:
        default_info.update(info)
    return FinancialData(
        ticker="TEST",
        info=default_info,
        income_stmt=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        history=history,
    )


# ─────────────────────────────── archetype fixtures ───────────────────────────

@pytest.fixture
def chipotle_clone() -> FinancialData:
    """Ackman dream business: high FCF, ROIC >25%, dominant, low debt, buybacks."""
    revs    = [12e9, 10e9,  8.5e9,  7e9,  6e9]
    op_incs = [ 3e9,  2.5e9, 2e9,   1.6e9, 1.3e9]
    ni      = [ 2.4e9, 2e9,  1.6e9, 1.2e9, 1e9]
    gps     = [ 5.5e9, 4.6e9, 3.9e9, 3.2e9, 2.8e9]   # ~45% gross margin
    ocf     = [ 3.2e9, 2.7e9, 2.2e9, 1.8e9, 1.5e9]
    capex   = [ 0.5e9, 0.45e9, 0.4e9, 0.35e9, 0.3e9]  # FCF ~26% margin
    ta  = [10e9, 9e9,  8e9,  7e9,  6e9]
    ca  = [ 3e9, 2.8e9, 2.5e9, 2.2e9, 2e9]
    cl  = [ 2e9, 1.8e9, 1.6e9, 1.4e9, 1.2e9]
    tl  = [ 4e9, 3.6e9, 3.2e9, 2.8e9, 2.4e9]
    eq  = [ 6e9, 5.4e9, 4.8e9, 4.2e9, 3.6e9]
    debt = [1e9, 0.9e9, 0.8e9, 0.7e9, 0.6e9]
    sh  = [300e6, 320e6, 340e6, 360e6, 380e6]  # share count declining (buybacks)
    cash = [2e9, 1.8e9, 1.6e9, 1.4e9, 1.2e9]
    return _make_ackman_data(
        revs=revs, op_incs=op_incs, net_incs=ni, gps=gps,
        ocf=ocf, capex=capex,
        ta=ta, ca=ca, cl=cl, tl=tl, eq=eq, debt=debt,
        shares=sh, cash=cash,
        info={
            "marketCap": 60e9,
            "enterpriseValue": 59e9,
            "ebitda": 3.5e9,
            "beta": 0.85,
            "sector": "Consumer Cyclical",
            "industry": "Restaurants",
            "heldPercentInsiders": 0.08,
            "heldPercentInstitutions": 0.70,
            "currentRatio": 1.5,
            "forwardPE": 22.0,
        },
    )


@pytest.fixture
def valeant_warning() -> FinancialData:
    """Valeant-like: high debt, FCF < debt, volatile revenue, poor quality."""
    revs    = [7e9,  9.5e9, 11e9,  8.5e9, 7e9]
    op_incs = [0.5e9, 1e9,   1.2e9, 0.3e9, -0.5e9]
    ni      = [-1e9, -0.5e9,  0.8e9, -2e9,  -3e9]
    gps     = [4.8e9, 6.5e9,  7.5e9,  5.8e9, 4.7e9]
    ocf     = [0.8e9,  1.2e9,  1.5e9, -0.5e9, -1e9]
    capex   = [0.3e9,  0.4e9,  0.4e9,  0.3e9,  0.3e9]
    ta  = [80e9, 82e9, 84e9, 78e9, 70e9]
    ca  = [ 5e9,  6e9,  7e9,  5e9,  4e9]
    cl  = [ 8e9,  9e9, 10e9,  8e9,  7e9]   # current ratio < 1
    tl  = [70e9, 72e9, 74e9, 68e9, 60e9]
    eq  = [10e9, 10e9, 10e9,  10e9, 10e9]
    debt = [60e9, 62e9, 64e9, 58e9, 50e9]  # Debt/FCF >> 5×
    sh  = [400e6, 450e6, 500e6, 550e6, 600e6]  # +50% dilution
    cash = [2e9, 2e9, 2.5e9, 1.5e9, 1e9]
    import math
    prices = [100] * 500 + [int(100 * math.exp(-i / 200)) for i in range(2017)]
    return _make_ackman_data(
        revs=revs, op_incs=op_incs, net_incs=ni, gps=gps,
        ocf=ocf, capex=capex,
        ta=ta, ca=ca, cl=cl, tl=tl, eq=eq, debt=debt,
        shares=sh, cash=cash,
        prices=prices,
        info={
            "marketCap": 15e9,
            "enterpriseValue": 73e9,
            "ebitda": 1.2e9,
            "beta": 2.2,
            "sector": "Healthcare",
            "industry": "Drug Manufacturers—Specialty & Generic",
            "heldPercentInsiders": 0.001,
            "heldPercentInstitutions": 0.55,
            "currentRatio": 0.63,
            "forwardPE": 80.0,
        },
    )


@pytest.fixture
def alphabet_quality() -> FinancialData:
    """Alphabet-like: high FCF, net cash, strong ROIC, wide moat."""
    revs    = [300e9, 280e9, 258e9, 220e9, 183e9]
    op_incs = [ 80e9,  75e9,  70e9,  60e9,  45e9]
    ni      = [ 65e9,  60e9,  55e9,  45e9,  35e9]
    gps     = [170e9, 155e9, 147e9, 125e9, 102e9]   # ~57% gross margin
    ocf     = [ 90e9,  85e9,  80e9,  65e9,  50e9]
    capex   = [ 30e9,  28e9,  24e9,  22e9,  16e9]   # FCF ~20% margin
    ta  = [400e9, 380e9, 360e9, 320e9, 280e9]
    ca  = [160e9, 150e9, 140e9, 120e9, 100e9]
    cl  = [ 60e9,  56e9,  52e9,  45e9,  38e9]
    tl  = [110e9, 100e9,  95e9,  80e9,  65e9]
    eq  = [290e9, 280e9, 265e9, 240e9, 215e9]
    debt = [15e9, 14e9, 13e9, 12e9, 11e9]
    sh  = [12.5e9, 12.8e9, 13.1e9, 13.5e9, 13.9e9]  # buybacks
    cash = [110e9, 100e9, 90e9, 80e9, 70e9]
    return _make_ackman_data(
        revs=revs, op_incs=op_incs, net_incs=ni, gps=gps,
        ocf=ocf, capex=capex,
        ta=ta, ca=ca, cl=cl, tl=tl, eq=eq, debt=debt,
        shares=sh, cash=cash,
        info={
            "marketCap": 2_000e9,
            "enterpriseValue": 1_905e9,
            "ebitda": 100e9,
            "beta": 1.05,
            "sector": "Communication Services",
            "industry": "Internet Content & Information",
            "heldPercentInsiders": 0.012,
            "heldPercentInstitutions": 0.68,
            "currentRatio": 2.7,
            "forwardPE": 20.0,
        },
    )


# ─────────────────────────────────── basic sanity ─────────────────────────────

def test_ackman_name():
    assert AckmanInvestor().name == "Ackman"


def test_ackman_rules_count_is_8(chipotle_clone):
    inv    = AckmanInvestor()
    result = inv.score(chipotle_clone)
    total_rules = len(result.rules_passed) + len(result.rules_failed)
    assert total_rules == 8


def test_ackman_total_score_bounded_0_100(chipotle_clone, valeant_warning):
    inv = AckmanInvestor()
    for data in [chipotle_clone, valeant_warning]:
        result = inv.score(data)
        assert 0.0 <= result.total_score <= 100.0


def test_ackman_verdict_is_valid(chipotle_clone):
    result = AckmanInvestor().score(chipotle_clone)
    assert result.verdict in ("Strong Buy", "Buy", "Hold", "Avoid")


def test_ackman_empty_data_no_crash(empty_data):
    result = AckmanInvestor().score(empty_data)
    assert result.total_score >= 0.0
    assert result.investor == "Ackman"


# ─────────────────────────────── archetype scoring ────────────────────────────

def test_ackman_chipotle_clone_scores_high(chipotle_clone):
    """Ideal Ackman business should score 70+ (all 8 commandments met)."""
    result = AckmanInvestor().score(chipotle_clone)
    assert result.total_score >= 70, f"Expected ≥70, got {result.total_score:.1f}"


def test_ackman_valeant_scores_low(valeant_warning):
    """Valeant-like business should score <40 (violates multiple commandments)."""
    result = AckmanInvestor().score(valeant_warning)
    assert result.total_score < 45, f"Expected <45, got {result.total_score:.1f}"


def test_ackman_alphabet_quality_scores_mid_high(alphabet_quality):
    """Alphabet-like should score 60-90 (quality but expensive)."""
    result = AckmanInvestor().score(alphabet_quality)
    assert 55 <= result.total_score <= 95, f"Expected 55-95, got {result.total_score:.1f}"


def test_ackman_chipotle_beats_valeant(chipotle_clone, valeant_warning):
    inv = AckmanInvestor()
    good = inv.score(chipotle_clone).total_score
    bad  = inv.score(valeant_warning).total_score
    assert good > bad


# ─────────────────────────────── bonus / penalty ──────────────────────────────

def test_ackman_negative_fcf_penalty():
    """Company with negative TTM FCF should lose 10 pts from penalty."""
    # Build two versions — identical except one has negative FCF in TTM
    base_kwargs = dict(
        revs=[10e9] * 5, op_incs=[2e9] * 5, net_incs=[1.5e9] * 5, gps=[5e9] * 5,
        ta=[20e9] * 5, ca=[6e9] * 5, cl=[3e9] * 5, tl=[10e9] * 5,
        eq=[10e9] * 5, debt=[2e9] * 5,
        info={"marketCap": 30e9, "enterpriseValue": 32e9, "ebitda": 3e9,
              "beta": 0.9, "sector": "Consumer Defensive", "industry": "Grocery Stores",
              "heldPercentInsiders": 0.05, "heldPercentInstitutions": 0.60,
              "currentRatio": 2.0},
    )
    inv = AckmanInvestor()

    # Positive FCF
    data_good = _make_ackman_data(ocf=[2e9] * 5, capex=[0.5e9] * 5, **base_kwargs)
    score_good = inv.score(data_good).total_score

    # Negative TTM FCF — conftest stores newest first, so index 0 = 2023 (TTM)
    data_bad = _make_ackman_data(
        ocf=[0.2e9, 2e9, 2e9, 2e9, 2e9],   # 2023 (newest) has very low OCF
        capex=[0.5e9, 0.5e9, 0.5e9, 0.5e9, 0.5e9],
        **base_kwargs,
    )
    score_bad = inv.score(data_bad).total_score

    assert score_good > score_bad


def test_ackman_negative_fcf_flag_in_red_flags():
    """Negative FCF penalty should appear in red_flags."""
    data = _make_ackman_data(
        revs=[10e9] * 5, op_incs=[2e9] * 5, net_incs=[1.5e9] * 5, gps=[5e9] * 5,
        ocf=[0.1e9, 2e9, 2e9, 2e9, 2e9],   # 2023 (newest, index 0) TTM FCF = 0.1 - 0.5 = -0.4B
        capex=[0.5e9] * 5,
        ta=[20e9] * 5, ca=[6e9] * 5, cl=[3e9] * 5,
        tl=[10e9] * 5, eq=[10e9] * 5, debt=[2e9] * 5,
    )
    result = AckmanInvestor().score(data)
    penalty_flags = [f for f in result.red_flags if "PENALTY" in f and "cash flow" in f.lower()]
    assert penalty_flags, "Expected a negative FCF penalty flag"


def test_ackman_trifecta_bonus():
    """FCF>20% + ROIC>20% + Debt/FCF<2× triggers +5 trifecta bonus."""
    # Build a company that clearly hits the trifecta
    # FCF margin: OCF 2.8B - capex 0.2B = 2.6B / 10B rev = 26%  ✓ >20%
    # ROIC: NOPAT 1.5B / IC(eq=4+max(0,debt=2-cash=1)=5B) = 30%  ✓ >20%
    # Debt/FCF: 2B / 2.6B = 0.77×  ✓ <2×
    data = _make_ackman_data(
        revs=[10e9] * 5, op_incs=[2e9] * 5, net_incs=[1.5e9] * 5, gps=[6e9] * 5,
        ocf=[2.8e9] * 5, capex=[0.2e9] * 5,
        ta=[10e9] * 5, ca=[3e9] * 5, cl=[1e9] * 5,
        tl=[6e9]  * 5, eq=[4e9]  * 5, debt=[2e9] * 5,
        cash=[1e9] * 5,
        info={
            "marketCap": 60e9,
            "enterpriseValue": 63e9,
            "ebitda": 2.5e9,
            "beta": 0.85,
            "sector": "Consumer Defensive",
            "heldPercentInsiders": 0.08,
            "heldPercentInstitutions": 0.65,
            "currentRatio": 2.0,
        },
    )
    result = AckmanInvestor().score(data)
    trifecta_flags = [f for f in result.red_flags if "trifecta" in f.lower()]
    assert trifecta_flags, "Expected trifecta bonus flag"


def test_ackman_contrarian_bonus():
    """Stock down >30% in 12 months triggers +3 contrarian bonus."""
    # Price falls 40% in trailing year
    prices = [100] * 1265 + [100, 95, 90, 85, 80, 75, 70, 65, 60] * 28 + [60] * 1
    prices = prices[:2517]
    data = _make_ackman_data(
        revs=[10e9] * 5, op_incs=[2e9] * 5, net_incs=[1.5e9] * 5, gps=[5e9] * 5,
        ocf=[2e9] * 5, capex=[0.5e9] * 5,
        ta=[20e9] * 5, ca=[6e9] * 5, cl=[3e9] * 5,
        tl=[10e9] * 5, eq=[10e9] * 5, debt=[3e9] * 5,
        prices=prices,
    )
    result = AckmanInvestor().score(data)
    contrarian_flags = [f for f in result.red_flags if "Contrarian" in f or "contrarian" in f]
    assert contrarian_flags, "Expected contrarian bonus flag"


def test_ackman_high_leverage_penalty():
    """Debt/FCF > 5× should trigger -8 penalty."""
    # Avg FCF = 0.5B/yr, Debt = 30B → Debt/FCF = 60×
    data = _make_ackman_data(
        revs=[10e9] * 5, op_incs=[1e9] * 5, net_incs=[0.5e9] * 5, gps=[4e9] * 5,
        ocf=[0.8e9] * 5, capex=[0.3e9] * 5,
        ta=[50e9] * 5, ca=[5e9] * 5, cl=[4e9] * 5,
        tl=[40e9] * 5, eq=[10e9] * 5, debt=[30e9] * 5,
    )
    result = AckmanInvestor().score(data)
    leverage_flags = [f for f in result.red_flags if "PENALTY" in f and "Debt/FCF" in f]
    assert leverage_flags, "Expected high leverage penalty flag"


def test_ackman_dilution_penalty():
    """Share count growing >10% over 5yr triggers -5 dilution penalty."""
    # Shares grow from 200M to 240M = +20%
    # shares list is newest→oldest: [240M, 230M, 220M, 210M, 200M]
    sh = [240e6, 230e6, 220e6, 210e6, 200e6]
    data = _make_ackman_data(
        revs=[10e9] * 5, op_incs=[2e9] * 5, net_incs=[1.5e9] * 5, gps=[5e9] * 5,
        ocf=[2e9] * 5, capex=[0.5e9] * 5,
        ta=[20e9] * 5, ca=[6e9] * 5, cl=[3e9] * 5,
        tl=[10e9] * 5, eq=[10e9] * 5, debt=[2e9] * 5,
        shares=sh,
    )
    result = AckmanInvestor().score(data)
    dilution_flags = [f for f in result.red_flags if "PENALTY" in f and "dilution" in f.lower()]
    assert dilution_flags, "Expected dilution penalty flag"


def test_ackman_roic_below_wacc_penalty():
    """ROIC consistently below 8% triggers -5 value-destroyer penalty."""
    # Tiny equity + large debt → very small IC → but let's use explicit low-return data
    # Op income 3% of large asset base → ROIC ~3%
    revs    = [50e9] * 5
    op_incs = [ 1.5e9] * 5   # 3% op margin
    ni      = [ 1e9] * 5
    gps     = [10e9] * 5
    ta  = [80e9] * 5; ca  = [10e9] * 5; cl  = [8e9] * 5
    tl  = [50e9] * 5; eq  = [30e9] * 5; debt = [20e9] * 5
    data = _make_ackman_data(
        revs=revs, op_incs=op_incs, net_incs=ni, gps=gps,
        ocf=[2e9] * 5, capex=[1.5e9] * 5,
        ta=ta, ca=ca, cl=cl, tl=tl, eq=eq, debt=debt,
    )
    result = AckmanInvestor().score(data)
    wacc_flags = [f for f in result.red_flags if "PENALTY" in f and "ROIC" in f]
    assert wacc_flags, "Expected ROIC-below-WACC penalty flag"


# ─────────────────────────────── pillar-level tests ───────────────────────────

def test_pillar_simple_low_cov_passes(chipotle_clone):
    """Stable revenue / earnings should pass Commandment 1."""
    result = AckmanInvestor().score(chipotle_clone)
    p1 = next(r for r in result.rules_passed + result.rules_failed
               if "Simple" in r.name)
    assert p1.value >= 6.0, f"Expected pillar 1 ≥6.0, got {p1.value}"


def test_pillar_fcf_high_margin_scores_high(chipotle_clone):
    """High FCF margin business should pass Commandment 2."""
    result = AckmanInvestor().score(chipotle_clone)
    p2 = next(r for r in result.rules_passed + result.rules_failed
               if "Free Cash Flow" in r.name)
    assert p2.value >= 6.0, f"Expected pillar 2 ≥6.0, got {p2.value}"


def test_pillar_fcf_high_margin_scores_max(alphabet_quality):
    """Alphabet-like should get high FCF pillar score."""
    result = AckmanInvestor().score(alphabet_quality)
    p2 = next(r for r in result.rules_passed + result.rules_failed
               if "Free Cash Flow" in r.name)
    assert p2.value >= 6.5, f"Expected pillar 2 ≥6.5, got {p2.value}"


def test_pillar_dominant_high_market_cap_scores_high(alphabet_quality):
    """Very large cap + high gross margin should pass Commandment 3."""
    result = AckmanInvestor().score(alphabet_quality)
    p3 = next(r for r in result.rules_passed + result.rules_failed
               if "Dominant" in r.name)
    assert p3.value >= 7.0, f"Expected pillar 3 ≥7.0, got {p3.value}"


def test_pillar_roc_high_roic_scores_high(chipotle_clone):
    """High ROIC business should pass Commandment 5."""
    result = AckmanInvestor().score(chipotle_clone)
    p5 = next(r for r in result.rules_passed + result.rules_failed
               if "Return on Capital" in r.name)
    assert p5.value >= 6.0, f"Expected pillar 5 ≥6.0, got {p5.value}"


def test_pillar_extrinsic_low_beta_stable_sector():
    """Low-beta defensive sector should score well on Commandment 6."""
    data = _make_ackman_data(
        revs=[5e9] * 5, op_incs=[1e9] * 5, net_incs=[0.8e9] * 5, gps=[2e9] * 5,
        ocf=[1.2e9] * 5, capex=[0.2e9] * 5,
        ta=[8e9] * 5, ca=[3e9] * 5, cl=[1e9] * 5,
        tl=[3e9] * 5, eq=[5e9] * 5, debt=[1e9] * 5,
        info={
            "marketCap": 20e9,
            "beta": 0.6,
            "sector": "Consumer Defensive",
            "industry": "Grocery Stores",
            "country": "United States",
        },
    )
    result = AckmanInvestor().score(data)
    p6 = next(r for r in result.rules_passed + result.rules_failed
               if "Extrinsic" in r.name)
    assert p6.value >= 7.0, f"Expected pillar 6 ≥7.0, got {p6.value}"


def test_pillar_balance_low_debt_scores_high(alphabet_quality):
    """Net-cash company should pass Commandment 7."""
    result = AckmanInvestor().score(alphabet_quality)
    p7 = next(r for r in result.rules_passed + result.rules_failed
               if "Balance Sheet" in r.name)
    assert p7.value >= 6.0, f"Expected pillar 7 ≥6.0, got {p7.value}"


def test_pillar_balance_high_debt_scores_low(valeant_warning):
    """Very high leverage should fail Commandment 7."""
    result = AckmanInvestor().score(valeant_warning)
    p7 = next(r for r in result.rules_passed + result.rules_failed
               if "Balance Sheet" in r.name)
    assert p7.value < 5.0, f"Expected pillar 7 <5.0, got {p7.value}"


def test_pillar_mgmt_high_insider_scores_high():
    """High insider ownership + institutional ownership should pass Commandment 8."""
    data = _make_ackman_data(
        revs=[10e9] * 5, op_incs=[2e9] * 5, net_incs=[1.5e9] * 5, gps=[5e9] * 5,
        ocf=[2.5e9] * 5, capex=[0.5e9] * 5,
        ta=[15e9] * 5, ca=[5e9] * 5, cl=[2e9] * 5,
        tl=[7e9]  * 5, eq=[8e9]  * 5, debt=[2e9] * 5,
        info={
            "heldPercentInsiders": 0.15,        # 15% — founder-led
            "heldPercentInstitutions": 0.60,
            "payoutRatio": 0.35,
            "marketCap": 40e9,
        },
    )
    result = AckmanInvestor().score(data)
    p8 = next(r for r in result.rules_passed + result.rules_failed
               if "Management" in r.name)
    assert p8.value >= 6.0, f"Expected pillar 8 ≥6.0, got {p8.value}"


# ─────────────────────────────── proportional scoring ─────────────────────────

def test_all_pillar_points_sum_to_100_max():
    """Total possible points across all 8 pillars must equal 100."""
    inv = AckmanInvestor()
    total_possible = sum(inv._PILLAR_WEIGHTS.values())
    assert total_possible == 100


def test_pillar_rule_points_awarded_proportional(chipotle_clone):
    """points_awarded should equal pillar_score/10 × points_possible."""
    result = AckmanInvestor().score(chipotle_clone)
    for rule in result.rules_passed + result.rules_failed:
        expected = (rule.value / 10.0) * rule.points_possible
        assert abs(rule.points_awarded - expected) < 0.01, (
            f"{rule.name}: expected {expected:.2f}, got {rule.points_awarded:.2f}"
        )


def test_pillar_threshold_is_6(chipotle_clone):
    """All pillar rules should have threshold = 6.0 (60% of pillar max)."""
    result = AckmanInvestor().score(chipotle_clone)
    for rule in result.rules_passed + result.rules_failed:
        assert rule.threshold == 6.0


# ─────────────────────────────── existing fixtures ────────────────────────────

def test_ackman_high_quality_fixture_scores_above_low_quality(
    high_quality_data, low_quality_data
):
    inv = AckmanInvestor()
    good = inv.score(high_quality_data).total_score
    bad  = inv.score(low_quality_data).total_score
    assert good > bad, f"Expected high_quality ({good:.1f}) > low_quality ({bad:.1f})"


def test_ackman_valuation_flag_appears(chipotle_clone):
    """Valuation overlay flag should appear when EV and FCF are available."""
    result = AckmanInvestor().score(chipotle_clone)
    val_flags = [f for f in result.red_flags if "VALUATION" in f]
    assert val_flags, "Expected a VALUATION: flag in red_flags"
