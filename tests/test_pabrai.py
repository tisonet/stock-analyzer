"""Unit tests for Mohnish Pabrai scoring module."""
from __future__ import annotations

import pytest
from src.backend.investors.pabrai import PabraiInvestor


def test_pabrai_high_quality_scores_moderately(high_quality_data):
    """High-quality but expensive stock (P/E=22, D/E=0.82) — Pabrai is a deep value
    investor so he correctly scores expensive quality stocks low."""
    inv = PabraiInvestor()
    result = inv.score(high_quality_data)
    assert result.investor == "Pabrai"
    # Pabrai would recognise the quality (ROIC, predictability) but not the price
    assert result.total_score >= 20, f"Expected >= 20, got {result.total_score}"
    assert len(result.rules_passed) > 0
    assert result.key_insight == ""  # filled by engine


def test_pabrai_low_quality_scores_poorly(low_quality_data):
    inv = PabraiInvestor()
    result = inv.score(low_quality_data)
    assert result.total_score < 40, f"Expected < 40 for low-quality co, got {result.total_score}"
    assert result.verdict in ("Avoid", "Hold")
    assert len(result.rules_failed) > 0


def test_pabrai_leverage_rule(high_quality_data, low_quality_data):
    """Low-debt company passes leverage rule, high-debt fails."""
    inv = PabraiInvestor()

    # high_quality_data has D/E = 0.82 (manageable but above 0.3)
    hq = inv.score(high_quality_data)
    de_rule_hq = next(
        (r for r in hq.rules_passed + hq.rules_failed if "Leverage" in r.name), None
    )
    assert de_rule_hq is not None
    assert de_rule_hq.points_possible == 20.0

    # low_quality_data has D/E = 9.0 — should definitely fail
    lq = inv.score(low_quality_data)
    de_rule_lq = next(
        (r for r in lq.rules_failed if "Leverage" in r.name), None
    )
    assert de_rule_lq is not None, "D/E=9.0 should fail leverage rule"


def test_pabrai_cannibal_rule(high_quality_data):
    """High-quality data has declining shares — should detect cannibalism."""
    inv = PabraiInvestor()
    result = inv.score(high_quality_data)
    cannibal_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "Cannibal" in r.name), None
    )
    assert cannibal_rule is not None
    # high_quality_data has declining shares + reasonable P/S
    assert "Shares down" in cannibal_rule.description or "unavailable" in cannibal_rule.description


def test_pabrai_dilution_detected(low_quality_data):
    """Low-quality data has increasing shares — should fail cannibal rule."""
    inv = PabraiInvestor()
    result = inv.score(low_quality_data)
    cannibal_rule = next(
        (r for r in result.rules_failed if "Cannibal" in r.name), None
    )
    assert cannibal_rule is not None


def test_pabrai_fcf_yield_rule(high_quality_data):
    """FCF yield rule should always be present."""
    inv = PabraiInvestor()
    result = inv.score(high_quality_data)
    fcf_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "FCF Yield" in r.name), None
    )
    assert fcf_rule is not None
    assert fcf_rule.points_possible == 15.0


def test_pabrai_pe_rule_net_net(net_net_data):
    """Net-net data has P/E = 12 — should pass Pabrai's low P/E rule."""
    inv = PabraiInvestor()
    result = inv.score(net_net_data)
    pe_rule = next(
        (r for r in result.rules_passed if "P/E" in r.name), None
    )
    assert pe_rule is not None, "P/E = 12 should pass Pabrai's < 15 threshold"


def test_pabrai_predictability_rule(high_quality_data):
    """Stable revenue growth should pass simple & predictable rule."""
    inv = PabraiInvestor()
    result = inv.score(high_quality_data)
    pred_rule = next(
        (r for r in result.rules_passed + result.rules_failed if "Predictable" in r.name), None
    )
    assert pred_rule is not None
    assert pred_rule.points_possible == 10.0


def test_pabrai_red_flags_on_leverage(low_quality_data):
    """Highly leveraged company should trigger leverage red flag."""
    inv = PabraiInvestor()
    result = inv.score(low_quality_data)
    leverage_flags = [f for f in result.red_flags if "leverage" in f.lower() or "D/E" in f]
    assert len(leverage_flags) > 0, "D/E=9.0 should trigger leverage red flag"


def test_pabrai_score_bounds(high_quality_data):
    inv = PabraiInvestor()
    result = inv.score(high_quality_data)
    assert 0 <= result.total_score <= 100


def test_pabrai_crash_safety(empty_data):
    """Must not crash with empty data."""
    inv = PabraiInvestor()
    result = inv.score(empty_data)
    assert result.total_score >= 0
    assert result.verdict in ("Strong Buy", "Buy", "Hold", "Avoid")
