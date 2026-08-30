"""
Domain two: generated-code property violation.

The adjudicator is CPython running a reference implementation, so a verdict
here is as non-circular as domain one's arithmetic. Candidates are *inputs*
rather than expressions, which is why this domain needs process isolation where
domain one needed only an AST whitelist.
"""

from .domain import CodePropertyDomain
from .sandbox import DEFAULT_TIMEOUT_SECONDS, RunResult, run_property
from .targets import RULE_IDS, RULES, Rule, check_contract, check_property

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "RULES",
    "RULE_IDS",
    "CodePropertyDomain",
    "Rule",
    "RunResult",
    "check_contract",
    "check_property",
    "run_property",
]
