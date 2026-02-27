"""Comprehensive CLI tests for aumai-benchmarkhub."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from click.testing import CliRunner

from aumai_benchmarkhub.cli import main
from aumai_benchmarkhub.models import BenchmarkCase, BenchmarkCategory, BenchmarkSuite


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from mixed CLI output."""
    start = text.index("{")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("No JSON object found in output")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_suite_json(path: Path, num_cases: int = 2) -> None:
    cases = [
        {
            "case_id": f"case-{i:03d}",
            "category": "reasoning",
            "prompt": f"Question {i}?",
            "expected_behavior": {"contains": ["answer"]},
            "difficulty": "easy",
            "tags": ["test"],
        }
        for i in range(num_cases)
    ]
    suite = {
        "suite_id": str(uuid.uuid4()),
        "name": "CLI Test Suite",
        "version": "1.0.0",
        "cases": cases,
    }
    path.write_text(json.dumps(suite), encoding="utf-8")


def _make_results_jsonl(path: Path, case_ids: list[str], output_text: str = "the answer") -> None:
    lines = [json.dumps({"case_id": cid, "output": output_text}) for cid in case_ids]
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# version / help
# ---------------------------------------------------------------------------


class TestCliMeta:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "BenchmarkHub" in result.output or "benchmarkhub" in result.output.lower()


# ---------------------------------------------------------------------------
# `run` command
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_run_requires_suite_and_results(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["run"])
        assert result.exit_code != 0

    def test_run_builtin_reasoning_suite(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Build results JSONL for all 10 reasoning cases
            from aumai_benchmarkhub.suites import REASONING_SUITE

            case_ids = [c.case_id for c in REASONING_SUITE.cases]
            _make_results_jsonl(
                Path("results.jsonl"),
                case_ids,
                output_text="The answer is $0.05, five cents, and yes all Bloops are Lazzies.",
            )
            result = runner.invoke(
                main,
                ["run", "--suite", "reasoning", "--results", "results.jsonl"],
            )
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert "overall_score" in data
            assert "scores" in data

    def test_run_with_custom_suite_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            _make_suite_json(Path("suite.json"), num_cases=2)
            _make_results_jsonl(
                Path("results.jsonl"),
                ["case-000", "case-001"],
                output_text="the answer",
            )
            result = runner.invoke(
                main,
                ["run", "--suite", "suite.json", "--results", "results.jsonl"],
            )
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert "overall_score" in data

    def test_run_output_to_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            _make_suite_json(Path("suite.json"))
            _make_results_jsonl(Path("results.jsonl"), ["case-000", "case-001"])
            result = runner.invoke(
                main,
                [
                    "run",
                    "--suite", "suite.json",
                    "--results", "results.jsonl",
                    "--output", "report.json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(Path("report.json").read_text(encoding="utf-8"))
            assert "overall_score" in data

    def test_run_results_structure(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            _make_suite_json(Path("suite.json"), num_cases=3)
            _make_results_jsonl(
                Path("results.jsonl"),
                ["case-000", "case-001", "case-002"],
                output_text="the answer",
            )
            result = runner.invoke(
                main,
                ["run", "--suite", "suite.json", "--results", "results.jsonl"],
            )
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert len(data["scores"]) == 3
            for score in data["scores"]:
                assert "case_id" in score
                assert "score" in score
                assert "passed" in score

    def test_run_builtin_safety_suite(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            from aumai_benchmarkhub.suites import SAFETY_SUITE

            case_ids = [c.case_id for c in SAFETY_SUITE.cases]
            _make_results_jsonl(
                Path("results.jsonl"),
                case_ids,
                output_text="I cannot help with that. This is harmful and I refuse.",
            )
            result = runner.invoke(
                main,
                ["run", "--suite", "safety", "--results", "results.jsonl"],
            )
            assert result.exit_code == 0

    def test_run_builtin_tool_use_suite(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            from aumai_benchmarkhub.suites import TOOL_USE_SUITE

            case_ids = [c.case_id for c in TOOL_USE_SUITE.cases]
            _make_results_jsonl(
                Path("results.jsonl"),
                case_ids,
                output_text="I will search for the weather and send an email.",
            )
            result = runner.invoke(
                main,
                ["run", "--suite", "tool_use", "--results", "results.jsonl"],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# `list` command
# ---------------------------------------------------------------------------


class TestListCommand:
    def test_list_all_cases(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        # Should show cases from all 3 built-in suites (30 total)
        assert "Found" in result.output

    def test_list_filter_by_category_reasoning(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list", "--category", "reasoning"])
        assert result.exit_code == 0
        assert "reasoning" in result.output

    def test_list_filter_by_category_safety(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list", "--category", "safety"])
        assert result.exit_code == 0
        assert "safety" in result.output

    def test_list_filter_by_category_tool_use(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list", "--category", "tool_use"])
        assert result.exit_code == 0
        assert "tool_use" in result.output

    def test_list_by_suite_name_reasoning(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list", "--suite", "reasoning"])
        assert result.exit_code == 0
        assert "reasoning" in result.output

    def test_list_by_custom_suite_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            _make_suite_json(Path("suite.json"), num_cases=3)
            result = runner.invoke(main, ["list", "--suite", "suite.json"])
            assert result.exit_code == 0
            assert "Found 3" in result.output

    def test_list_invalid_category(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list", "--category", "invalid_cat"])
        assert result.exit_code != 0

    def test_list_shows_difficulty(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list", "--category", "reasoning"])
        assert result.exit_code == 0
        # Difficulty values should appear in output
        assert "easy" in result.output or "medium" in result.output or "hard" in result.output


# ---------------------------------------------------------------------------
# `create` command
# ---------------------------------------------------------------------------


class TestCreateCommand:
    def test_create_requires_name_and_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["create"])
        assert result.exit_code != 0

    def test_create_empty_suite(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                ["create", "--name", "My Suite", "--output", "suite.json"],
            )
            assert result.exit_code == 0
            data = json.loads(Path("suite.json").read_text(encoding="utf-8"))
            assert data["name"] == "My Suite"
            assert data["cases"] == []

    def test_create_with_version(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                ["create", "--name", "S", "--output", "s.json", "--version", "2.5.0"],
            )
            assert result.exit_code == 0
            data = json.loads(Path("s.json").read_text(encoding="utf-8"))
            assert data["version"] == "2.5.0"

    def test_create_with_cases_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            cases = [
                {
                    "case_id": "c1",
                    "category": "reasoning",
                    "prompt": "Test?",
                    "expected_behavior": {"contains": ["yes"]},
                    "difficulty": "easy",
                }
            ]
            cases_path = Path("cases.jsonl")
            cases_path.write_text(
                "\n".join(json.dumps(c) for c in cases), encoding="utf-8"
            )
            result = runner.invoke(
                main,
                [
                    "create",
                    "--name", "Suite With Cases",
                    "--output", "suite.json",
                    "--from-cases", "cases.jsonl",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(Path("suite.json").read_text(encoding="utf-8"))
            assert len(data["cases"]) == 1
            assert data["cases"][0]["case_id"] == "c1"

    def test_create_outputs_json_to_stdout(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                ["create", "--name", "TestSuite", "--output", "suite.json"],
            )
            assert result.exit_code == 0
            # CLI also echoes JSON to stdout
            assert "TestSuite" in result.output
