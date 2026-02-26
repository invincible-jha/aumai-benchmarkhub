"""CLI entry point for aumai-benchmarkhub."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from aumai_benchmarkhub.core import BenchmarkRunner, ScoreCalculator, SuiteBuilder
from aumai_benchmarkhub.models import BenchmarkCase, BenchmarkCategory, BenchmarkSuite
from aumai_benchmarkhub.suites import REASONING_SUITE, SAFETY_SUITE, TOOL_USE_SUITE

# Registry of built-in suites.
_BUILTIN_SUITES: dict[str, BenchmarkSuite] = {
    "reasoning": REASONING_SUITE,
    "tool_use": TOOL_USE_SUITE,
    "safety": SAFETY_SUITE,
}


def _load_jsonl(path: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


@click.group()
@click.version_option()
def main() -> None:
    """AumAI BenchmarkHub — standardised benchmarks for agent capabilities."""


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


@main.command("run")
@click.option(
    "--suite",
    "suite_name",
    required=True,
    help=(
        "Built-in suite name (reasoning/tool_use/safety) or path to a .json suite file."
    ),
)
@click.option(
    "--results",
    "results_path",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="JSONL file mapping case_id -> agent_output.",
)
@click.option(
    "--output",
    default="-",
    type=click.Path(allow_dash=True),
    show_default=True,
    help="Output file for the report JSON. '-' for stdout.",
)
def run_cmd(suite_name: str, results_path: str, output: str) -> None:
    """Run a benchmark suite against agent outputs and produce a report."""
    runner = BenchmarkRunner()

    # Resolve suite.
    if suite_name in _BUILTIN_SUITES:
        suite = _BUILTIN_SUITES[suite_name]
    else:
        suite = runner.load_suite(suite_name)

    # Load agent outputs.
    records = _load_jsonl(results_path)
    agent_outputs: dict[str, str] = {
        str(record["case_id"]): str(record.get("output", record.get("agent_output", "")))
        for record in records
    }

    click.echo(
        f"Running suite '{suite.name}' ({len(suite.cases)} cases) ...",
        err=True,
    )

    report = runner.run_suite(suite, agent_outputs)

    output_data = report.model_dump()
    out_text = json.dumps(output_data, indent=2)

    if output == "-":
        click.echo(out_text)
    else:
        Path(output).write_text(out_text, encoding="utf-8")
        click.echo(f"Report written to: {output}", err=True)

    click.echo(
        f"\nOverall score: {report.overall_score:.4f}",
        err=True,
    )
    for cat, cat_score in report.by_category.items():
        click.echo(f"  {cat}: {cat_score:.4f}", err=True)

    passed = sum(1 for s in report.scores if s.passed)
    click.echo(
        f"\nPassed: {passed}/{len(report.scores)} cases",
        err=True,
    )


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------


@main.command("list")
@click.option(
    "--category",
    type=click.Choice([c.value for c in BenchmarkCategory], case_sensitive=False),
    default=None,
    help="Filter by benchmark category.",
)
@click.option(
    "--suite",
    "suite_name",
    default=None,
    help="Built-in suite name or path to a .json suite file.",
)
def list_cmd(category: str | None, suite_name: str | None) -> None:
    """List benchmark cases, optionally filtered by category or suite."""
    cases: list[BenchmarkCase] = []

    if suite_name is not None:
        if suite_name in _BUILTIN_SUITES:
            cases = list(_BUILTIN_SUITES[suite_name].cases)
        else:
            runner = BenchmarkRunner()
            suite = runner.load_suite(suite_name)
            cases = list(suite.cases)
    else:
        for suite in _BUILTIN_SUITES.values():
            cases.extend(suite.cases)

    if category is not None:
        target_cat = BenchmarkCategory(category)
        cases = [c for c in cases if c.category == target_cat]

    if not cases:
        click.echo("No benchmark cases found.", err=True)
        return

    click.echo(f"\nFound {len(cases)} case(s):\n")
    for case in cases:
        tags = ", ".join(case.tags) if case.tags else "-"
        click.echo(
            f"  [{case.difficulty:6s}] {case.case_id:20s}  "
            f"category={case.category.value:10s}  tags={tags}"
        )
    click.echo("")


# ---------------------------------------------------------------------------
# create command
# ---------------------------------------------------------------------------


@main.command("create")
@click.option("--name", required=True, help="Suite name.")
@click.option(
    "--output",
    required=True,
    type=click.Path(allow_dash=False),
    help="Output .json file for the new suite.",
)
@click.option(
    "--version",
    default="1.0.0",
    show_default=True,
    help="Suite version string.",
)
@click.option(
    "--from-cases",
    "cases_path",
    default=None,
    type=click.Path(exists=True, readable=True),
    help="Optional JSONL file of BenchmarkCase objects to seed the suite.",
)
def create_cmd(name: str, output: str, version: str, cases_path: str | None) -> None:
    """Create a new benchmark suite, optionally pre-populated from a JSONL file."""
    builder = SuiteBuilder()
    suite = builder.create_suite(name, version)

    if cases_path is not None:
        records = _load_jsonl(cases_path)
        for record in records:
            case = BenchmarkCase.model_validate(record)
            builder.add_case(suite, case)

    builder.save_suite(suite, output)
    click.echo(
        f"Created suite '{name}' ({len(suite.cases)} cases) -> {output}",
        err=True,
    )
    click.echo(json.dumps(suite.model_dump(), indent=2))


if __name__ == "__main__":
    main()
