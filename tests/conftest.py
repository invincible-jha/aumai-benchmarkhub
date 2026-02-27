"""Shared test fixtures for aumai-benchmarkhub."""
from __future__ import annotations

import uuid

import pytest

from aumai_benchmarkhub.core import BenchmarkRunner, ScoreCalculator, SuiteBuilder
from aumai_benchmarkhub.models import (
    BenchmarkCase,
    BenchmarkCategory,
    BenchmarkScore,
    BenchmarkSuite,
)


def make_case(
    case_id: str = "test-001",
    category: BenchmarkCategory = BenchmarkCategory.reasoning,
    prompt: str = "What is 2 + 2?",
    expected_behavior: dict | None = None,
    difficulty: str = "easy",
    tags: list[str] | None = None,
) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=case_id,
        category=category,
        prompt=prompt,
        expected_behavior=expected_behavior if expected_behavior is not None else {"contains": ["4"]},
        difficulty=difficulty,
        tags=tags or [],
    )


def make_score(
    case_id: str = "test-001",
    passed: bool = True,
    score: float = 1.0,
    details: dict | None = None,
) -> BenchmarkScore:
    return BenchmarkScore(
        case_id=case_id,
        passed=passed,
        score=score,
        details=details or {},
        latency_ms=0.0,
    )


@pytest.fixture()
def calculator() -> ScoreCalculator:
    return ScoreCalculator()


@pytest.fixture()
def runner() -> BenchmarkRunner:
    return BenchmarkRunner()


@pytest.fixture()
def builder() -> SuiteBuilder:
    return SuiteBuilder()


@pytest.fixture()
def easy_case() -> BenchmarkCase:
    return make_case(case_id="easy-001", difficulty="easy")


@pytest.fixture()
def medium_case() -> BenchmarkCase:
    return make_case(case_id="medium-001", difficulty="medium")


@pytest.fixture()
def hard_case() -> BenchmarkCase:
    return make_case(case_id="hard-001", difficulty="hard")


@pytest.fixture()
def sample_suite(easy_case: BenchmarkCase, medium_case: BenchmarkCase) -> BenchmarkSuite:
    return BenchmarkSuite(
        suite_id=str(uuid.uuid4()),
        name="Test Suite",
        version="1.0.0",
        cases=[easy_case, medium_case],
    )
