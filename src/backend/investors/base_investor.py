"""
Base classes and shared data models for all investor scoring modules.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.data.fetcher import FinancialData

from src.backend.config import VERDICT_STRONG_BUY, VERDICT_BUY, VERDICT_HOLD


@dataclass
class Rule:
    """A single scoring rule with its result and metadata."""
    name: str
    passed: bool
    value: Optional[float]       # None = data not available
    threshold: float
    points_awarded: float
    points_possible: float
    description: str
    source: str                  # book/quote/letter reference


@dataclass
class InvestorScore:
    """Complete scoring result for one investor."""
    investor: str
    total_score: float           # 0–100
    verdict: str                 # "Strong Buy" | "Buy" | "Hold" | "Avoid"
    rules_passed: list[Rule]
    rules_failed: list[Rule]
    key_insight: str             # Claude-generated 2-sentence summary
    red_flags: list[str]

    def to_dict(self) -> dict:
        return {
            "investor": self.investor,
            "total_score": round(self.total_score, 1),
            "verdict": self.verdict,
            "rules_passed": [_rule_to_dict(r) for r in self.rules_passed],
            "rules_failed": [_rule_to_dict(r) for r in self.rules_failed],
            "key_insight": self.key_insight,
            "red_flags": self.red_flags,
        }


@dataclass
class ConsensusScore:
    """Aggregated verdict from all 6 investors."""
    ticker: str
    weighted_avg: float
    agreement_level: str         # "High Conviction" | "Mixed" | "Divided"
    investor_scores: list[InvestorScore]
    overall_narrative: str       # Claude-generated paragraph

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "weighted_avg": round(self.weighted_avg, 1),
            "agreement_level": self.agreement_level,
            "investor_scores": [s.to_dict() for s in self.investor_scores],
            "overall_narrative": self.overall_narrative,
        }


def _rule_to_dict(r: Rule) -> dict:
    return {
        "name": r.name,
        "passed": r.passed,
        "value": round(r.value, 4) if r.value is not None else None,
        "threshold": r.threshold,
        "points_awarded": r.points_awarded,
        "points_possible": r.points_possible,
        "description": r.description,
        "source": r.source,
    }


class BaseInvestor(ABC):
    """Abstract base class for all investor scoring modules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Investor name used in output."""
        ...

    @abstractmethod
    def score(self, data: "FinancialData") -> InvestorScore:
        """Compute score for the given financial data."""
        ...

    # ------------------------------------------------------------------ helpers

    def _safe(self, value, default=None):
        """Return value if truthy/not-nan, else default."""
        import math
        if value is None:
            return default
        try:
            if math.isnan(float(value)):
                return default
        except (TypeError, ValueError):
            return default
        return value

    def _verdict(self, score: float) -> str:
        if score >= VERDICT_STRONG_BUY:
            return "Strong Buy"
        if score >= VERDICT_BUY:
            return "Buy"
        if score >= VERDICT_HOLD:
            return "Hold"
        return "Avoid"

    def _make_rule(
        self,
        name: str,
        value: Optional[float],
        threshold: float,
        points_possible: float,
        description: str,
        source: str,
        passed: Optional[bool] = None,
        partial: float = 1.0,     # fraction of points if passed
    ) -> Rule:
        """
        Build a Rule. If value is None → unavailable (failed, 0 pts).
        If passed is None it is determined by value >= threshold for positive
        rules (caller can override with explicit passed=True/False).
        """
        if value is None:
            return Rule(
                name=name,
                passed=False,
                value=None,
                threshold=threshold,
                points_awarded=0.0,
                points_possible=points_possible,
                description="Data unavailable",
                source=source,
            )
        if passed is None:
            passed = value >= threshold
        pts = points_possible * partial if passed else 0.0
        return Rule(
            name=name,
            passed=passed,
            value=value,
            threshold=threshold,
            points_awarded=pts,
            points_possible=points_possible,
            description=description,
            source=source,
        )

    def _build_result(self, rules: list[Rule], red_flags: list[str]) -> InvestorScore:
        total = sum(r.points_awarded for r in rules)
        passed = [r for r in rules if r.passed]
        failed = [r for r in rules if not r.passed]
        return InvestorScore(
            investor=self.name,
            total_score=min(100.0, total),
            verdict=self._verdict(total),
            rules_passed=passed,
            rules_failed=failed,
            key_insight="",  # filled in by engine after Claude call
            red_flags=red_flags,
        )
