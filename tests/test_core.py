"""Comprehensive tests for aumai_benchmarkhub core, models, and suites."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from aumai_benchmarkhub.core import (
    BenchmarkRunner,
    ScoreCalculator,
    SuiteBuilder,
    UnsafePatternError,
    _evaluate_output,
    _DIFFICULTY_WEIGHTS,
    _validate_and_compile_regex,
)
from aumai_benchmarkhub.models import (
    BenchmarkCase,
    BenchmarkCategory,
    BenchmarkReport,
    BenchmarkScore,
    BenchmarkSuite,
)
from aumai_benchmarkhub.suites import REASONING_SUITE, SAFETY_SUITE, TOOL_USE_SUITE
from tests.conftest import make_case, make_score


# ---------------------------------------------------------------------------
# Tests for _evaluate_output
# ---------------------------------------------------------------------------


class TestEvaluateOutput:
    def test_contains_all_tokens_passes(self) -> None:
        case = make_case(expected_behavior={"contains": ["hello", "world"]})
        passed, score, details = _evaluate_output(case, "Hello World!")
        assert passed is True
        assert score == 1.0

    def test_contains_missing_token_fails(self) -> None:
        case = make_case(expected_behavior={"contains": ["hello", "missing"]})
        passed, score, details = _evaluate_output(case, "Hello there")
        assert passed is False
        assert score < 1.0
        assert "missing_tokens" in details

    def test_not_contains_passes_when_absent(self) -> None:
        case = make_case(expected_behavior={"not_contains": ["forbidden"]})
        passed, score, details = _evaluate_output(case, "This is safe output.")
        assert passed is True

    def test_not_contains_fails_when_present(self) -> None:
        case = make_case(expected_behavior={"not_contains": ["forbidden"]})
        passed, score, details = _evaluate_output(case, "This is forbidden output.")
        assert passed is False
        assert "forbidden_found" in details

    def test_regex_check_passes(self) -> None:
        case = make_case(expected_behavior={"regex": r"\d{4}"})
        passed, score, details = _evaluate_output(case, "The year was 2024.")
        assert passed is True

    def test_regex_check_fails(self) -> None:
        case = make_case(expected_behavior={"regex": r"\d{4}"})
        passed, score, details = _evaluate_output(case, "No numbers here.")
        assert passed is False
        assert "regex_failed" in details

    def test_min_length_passes(self) -> None:
        case = make_case(expected_behavior={"min_length": 5})
        passed, score, details = _evaluate_output(case, "Hello world!")
        assert passed is True

    def test_min_length_fails(self) -> None:
        case = make_case(expected_behavior={"min_length": 100})
        passed, score, details = _evaluate_output(case, "Short.")
        assert passed is False
        assert "too_short" in details

    def test_max_length_passes(self) -> None:
        case = make_case(expected_behavior={"max_length": 1000})
        passed, score, details = _evaluate_output(case, "Short answer.")
        assert passed is True

    def test_max_length_fails(self) -> None:
        case = make_case(expected_behavior={"max_length": 5})
        passed, score, details = _evaluate_output(case, "This is too long for the limit.")
        assert passed is False
        assert "too_long" in details

    def test_json_valid_check_passes(self) -> None:
        case = make_case(expected_behavior={"json_valid": True})
        passed, score, details = _evaluate_output(case, '{"key": "value"}')
        assert passed is True

    def test_json_valid_check_fails(self) -> None:
        case = make_case(expected_behavior={"json_valid": True})
        passed, score, details = _evaluate_output(case, "not valid json {")
        assert passed is False
        assert "json_error" in details

    def test_no_checks_passes_if_nonempty(self) -> None:
        case = make_case(expected_behavior={})
        passed, score, details = _evaluate_output(case, "Any non-empty response.")
        assert passed is True

    def test_no_checks_fails_if_empty(self) -> None:
        case = make_case(expected_behavior={})
        passed, score, details = _evaluate_output(case, "")
        assert passed is False

    def test_no_checks_fails_if_whitespace_only(self) -> None:
        case = make_case(expected_behavior={})
        passed, score, details = _evaluate_output(case, "   ")
        assert passed is False

    def test_multiple_checks_partial_score(self) -> None:
        case = make_case(expected_behavior={"contains": ["a", "b"], "min_length": 3})
        passed, score, details = _evaluate_output(case, "a is here")
        # 1/2 contains + 1/1 min_length = 2/3 checks
        assert 0.0 < score < 1.0

    def test_case_insensitive_contains(self) -> None:
        case = make_case(expected_behavior={"contains": ["HELLO"]})
        passed, score, details = _evaluate_output(case, "hello world")
        assert passed is True

    def test_regex_case_insensitive(self) -> None:
        case = make_case(expected_behavior={"regex": r"python"})
        passed, score, details = _evaluate_output(case, "I love PYTHON!")
        assert passed is True

    def test_regex_invalid_pattern_is_safe(self) -> None:
        """An invalid regex must not raise; it must be recorded as a failed check."""
        case = make_case(expected_behavior={"regex": r"[unclosed"})
        passed, score, details = _evaluate_output(case, "some output")
        assert passed is False
        assert "regex_error" in details

    def test_regex_nested_quantifier_is_rejected(self) -> None:
        """A pattern with nested quantifiers must be rejected without running."""
        case = make_case(expected_behavior={"regex": r"(a+)+"})
        passed, score, details = _evaluate_output(case, "aaaaaa")
        assert passed is False
        assert "regex_error" in details

    def test_regex_overly_long_pattern_is_rejected(self) -> None:
        """A pattern exceeding 500 chars must be rejected."""
        long_pattern = "a" * 501
        case = make_case(expected_behavior={"regex": long_pattern})
        passed, score, details = _evaluate_output(case, "a" * 501)
        assert passed is False
        assert "regex_error" in details


# ---------------------------------------------------------------------------
# Tests for _validate_and_compile_regex
# ---------------------------------------------------------------------------


class TestValidateAndCompileRegex:
    def test_valid_simple_pattern_compiles(self) -> None:
        compiled = _validate_and_compile_regex(r"\d{4}")
        assert compiled.search("year 2024")

    def test_pattern_at_max_length_is_accepted(self) -> None:
        pattern = "a" * 500
        # Should compile without raising.
        compiled = _validate_and_compile_regex(pattern)
        assert compiled is not None

    def test_pattern_over_max_length_raises(self) -> None:
        with pytest.raises(UnsafePatternError, match="maximum allowed length"):
            _validate_and_compile_regex("a" * 501)

    def test_nested_quantifier_raises(self) -> None:
        with pytest.raises(UnsafePatternError, match="nested quantifiers"):
            _validate_and_compile_regex(r"(a+)+")

    def test_nested_star_raises(self) -> None:
        with pytest.raises(UnsafePatternError, match="nested quantifiers"):
            _validate_and_compile_regex(r"(.+)*")

    def test_invalid_syntax_raises(self) -> None:
        with pytest.raises(UnsafePatternError, match="Invalid regex"):
            _validate_and_compile_regex(r"[unclosed")

    def test_legitimate_complex_pattern_accepted(self) -> None:
        # A moderately complex but safe pattern.
        compiled = _validate_and_compile_regex(r"^(https?|ftp)://[^\s/$.?#].[^\s]*$")
        assert compiled is not None

    def test_compiled_pattern_uses_ignorecase_and_dotall(self) -> None:
        compiled = _validate_and_compile_regex(r"hello")
        assert compiled.search("HELLO world")  # IGNORECASE
        assert compiled.search("line1\nHELLO\nline2")  # DOTALL


# ---------------------------------------------------------------------------
# Tests for ScoreCalculator
# ---------------------------------------------------------------------------


class TestScoreCalculator:
    def test_overall_empty_scores_returns_zero(self, calculator: ScoreCalculator) -> None:
        assert calculator.overall([], []) == 0.0

    def test_overall_single_perfect_score(
        self, calculator: ScoreCalculator, easy_case: BenchmarkCase
    ) -> None:
        score = make_score(case_id="easy-001", score=1.0)
        result = calculator.overall([score], [easy_case])
        assert result == 1.0

    def test_overall_single_zero_score(
        self, calculator: ScoreCalculator, easy_case: BenchmarkCase
    ) -> None:
        score = make_score(case_id="easy-001", score=0.0)
        result = calculator.overall([score], [easy_case])
        assert result == 0.0

    def test_overall_weights_hard_cases_more(
        self,
        calculator: ScoreCalculator,
        easy_case: BenchmarkCase,
        hard_case: BenchmarkCase,
    ) -> None:
        # All pass: easy_case weight=1.0, hard_case weight=2.0
        scores = [
            make_score(case_id="easy-001", score=1.0),
            make_score(case_id="hard-001", score=0.0),
        ]
        cases = [easy_case, hard_case]
        result = calculator.overall(scores, cases)
        # Weighted: (1.0*1.0 + 0.0*2.0) / (1.0+2.0) = 1/3
        assert abs(result - 1 / 3) < 0.001

    def test_overall_unknown_case_uses_medium_weight(
        self, calculator: ScoreCalculator
    ) -> None:
        scores = [make_score(case_id="unknown-id", score=1.0)]
        result = calculator.overall(scores, [])
        # Uses medium weight (1.5)
        assert result == 1.0

    def test_by_category_groups_correctly(
        self,
        calculator: ScoreCalculator,
        easy_case: BenchmarkCase,
    ) -> None:
        safety_case = make_case(
            case_id="safety-t",
            category=BenchmarkCategory.safety,
            difficulty="easy",
        )
        scores = [
            make_score(case_id="easy-001", score=1.0),
            make_score(case_id="safety-t", score=0.5),
        ]
        result = calculator.by_category(scores, [easy_case, safety_case])
        assert "reasoning" in result
        assert "safety" in result
        assert result["reasoning"] == 1.0
        assert result["safety"] == 0.5

    def test_by_category_missing_case_skipped(
        self, calculator: ScoreCalculator
    ) -> None:
        scores = [make_score(case_id="no-such-case", score=1.0)]
        result = calculator.by_category(scores, [])
        assert result == {}

    def test_difficulty_weights_defined(self) -> None:
        assert "easy" in _DIFFICULTY_WEIGHTS
        assert "medium" in _DIFFICULTY_WEIGHTS
        assert "hard" in _DIFFICULTY_WEIGHTS
        assert _DIFFICULTY_WEIGHTS["hard"] > _DIFFICULTY_WEIGHTS["easy"]


# ---------------------------------------------------------------------------
# Tests for BenchmarkRunner
# ---------------------------------------------------------------------------


class TestBenchmarkRunner:
    def test_run_case_passes_on_correct_output(
        self, runner: BenchmarkRunner, easy_case: BenchmarkCase
    ) -> None:
        # easy_case expected_behavior = {"contains": ["4"]}
        score = runner.run_case(easy_case, "The answer is 4.")
        assert score.passed is True
        assert score.score == 1.0

    def test_run_case_fails_on_wrong_output(
        self, runner: BenchmarkRunner, easy_case: BenchmarkCase
    ) -> None:
        score = runner.run_case(easy_case, "I don't know.")
        assert score.passed is False

    def test_run_case_returns_case_id(
        self, runner: BenchmarkRunner, easy_case: BenchmarkCase
    ) -> None:
        score = runner.run_case(easy_case, "4")
        assert score.case_id == "easy-001"

    def test_run_case_latency_positive(
        self, runner: BenchmarkRunner, easy_case: BenchmarkCase
    ) -> None:
        score = runner.run_case(easy_case, "The answer is 4.")
        assert score.latency_ms >= 0.0

    def test_run_suite_returns_report(
        self,
        runner: BenchmarkRunner,
        sample_suite: BenchmarkSuite,
    ) -> None:
        outputs = {
            "easy-001": "The answer is 4.",
            "medium-001": "The answer is 4.",
        }
        report = runner.run_suite(sample_suite, outputs)
        assert isinstance(report, BenchmarkReport)

    def test_run_suite_scores_count_matches_cases(
        self,
        runner: BenchmarkRunner,
        sample_suite: BenchmarkSuite,
    ) -> None:
        outputs = {c.case_id: "4" for c in sample_suite.cases}
        report = runner.run_suite(sample_suite, outputs)
        assert len(report.scores) == len(sample_suite.cases)

    def test_run_suite_missing_output_uses_empty_string(
        self,
        runner: BenchmarkRunner,
        sample_suite: BenchmarkSuite,
    ) -> None:
        report = runner.run_suite(sample_suite, {})
        # All outputs missing -> should not raise; scores will be fails
        assert len(report.scores) == 2

    def test_run_suite_overall_score_in_range(
        self,
        runner: BenchmarkRunner,
        sample_suite: BenchmarkSuite,
    ) -> None:
        outputs = {c.case_id: "4" for c in sample_suite.cases}
        report = runner.run_suite(sample_suite, outputs)
        assert 0.0 <= report.overall_score <= 1.0

    def test_run_suite_by_category_populated(
        self,
        runner: BenchmarkRunner,
        sample_suite: BenchmarkSuite,
    ) -> None:
        outputs = {c.case_id: "4" for c in sample_suite.cases}
        report = runner.run_suite(sample_suite, outputs)
        assert "reasoning" in report.by_category

    def test_load_suite_roundtrip(
        self, runner: BenchmarkRunner, sample_suite: BenchmarkSuite, tmp_path: Path
    ) -> None:
        suite_path = tmp_path / "suite.json"
        suite_path.write_text(sample_suite.model_dump_json(), encoding="utf-8")
        loaded = runner.load_suite(str(suite_path))
        assert loaded.name == sample_suite.name
        assert len(loaded.cases) == len(sample_suite.cases)


# ---------------------------------------------------------------------------
# Tests for SuiteBuilder
# ---------------------------------------------------------------------------


class TestSuiteBuilder:
    def test_create_suite_has_uuid_id(self, builder: SuiteBuilder) -> None:
        suite = builder.create_suite("TestSuite")
        uuid.UUID(suite.suite_id)  # Validates UUID format

    def test_create_suite_name(self, builder: SuiteBuilder) -> None:
        suite = builder.create_suite("My Suite")
        assert suite.name == "My Suite"

    def test_create_suite_custom_version(self, builder: SuiteBuilder) -> None:
        suite = builder.create_suite("S", version="2.0.0")
        assert suite.version == "2.0.0"

    def test_create_suite_empty_cases(self, builder: SuiteBuilder) -> None:
        suite = builder.create_suite("S")
        assert suite.cases == []

    def test_add_case_appends(self, builder: SuiteBuilder, easy_case: BenchmarkCase) -> None:
        suite = builder.create_suite("S")
        builder.add_case(suite, easy_case)
        assert len(suite.cases) == 1
        assert suite.cases[0] == easy_case

    def test_add_multiple_cases(
        self,
        builder: SuiteBuilder,
        easy_case: BenchmarkCase,
        medium_case: BenchmarkCase,
    ) -> None:
        suite = builder.create_suite("S")
        builder.add_case(suite, easy_case)
        builder.add_case(suite, medium_case)
        assert len(suite.cases) == 2

    def test_save_suite_creates_file(
        self, builder: SuiteBuilder, sample_suite: BenchmarkSuite, tmp_path: Path
    ) -> None:
        output_path = tmp_path / "suite.json"
        builder.save_suite(sample_suite, str(output_path))
        assert output_path.exists()

    def test_save_suite_valid_json(
        self, builder: SuiteBuilder, sample_suite: BenchmarkSuite, tmp_path: Path
    ) -> None:
        output_path = tmp_path / "suite.json"
        builder.save_suite(sample_suite, str(output_path))
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["name"] == sample_suite.name
        assert len(data["cases"]) == len(sample_suite.cases)


# ---------------------------------------------------------------------------
# Tests for built-in suites
# ---------------------------------------------------------------------------


class TestBuiltinSuites:
    def test_reasoning_suite_has_ten_cases(self) -> None:
        assert len(REASONING_SUITE.cases) == 10

    def test_reasoning_suite_all_reasoning_category(self) -> None:
        for case in REASONING_SUITE.cases:
            assert case.category == BenchmarkCategory.reasoning

    def test_tool_use_suite_has_ten_cases(self) -> None:
        assert len(TOOL_USE_SUITE.cases) == 10

    def test_tool_use_suite_all_tool_use_category(self) -> None:
        for case in TOOL_USE_SUITE.cases:
            assert case.category == BenchmarkCategory.tool_use

    def test_safety_suite_has_ten_cases(self) -> None:
        assert len(SAFETY_SUITE.cases) == 10

    def test_safety_suite_all_safety_category(self) -> None:
        for case in SAFETY_SUITE.cases:
            assert case.category == BenchmarkCategory.safety

    def test_all_suites_have_unique_ids(self) -> None:
        suite_ids = {REASONING_SUITE.suite_id, TOOL_USE_SUITE.suite_id, SAFETY_SUITE.suite_id}
        assert len(suite_ids) == 3

    def test_all_cases_have_unique_ids(self) -> None:
        all_cases = (
            REASONING_SUITE.cases + TOOL_USE_SUITE.cases + SAFETY_SUITE.cases
        )
        case_ids = {c.case_id for c in all_cases}
        assert len(case_ids) == 30

    def test_all_cases_have_difficulty(self) -> None:
        all_cases = (
            REASONING_SUITE.cases + TOOL_USE_SUITE.cases + SAFETY_SUITE.cases
        )
        valid_difficulties = {"easy", "medium", "hard"}
        for case in all_cases:
            assert case.difficulty in valid_difficulties

    def test_all_cases_have_expected_behavior(self) -> None:
        all_cases = (
            REASONING_SUITE.cases + TOOL_USE_SUITE.cases + SAFETY_SUITE.cases
        )
        for case in all_cases:
            assert isinstance(case.expected_behavior, dict)
            assert len(case.expected_behavior) > 0

    def test_reasoning_suite_name(self) -> None:
        assert REASONING_SUITE.name == "Reasoning"

    def test_tool_use_suite_name(self) -> None:
        assert TOOL_USE_SUITE.name == "Tool Use"

    def test_safety_suite_name(self) -> None:
        assert SAFETY_SUITE.name == "Safety"

    def test_run_reasoning_suite_with_correct_answers(self, runner: BenchmarkRunner) -> None:
        # Provide responses that satisfy the first case
        case = REASONING_SUITE.cases[0]
        # case_id="reasoning-001", expected contains ["5 cents", "$0.05", "five cents"]
        # ALL tokens must be present for passed=True, plus not_contains tokens absent
        outputs = {case.case_id: "The answer is 5 cents, which is $0.05, five cents."}
        outputs.update({c.case_id: "" for c in REASONING_SUITE.cases[1:]})
        report = runner.run_suite(REASONING_SUITE, outputs)
        assert report.scores[0].passed is True


# ---------------------------------------------------------------------------
# Tests for models
# ---------------------------------------------------------------------------


class TestModels:
    def test_benchmark_category_values(self) -> None:
        assert BenchmarkCategory.reasoning.value == "reasoning"
        assert BenchmarkCategory.tool_use.value == "tool_use"
        assert BenchmarkCategory.safety.value == "safety"

    def test_benchmark_score_range(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            BenchmarkScore(case_id="x", passed=True, score=1.5)

    def test_benchmark_score_latency_positive(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            BenchmarkScore(case_id="x", passed=True, score=0.5, latency_ms=-1.0)

    def test_benchmark_report_overall_range(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            BenchmarkReport(
                suite=BenchmarkSuite(suite_id="s1", name="S"),
                scores=[],
                overall_score=2.0,  # > 1.0
            )

    def test_benchmark_case_defaults(self) -> None:
        case = BenchmarkCase(
            case_id="c1",
            category=BenchmarkCategory.coding,
            prompt="Write a function",
            expected_behavior={"contains": ["def"]},
        )
        assert case.difficulty == "medium"
        assert case.tags == []

    @pytest.mark.parametrize(
        "category",
        list(BenchmarkCategory),
    )
    def test_all_categories_valid(self, category: BenchmarkCategory) -> None:
        case = make_case(category=category)
        assert case.category == category
