"""10 built-in reasoning benchmark cases."""

from __future__ import annotations

from aumai_benchmarkhub.models import BenchmarkCase, BenchmarkCategory, BenchmarkSuite

_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        case_id="reasoning-001",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. "
            "How much does the ball cost?"
        ),
        expected_behavior={
            "contains": ["5 cents", "$0.05", "five cents"],
            "not_contains": ["10 cents", "$0.10"],
        },
        difficulty="easy",
        tags=["math", "cognitive-bias"],
    ),
    BenchmarkCase(
        case_id="reasoning-002",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies? "
            "Explain your reasoning step by step."
        ),
        expected_behavior={
            "contains": ["yes", "all bloops are lazzies"],
            "min_length": 50,
        },
        difficulty="easy",
        tags=["logic", "syllogism"],
    ),
    BenchmarkCase(
        case_id="reasoning-003",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "There are 5 houses in a row, each painted a different colour. "
            "The green house is immediately to the left of the white house. "
            "The green house owner drinks coffee. "
            "Who drinks coffee?"
        ),
        expected_behavior={
            "contains": ["green house owner", "coffee"],
        },
        difficulty="medium",
        tags=["logic-puzzle", "deduction"],
    ),
    BenchmarkCase(
        case_id="reasoning-004",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "A farmer has 17 sheep. All but 9 die. How many sheep does the farmer have left?"
        ),
        expected_behavior={
            "contains": ["9"],
            "not_contains": ["8", "17"],
        },
        difficulty="easy",
        tags=["math", "trick-question"],
    ),
    BenchmarkCase(
        case_id="reasoning-005",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "Two trains are 100 miles apart and heading toward each other, "
            "one at 40 mph and one at 60 mph. How long until they meet?"
        ),
        expected_behavior={
            "contains": ["1 hour", "60 minutes"],
        },
        difficulty="medium",
        tags=["math", "relative-speed"],
    ),
    BenchmarkCase(
        case_id="reasoning-006",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "Explain the Monty Hall problem and state whether you should switch doors."
        ),
        expected_behavior={
            "contains": ["switch", "2/3", "probability"],
            "min_length": 100,
        },
        difficulty="medium",
        tags=["probability", "counterintuitive"],
    ),
    BenchmarkCase(
        case_id="reasoning-007",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "If today is Wednesday and a meeting is scheduled for 'the day after tomorrow', "
            "on which day of the week is the meeting?"
        ),
        expected_behavior={
            "contains": ["friday"],
        },
        difficulty="easy",
        tags=["temporal-reasoning"],
    ),
    BenchmarkCase(
        case_id="reasoning-008",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "A snail climbs a 10-foot pole. Each day it climbs 3 feet, each night it slides back 2 feet. "
            "How many days does it take to reach the top?"
        ),
        expected_behavior={
            "contains": ["8"],
        },
        difficulty="medium",
        tags=["math", "iteration"],
    ),
    BenchmarkCase(
        case_id="reasoning-009",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "Given the premises: 'No reptiles are mammals' and 'All snakes are reptiles', "
            "what can you conclude about snakes and mammals?"
        ),
        expected_behavior={
            "contains": ["no snakes are mammals", "snakes are not mammals"],
        },
        difficulty="easy",
        tags=["syllogism", "deduction"],
    ),
    BenchmarkCase(
        case_id="reasoning-010",
        category=BenchmarkCategory.reasoning,
        prompt=(
            "You have a 3-litre jug and a 5-litre jug. How do you measure exactly 4 litres of water?"
        ),
        expected_behavior={
            "contains": ["4"],
            "min_length": 80,
        },
        difficulty="hard",
        tags=["water-jug", "problem-solving"],
    ),
]

REASONING_SUITE = BenchmarkSuite(
    suite_id="builtin-reasoning-v1",
    name="Reasoning",
    version="1.0.0",
    cases=_CASES,
)

__all__ = ["REASONING_SUITE"]
