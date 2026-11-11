"""Read an EMI receipt into the facts the evals score."""

from __future__ import annotations

import json

EXIT_ACTION = {0: "stop", 3: "repair", 4: "ask_person", 5: "incomplete", 2: "usage_error"}


def parse(stdout: str) -> dict | None:
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        start = stdout.find("{")
        if start < 0:
            return None
        try:
            return json.loads(stdout[start:])
        except (json.JSONDecodeError, ValueError):
            return None


def _n(obj, *path) -> int:
    for p in path:
        obj = (obj or {}).get(p) if isinstance(obj, dict) else None
    return len(obj) if isinstance(obj, list) else 0


def summarize(code: int, receipt: dict | None, stderr: str = "") -> dict:
    """The facts of one check, flattened for scoring and for the report."""
    if receipt is None:
        return {
            "action": EXIT_ACTION.get(code, f"crash({code})"),
            "exit": code,
            "receipt": False,
            "error": stderr.strip()[-600:],
        }
    laws = receipt.get("laws") or {}
    law_rows = laws.get("laws") or []
    adequacy = receipt.get("adequacy") or {}
    preserve = receipt.get("preserve") or {}
    change = receipt.get("change") or {}
    regression = receipt.get("regression") or {}
    action = receipt.get("action")
    exit_matches = EXIT_ACTION.get(code) == action
    return {
        "action": action,
        "exit": code,
        "exit_matches_action": exit_matches,
        "receipt": True,
        "regression": regression.get("status"),
        "regression_failed": regression.get("failed", [])[:5],
        "missing": regression.get("missing", [])[:5],
        "quarantined": len(regression.get("quarantined") or []),
        "nondeterministic": len(regression.get("nondeterministic") or []),
        "change": change.get("status"),
        "proving": _n(change, "proving_tests"),
        "redundant": _n(change, "redundant_tests"),
        "failing": _n(change, "failing_tests"),
        "skipped": _n(change, "skipped_tests"),
        "unexercised": sum(1 for f in change.get("functions") or [] if f.get("status") == "unexercised"),
        "changed_old_tests": [f"{c.get('type')}:{c.get('path')}" for c in receipt.get("changed_old_tests") or []],
        "laws": {r.get("id", "?").split("::")[-1]: r.get("status") for r in law_rows},
        "law_every_input": {
            r.get("id", "?").split("::")[-1]: (r.get("examples") or {}).get("every_input")
            for r in law_rows if r.get("examples")
        },
        "law_proposals": len(laws.get("proposals") or []),
        "law_fault": laws.get("fault"),
        "divergences": len(preserve.get("divergences") or []) if isinstance(preserve, dict) else 0,
        "survivors": len(adequacy.get("survivors") or []) if isinstance(adequacy, dict) else 0,
        "signals": [s if isinstance(s, str) else (s.get("kind") or s.get("pattern") or json.dumps(s, sort_keys=True))
                    for s in receipt.get("signals") or []],
        "repair": receipt.get("repair") or [],
        "ask": receipt.get("ask") or [],
        "this_run": receipt.get("this_run") or [],
        "isolation": (receipt.get("assurance") or {}).get("isolation"),
        "setting": (receipt.get("assurance") or {}).get("setting"),
        "environment_identified": (receipt.get("inputs") or {}).get("environment") is not None,
        "input_id": receipt.get("input_id"),
        "decision_id": receipt.get("decision_id"),
    }


def feedback_text(s: dict) -> str:
    """Everything EMI tells the agent or the person, for mention scoring."""
    return "\n".join([*s.get("repair", []), *map(str, s.get("ask", [])), *s.get("changed_old_tests", [])])
