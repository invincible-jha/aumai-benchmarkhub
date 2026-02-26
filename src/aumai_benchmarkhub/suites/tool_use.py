"""10 built-in tool-use benchmark cases."""

from __future__ import annotations

from aumai_benchmarkhub.models import BenchmarkCase, BenchmarkCategory, BenchmarkSuite

_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        case_id="tool-001",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Search the web for the current weather in New York City and summarise it."
        ),
        expected_behavior={
            "contains": ["search", "weather"],
            "min_length": 30,
        },
        difficulty="easy",
        tags=["search", "retrieval"],
    ),
    BenchmarkCase(
        case_id="tool-002",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Send an email to john@example.com with subject 'Q4 Report' "
            "and a body saying the report is attached."
        ),
        expected_behavior={
            "contains": ["john@example.com", "q4 report"],
        },
        difficulty="easy",
        tags=["email", "communication"],
    ),
    BenchmarkCase(
        case_id="tool-003",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Read the file at /data/config.json and return the value of the 'api_key' field."
        ),
        expected_behavior={
            "contains": ["read", "api_key", "/data/config.json"],
        },
        difficulty="easy",
        tags=["file", "read"],
    ),
    BenchmarkCase(
        case_id="tool-004",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Execute a SQL query to find all users who signed up in the last 30 days."
        ),
        expected_behavior={
            "contains": ["select", "users"],
            "regex": r"(?i)(interval|now\(\)|current_timestamp|date_sub)",
        },
        difficulty="medium",
        tags=["database", "sql"],
    ),
    BenchmarkCase(
        case_id="tool-005",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Chain two tool calls: first search for 'Python async best practices', "
            "then save the top result to /tmp/results.txt."
        ),
        expected_behavior={
            "contains": ["search", "write", "/tmp/results.txt"],
        },
        difficulty="medium",
        tags=["chained-tools", "search", "file"],
    ),
    BenchmarkCase(
        case_id="tool-006",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Look up the stock price of AAPL using the market data tool, "
            "then send the result via email to cfo@company.com."
        ),
        expected_behavior={
            "contains": ["aapl", "cfo@company.com"],
        },
        difficulty="medium",
        tags=["chained-tools", "finance", "email"],
    ),
    BenchmarkCase(
        case_id="tool-007",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "List all files in the /data/reports/ directory and return the names of those "
            "modified in the last 7 days."
        ),
        expected_behavior={
            "contains": ["/data/reports/", "list"],
        },
        difficulty="easy",
        tags=["file", "list"],
    ),
    BenchmarkCase(
        case_id="tool-008",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Delete the temporary file at /tmp/cache.json and confirm success."
        ),
        expected_behavior={
            "contains": ["/tmp/cache.json", "delete"],
        },
        difficulty="easy",
        tags=["file", "delete"],
    ),
    BenchmarkCase(
        case_id="tool-009",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Perform a batch update in the database: set status='archived' "
            "for all records where last_active < '2023-01-01'."
        ),
        expected_behavior={
            "contains": ["update", "archived", "last_active"],
            "not_contains": ["drop", "truncate", "delete from"],
        },
        difficulty="hard",
        tags=["database", "batch-update"],
    ),
    BenchmarkCase(
        case_id="tool-010",
        category=BenchmarkCategory.tool_use,
        prompt=(
            "Given a tool that returns JSON, call it with arguments {'query': 'latest AI news'} "
            "and parse the 'title' fields from the results array."
        ),
        expected_behavior={
            "contains": ["title", "results", "json"],
            "min_length": 50,
        },
        difficulty="medium",
        tags=["json-parsing", "api"],
    ),
]

TOOL_USE_SUITE = BenchmarkSuite(
    suite_id="builtin-tool-use-v1",
    name="Tool Use",
    version="1.0.0",
    cases=_CASES,
)

__all__ = ["TOOL_USE_SUITE"]
