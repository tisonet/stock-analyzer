"""Tests for historical ratios computation."""
from __future__ import annotations

import pandas as pd
import pytest

from src.backend.data.ratios import compute_historical_ratios


def test_ratios_high_quality(high_quality_data):
    """High-quality company should produce valid ratios for all years."""
    result = compute_historical_ratios(high_quality_data)
    assert result["ticker"] == "HQCO"
    assert len(result["years"]) > 0

    # Years should be sorted oldest → newest
    years_list = [y["year"] for y in result["years"]]
    assert years_list == sorted(years_list)

    # Check that each year has the expected keys
    for entry in result["years"]:
        for key in ("year", "pe", "ps", "fcf_yield", "gross_margin",
                     "net_margin", "fcf_per_share", "eps", "revenue_per_share"):
            assert key in entry

    # Gross margin should be between 0 and 1 for this company
    for entry in result["years"]:
        if entry["gross_margin"] is not None:
            assert 0 < entry["gross_margin"] < 1

    # Net margin should be positive for high-quality company
    for entry in result["years"]:
        if entry["net_margin"] is not None:
            assert entry["net_margin"] > 0


def test_ratios_low_quality(low_quality_data):
    """Low-quality company should still produce results (some may be None)."""
    result = compute_historical_ratios(low_quality_data)
    assert result["ticker"] == "LQCO"
    assert len(result["years"]) > 0

    # Should have gross margin even for a low-quality company
    gm_values = [y["gross_margin"] for y in result["years"] if y["gross_margin"] is not None]
    assert len(gm_values) > 0


def test_ratios_empty_data(empty_data):
    """Empty data should not crash and should return empty years list."""
    result = compute_historical_ratios(empty_data)
    assert result["ticker"] == "EMPTY"
    assert result["years"] == []


def test_ratios_pe_positive_eps(high_quality_data):
    """P/E should be positive when EPS is positive."""
    result = compute_historical_ratios(high_quality_data)
    for entry in result["years"]:
        if entry["eps"] is not None and entry["eps"] > 0 and entry["pe"] is not None:
            assert entry["pe"] > 0


def test_ratios_fcf_yield(high_quality_data):
    """FCF yield should be present for years with cash flow data."""
    result = compute_historical_ratios(high_quality_data)
    fcf_yields = [y["fcf_yield"] for y in result["years"] if y["fcf_yield"] is not None]
    assert len(fcf_yields) > 0
    # For high-quality company, FCF yield should be positive
    for fy in fcf_yields:
        assert fy > 0


def test_ratios_margins_no_price_needed(high_quality_data):
    """Gross Margin and Net Margin should work even without history."""
    high_quality_data.history = pd.DataFrame()
    result = compute_historical_ratios(high_quality_data)
    assert len(result["years"]) > 0

    gm_values = [y["gross_margin"] for y in result["years"] if y["gross_margin"] is not None]
    nm_values = [y["net_margin"] for y in result["years"] if y["net_margin"] is not None]
    assert len(gm_values) > 0
    assert len(nm_values) > 0

    # Price-dependent ratios should be None
    for entry in result["years"]:
        assert entry["pe"] is None
        assert entry["ps"] is None
        assert entry["fcf_yield"] is None


def test_ratios_net_net(net_net_data):
    """Net-net company should produce valid ratios."""
    result = compute_historical_ratios(net_net_data)
    assert result["ticker"] == "NNET"
    assert len(result["years"]) > 0

    # P/E should be reasonable for a value company
    pe_values = [y["pe"] for y in result["years"] if y["pe"] is not None]
    assert len(pe_values) > 0
