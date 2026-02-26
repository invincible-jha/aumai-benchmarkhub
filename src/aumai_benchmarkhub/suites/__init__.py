"""Built-in benchmark suites for aumai-benchmarkhub."""

from aumai_benchmarkhub.suites.reasoning import REASONING_SUITE
from aumai_benchmarkhub.suites.safety import SAFETY_SUITE
from aumai_benchmarkhub.suites.tool_use import TOOL_USE_SUITE

__all__ = ["REASONING_SUITE", "SAFETY_SUITE", "TOOL_USE_SUITE"]
