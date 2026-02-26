"""Pydantic v2 models for aumai-benchmarkhub."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class BenchmarkCategory(str, Enum):
    """High-level capability categories for benchmark cases."""

    reasoning = "reasoning"
    tool_use = "tool_use"
    planning = "planning"
    coding = "coding"
    safety = "safety"
    robustness = "robustness"


Difficulty = Literal["easy", "medium", "hard"]


class BenchmarkCase(BaseModel):
    """A single benchmark evaluation case."""

    case_id: str
    category: BenchmarkCategory
    prompt: str
    expected_behavior: dict[str, object]
    difficulty: Difficulty = "medium"
    tags: list[str] = Field(default_factory=list)


class BenchmarkSuite(BaseModel):
    """A named, versioned collection of benchmark cases."""

    suite_id: str
    name: str
    version: str = "1.0.0"
    cases: list[BenchmarkCase] = Field(default_factory=list)


class BenchmarkScore(BaseModel):
    """Result for a single benchmark case evaluation."""

    case_id: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: dict[str, object] = Field(default_factory=dict)
    latency_ms: float = Field(ge=0.0, default=0.0)


class BenchmarkReport(BaseModel):
    """Full report for a benchmark suite run."""

    suite: BenchmarkSuite
    scores: list[BenchmarkScore]
    overall_score: float = Field(ge=0.0, le=1.0)
    by_category: dict[str, float] = Field(default_factory=dict)


__all__ = [
    "BenchmarkCategory",
    "BenchmarkCase",
    "BenchmarkSuite",
    "BenchmarkScore",
    "BenchmarkReport",
    "Difficulty",
]
