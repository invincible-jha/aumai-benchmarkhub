"""Core runner, builder, and scoring logic for aumai-benchmarkhub."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

from aumai_benchmarkhub.models import (
    BenchmarkCase,
    BenchmarkCategory,
    BenchmarkReport,
    BenchmarkScore,
    BenchmarkSuite,
)

# ---------------------------------------------------------------------------
# Difficulty weights used by ScoreCalculator
# ---------------------------------------------------------------------------

_DIFFICULTY_WEIGHTS: dict[str, float] = {
    "easy": 1.0,
    "medium": 1.5,
    "hard": 2.0,
}

# ---------------------------------------------------------------------------
# ScoreCalculator
# ---------------------------------------------------------------------------


class ScoreCalculator:
    """Compute weighted scores from a list of BenchmarkScore objects."""

    def overall(
        self,
        scores: list[BenchmarkScore],
        cases: list[BenchmarkCase],
    ) -> float:
        """Return overall weighted score in [0, 1].

        Cases are weighted by difficulty; harder cases count more.
        """
        if not scores:
            return 0.0

        case_map = {c.case_id: c for c in cases}
        total_weight = 0.0
        weighted_sum = 0.0

        for bench_score in scores:
            case = case_map.get(bench_score.case_id)
            weight = _DIFFICULTY_WEIGHTS.get(case.difficulty if case else "medium", 1.5)
            weighted_sum += bench_score.score * weight
            total_weight += weight

        return round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    def by_category(
        self,
        scores: list[BenchmarkScore],
        cases: list[BenchmarkCase],
    ) -> dict[str, float]:
        """Return per-category weighted scores."""
        case_map = {c.case_id: c for c in cases}
        category_data: dict[str, tuple[float, float]] = {}  # category -> (weighted_sum, total_weight)

        for bench_score in scores:
            case = case_map.get(bench_score.case_id)
            if case is None:
                continue
            cat = case.category.value
            weight = _DIFFICULTY_WEIGHTS.get(case.difficulty, 1.5)
            prev_sum, prev_weight = category_data.get(cat, (0.0, 0.0))
            category_data[cat] = (
                prev_sum + bench_score.score * weight,
                prev_weight + weight,
            )

        return {
            cat: round(weighted_sum / total_weight, 4)
            for cat, (weighted_sum, total_weight) in category_data.items()
            if total_weight > 0
        }


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------


def _evaluate_output(case: BenchmarkCase, agent_output: str) -> tuple[bool, float, dict[str, object]]:
    """Score an agent's output against the case's expected_behavior.

    expected_behavior keys supported:
      - contains (list[str]):  output must contain all listed substrings.
      - not_contains (list[str]): output must not contain any listed substrings.
      - regex (str): output must match the regex pattern.
      - min_length (int): output must be at least this many characters.
      - max_length (int): output must be at most this many characters.
      - json_valid (bool): if True, output must be valid JSON.
    """
    details: dict[str, object] = {}
    checks_passed = 0
    checks_total = 0

    expected = case.expected_behavior
    output_lower = agent_output.lower()

    # contains check
    if "contains" in expected:
        required: list[str] = list(expected["contains"])  # type: ignore[arg-type]
        checks_total += len(required)
        for token in required:
            if token.lower() in output_lower:
                checks_passed += 1
            else:
                details.setdefault("missing_tokens", [])
                missing: list[str] = details["missing_tokens"]  # type: ignore[assignment]
                missing.append(token)

    # not_contains check
    if "not_contains" in expected:
        forbidden: list[str] = list(expected["not_contains"])  # type: ignore[arg-type]
        checks_total += len(forbidden)
        for token in forbidden:
            if token.lower() not in output_lower:
                checks_passed += 1
            else:
                details.setdefault("forbidden_found", [])
                found: list[str] = details["forbidden_found"]  # type: ignore[assignment]
                found.append(token)

    # regex check
    if "regex" in expected:
        pattern = str(expected["regex"])
        checks_total += 1
        if re.search(pattern, agent_output, re.IGNORECASE | re.DOTALL):
            checks_passed += 1
        else:
            details["regex_failed"] = pattern

    # min_length check
    if "min_length" in expected:
        min_len = int(expected["min_length"])  # type: ignore[arg-type]
        checks_total += 1
        if len(agent_output) >= min_len:
            checks_passed += 1
        else:
            details["too_short"] = len(agent_output)

    # max_length check
    if "max_length" in expected:
        max_len = int(expected["max_length"])  # type: ignore[arg-type]
        checks_total += 1
        if len(agent_output) <= max_len:
            checks_passed += 1
        else:
            details["too_long"] = len(agent_output)

    # json_valid check
    if expected.get("json_valid"):
        checks_total += 1
        try:
            json.loads(agent_output)
            checks_passed += 1
        except json.JSONDecodeError as exc:
            details["json_error"] = str(exc)

    # If no structured checks are defined, fall back to a naive non-empty check.
    if checks_total == 0:
        checks_total = 1
        checks_passed = 1 if agent_output.strip() else 0

    score = checks_passed / checks_total
    passed = score >= 1.0
    return passed, round(score, 4), details


class BenchmarkRunner:
    """Load suites, run cases, and produce reports."""

    def __init__(self, calculator: ScoreCalculator | None = None) -> None:
        self._calculator = calculator or ScoreCalculator()

    def load_suite(self, path: str) -> BenchmarkSuite:
        """Deserialise a BenchmarkSuite from a JSON file."""
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
        return BenchmarkSuite.model_validate(data)

    def run_case(
        self,
        case: BenchmarkCase,
        agent_output: str,
    ) -> BenchmarkScore:
        """Evaluate a single case and return a BenchmarkScore."""
        t_start = time.perf_counter()
        passed, score, details = _evaluate_output(case, agent_output)
        latency_ms = (time.perf_counter() - t_start) * 1000
        return BenchmarkScore(
            case_id=case.case_id,
            passed=passed,
            score=score,
            details=details,
            latency_ms=round(latency_ms, 3),
        )

    def run_suite(
        self,
        suite: BenchmarkSuite,
        agent_outputs: dict[str, str],
    ) -> BenchmarkReport:
        """Evaluate all cases in *suite* using *agent_outputs*.

        Args:
            suite:          The benchmark suite to evaluate.
            agent_outputs:  Mapping of case_id -> agent response string.

        Returns:
            A BenchmarkReport with per-case scores and aggregates.
        """
        scores: list[BenchmarkScore] = []
        for case in suite.cases:
            output = agent_outputs.get(case.case_id, "")
            bench_score = self.run_case(case, output)
            scores.append(bench_score)

        overall = self._calculator.overall(scores, suite.cases)
        category_scores = self._calculator.by_category(scores, suite.cases)

        return BenchmarkReport(
            suite=suite,
            scores=scores,
            overall_score=overall,
            by_category=category_scores,
        )


# ---------------------------------------------------------------------------
# SuiteBuilder
# ---------------------------------------------------------------------------


class SuiteBuilder:
    """Fluent builder for BenchmarkSuite objects."""

    def create_suite(self, name: str, version: str = "1.0.0") -> BenchmarkSuite:
        """Create a new, empty BenchmarkSuite with a generated ID."""
        return BenchmarkSuite(
            suite_id=str(uuid.uuid4()),
            name=name,
            version=version,
            cases=[],
        )

    def add_case(
        self,
        suite: BenchmarkSuite,
        case: BenchmarkCase,
    ) -> None:
        """Append *case* to *suite* in-place."""
        suite.cases.append(case)

    def save_suite(self, suite: BenchmarkSuite, path: str) -> None:
        """Serialise *suite* to a JSON file at *path*."""
        Path(path).write_text(
            suite.model_dump_json(indent=2),
            encoding="utf-8",
        )


__all__ = [
    "ScoreCalculator",
    "BenchmarkRunner",
    "SuiteBuilder",
]
