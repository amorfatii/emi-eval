# How to write the rules ("laws")

Rules are plain pytest files that will be placed in the project's `.emi/laws/`
folder and run from the project root with `python -m pytest .emi/laws`.
`pytest.ini` puts the project root on the import path, so import product code
as the baseline tests do (for example `from textutil import slugify`).
Available packages: the standard library, `pytest` and `hypothesis` (version 6). Nothing else.

A rule is one test function, or one Hypothesis `RuleBasedStateMachine`
(exported as `TestSomething = Something.TestCase`). Use:
- plain examples: `def test_...(): assert f(x) == y`;
- Hypothesis properties: `@given(...)`;
- Hypothesis state machines for objects with several operations.

Directly above every rule put exactly two comment lines:

    # <one plain-language sentence saying what the rule requires>
    # Source: "<the exact words of the request, or the answer, this rule comes from>"

If the rule keeps behaviour the baseline already has and the request does not
ask to change, write `# Source: baseline behaviour, not asked to change: <which>`.

The rules are written before any code exists. They run against the baseline
(where the rules about the requested change are expected to fail) and later
against the agent's finished change. A rule must fail on wrong work and pass on
every correct solution. A rule that rejects a correct solution is a serious
error: it would stop a correct agent from finishing. Do not depend on internal
names, helper functions, exact error messages, or anything the request leaves
open, unless the answers (where you have them) settle it.

Keep Hypothesis runs cheap (default settings or `max_examples` up to 200; no
`deadline` problems: use `@settings(deadline=None)` on properties that call slow code).
Name files `test_<something>_laws.py`. One or two files per task.
