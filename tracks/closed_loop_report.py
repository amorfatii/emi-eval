"""Trial E's report: the four setups side by side, and the two comparisons.

usage: python -m tracks.closed_loop_report RESULTS_DIR > RESULTS_DIR/report.md
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

SETUPS = ("none", "script", "emi", "emi_rules")


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "0/0"


def main(d: str) -> int:
    rows = [json.loads(line) for line in (Path(d) / "runs.jsonl").read_text().splitlines() if line.strip()]
    by = {s: [r for r in rows if r["setup"] == s] for s in SETUPS}
    out = ["# Trial E: a real agent, four ways", "",
           f"{len(rows)} runs over {len({r['task'] for r in rows})} tasks; model(s): "
           f"{', '.join(sorted({m for r in rows for m in r.get('models_used') or []}))}.", "",
           "| Setup | Runs | Wrong \"done\" accepted | Wrong, not caught | Ended correct | Correct, not accepted "
           "| Could not check | Sent to person | Sent back (mean) | Useful / wrong send-backs | Tokens (median) | Cost (mean) |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s, rs in by.items():
        if not rs:
            continue
        useful = sum(lbl == "useful" for r in rs for lbl in r["send_backs"])
        wrong = sum(lbl == "wrong" for r in rs for lbl in r["send_backs"])
        last = [r.get("last_checker_action") for r in rs]
        uncaught = sum((not r["final_correct"]) and (r["accepted"] or r.get("last_checker_action") == "incomplete")
                       for r in rs)
        out.append(f"| {s} | {len(rs)} | {pct(sum(r['wrong_done'] for r in rs), len(rs))} | {pct(uncaught, len(rs))} | "
                   f"{pct(sum(r['final_correct'] for r in rs), len(rs))} | "
                   f"{sum(r['final_correct'] and not r['accepted'] for r in rs)} | "
                   f"{last.count('incomplete')} | {last.count('ask_person')} | "
                   f"{statistics.mean(r['sent_back'] for r in rs):.1f} | {useful} / {wrong} | "
                   f"{int(statistics.median(r['tokens_in'] for r in rs)):,} | "
                   f"${statistics.mean((r['cost_usd'] or 0) for r in rs):.2f} |")
    out.append("")

    def pair(a: str, b: str) -> list[str]:
        key = lambda r: (r["task"], r["run"])  # noqa: E731
        A, B = {key(r): r for r in by[a]}, {key(r): r for r in by[b]}
        both = sorted(set(A) & set(B))
        if not both:
            return [f"- {a} vs {b}: no paired runs.", ""]
        wa, wb = sum(A[k]["wrong_done"] for k in both), sum(B[k]["wrong_done"] for k in both)
        nc = lambda r: (not r["final_correct"]) and (r["accepted"] or r.get("last_checker_action") == "incomplete")  # noqa: E731
        ua, ub = sum(nc(A[k]) for k in both), sum(nc(B[k]) for k in both)
        ca, cb = sum(A[k]["final_correct"] for k in both), sum(B[k]["final_correct"] for k in both)
        ta = statistics.median(A[k]["tokens_in"] for k in both)
        tb = statistics.median(B[k]["tokens_in"] for k in both)
        return [f"- **{a} vs {b}** ({len(both)} paired runs): wrong \"done\" accepted {wa} vs {wb}; "
                f"wrong and not caught {ua} vs {ub}; "
                f"ended correct {ca} vs {cb}; median tokens {int(ta):,} vs {int(tb):,} "
                f"({100 * (ta / tb - 1):+.0f}%)." if tb else "", ""]

    out += ["## Comparisons", ""]
    out += pair("emi", "script")
    out += ["  Pass mark: wrong \"done\" at least a third less often than the script, ended correct no less "
            "often, at most 30% more tokens.", ""]
    out += pair("emi_rules", "emi")
    out += pair("script", "none")
    flagged = [r for r in rows if r.get("touched_lab") or r.get("timed_out")]
    out += ["## Runs to look at", ""]
    out += [f"- {r['task']} / {r['setup']} / run {r['run']}: "
            f"{'read this lab' if r.get('touched_lab') else ''}{' timed out' if r.get('timed_out') else ''}"
            for r in flagged] or ["- none"]
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
