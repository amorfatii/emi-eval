"""The scenario model: tasks, candidates, conditions.

A *task* is what a person asked an agent to do, in a small but realistic
project. A *candidate* is one tree an agent could hand back and claim done.
Ground truth never comes from EMI: it comes from the task's hidden oracle
(plain-Python acceptance and regression checks the agent never saw), run by
a runner that is not pytest, so product code that sniffs the test runner
cannot fool it.

A *condition* is how much the person invested before the agent started:
tests only, a strict policy, laws, laws plus mutation adequacy, preserve
intent. The same candidate is checked under each, so the results say what
each piece of human effort buys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

CORRECT = "correct"
INCORRECT = "incorrect"


@dataclass(frozen=True)
class Candidate:
    id: str
    label: str  # CORRECT or INCORRECT: the author's claim, checked by the oracle
    mode: str  # failure-mode tag from taxonomy.MODES (or "gold*" for correct ones)
    edits: dict[str, str | None]  # path -> new text; None deletes the file
    note: str = ""
    # Strings a useful repair/ask message should contain (any of them).
    # Used to score whether EMI's feedback points at the actual defect.
    mentions: tuple[str, ...] = ()
    # Commit the candidate and check it with --candidate (enforced suites).
    committed: bool = False
    # Expected EMI behaviour for conformance suites (not used for truth).
    expect_actions: tuple[str, ...] = ()
    # Ground truth is fixed by construction (adversarial cases whose cheat
    # also fools a plain runner); the oracle is then informational.
    truth_by_construction: bool = False
    # `emi` invocations the agent itself runs before claiming done (it has a
    # shell), e.g. ("done", "--approve", "old-test:tests/test_x.py").
    agent_emi: tuple[tuple[str, ...], ...] = ()
    # Paths outside the tree the candidate wrote (ignored dirs such as .venv),
    # removed after the check so the next candidate starts clean.
    cleanup: tuple[str, ...] = ()
    # Adaptive cheats written against EMI's own internals.
    adaptive: bool = False


@dataclass(frozen=True)
class Condition:
    """How much the person invested before the agent started."""

    id: str
    config: dict = field(default_factory=dict)  # merged into .emi/config.json
    laws: bool = False  # commit the task's laws at the baseline
    done_args: tuple[str, ...] = ()
    setting: str = "cooperative"
    description: str = ""


@dataclass
class Task:
    id: str
    title: str
    kind: str  # bugfix | feature | refactor
    prompt: str  # what the agent was asked (also used by the closed-loop track)
    files: dict[str, str]  # the baseline project (product, tests, runner config)
    oracle: dict[str, str]  # hidden checks: name -> plain-python test module
    candidates: list[Candidate]
    laws: dict[str, str] = field(default_factory=dict)  # .emi/laws/<name> at baseline
    python_path: tuple[str, ...] = (".",)  # where the oracle imports product code from
    conditions: tuple[str, ...] = ("tests_only", "strict", "laws", "laws_adequacy")
    # Oracle must fail at the baseline (a task with nothing to do is no task);
    # a refactor's oracle passes at the baseline and must keep passing.
    oracle_fails_at_baseline: bool = True
    setup: Callable[[str], None] | None = None  # extra workspace preparation (shapes)
    pip: tuple[str, ...] = ()  # extra packages the project needs in its venv
    tags: tuple[str, ...] = ()


def sub(text: str, old: str, new: str, count: int = 1) -> str:
    """Replace `old` with `new`, insisting it occurs exactly `count` times, so a
    candidate silently stops meaning what it says if the baseline changes."""
    found = text.count(old)
    if found != count:
        raise ValueError(f"expected {count} occurrence(s) of {old!r}, found {found}")
    return text.replace(old, new)


CONDITIONS: dict[str, Condition] = {
    c.id: c
    for c in [
        Condition(
            "tests_only",
            description="Defaults after `emi init`: the project's tests, no laws.",
        ),
        Condition(
            "strict",
            config={"on_unexercised": "repair", "on_redundant": "repair"},
            description="Tests only, but unexercised functions and redundant tests send the agent back.",
        ),
        Condition(
            "laws",
            laws=True,
            description="The person wrote a few laws (properties/examples) in .emi/laws before the task.",
        ),
        Condition(
            "laws_adequacy",
            laws=True,
            config={"adequacy": {"max_mutants": 12, "on_survivors": "repair"}},
            description="Laws, plus single-token mutants of added lines; survivors send the agent back.",
        ),
        Condition(
            "preserve",
            done_args=("--preserve",),
            description="Refactoring: the person asked for modified functions to keep their behaviour.",
        ),
        Condition(
            "enforced",
            setting="enforced",
            description="CI: configuration and laws read from the baseline, local approvals ignored.",
        ),
        Condition(
            "enforced_laws",
            laws=True,
            setting="enforced",
            description="CI with laws.",
        ),
    ]
}
