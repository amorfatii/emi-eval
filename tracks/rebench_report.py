"""Trial C's report: one table per pass mark, from a rebench run's raw files.

Correct and wrong are the re-graded ground truth (`resolved`), not the
dataset's label. EMI "finishes" a change when its action is `stop`; it
"catches" one when its action is `repair` or `ask_person`. `incomplete` and
crashes are neither: they are counted apart, as "could not check". The
script finishes a change when it accepts it.

usage: python -m tracks.rebench_report RESULTS_DIR > RESULTS_DIR/report.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REAL = {"stop", "repair", "ask_person"}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "0/0"


def environments(inst: list[dict]) -> list[str]:
    out = ["## Environments", "", "| Task | Usable | Why not |", "| --- | --- | --- |"]
    latest = {r["instance"]: r for r in inst}
    for iid, r in sorted(latest.items()):
        out.append(f"| {iid} | {'yes' if r['valid'] else 'no'} | {'' if r['valid'] else r['validation'].get('why', '')} |")
    return out + [""]


def works(rows: list[dict], inst: list[dict]) -> list[str]:
    usable = sorted(r["instance"] for r in {r["instance"]: r for r in inst}.values() if r["valid"])
    total = len({r["instance"] for r in inst})
    gold = {r["instance"]: r["emi"]["action"] for r in rows if r["candidate"] == "gold" and r["condition"] == "visible"}
    real = [i for i in usable if gold.get(i) in REAL]
    allc = [r for r in rows if r["condition"] in ("visible", "spec_laws")]
    real_all = [r for r in allc if r["emi"]["action"] in REAL]
    return ["## 1. Works on real projects (pass: a real answer on at least 6 of 8)", "",
            f"- Real answer on the developers' fix (visible): **{len(real)} of {total}** projects "
            f"({len(usable)} usable environments).",
            f"- Real answer over every check (both conditions): {pct(len(real_all), len(allc))}.",
            f"- Verdict: **{'pass' if len(real) >= 6 else 'fail'}**.", ""]


def speed(rows: list[dict], wss: list[dict]) -> list[str]:
    ws = {(w["instance"], w["condition"]): w for w in wss if "error" not in w}
    out = ["## 2. Fast enough (pass: a check at most 3x the project's own run, and under 5 minutes)", "",
           "| Task | Condition | Own run (s) | EMI warm-up (s) | EMI check, fix (s) | Ratio | Pass |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    passes, n = 0, 0
    for r in sorted(rows, key=lambda r: (r["instance"], r["condition"])):
        if r["candidate"] != "gold":
            continue
        w = ws.get((r["instance"], r["condition"]))
        if not w:
            continue
        own = max(w["own"]["seconds"], 0.01)
        check = r["emi"].get("seconds") or 0
        ratio = check / own
        ok = ratio <= 3 and check < 300
        if r["condition"] == "visible":
            n += 1
            passes += ok
        out.append(f"| {r['instance']} | {r['condition']} | {w['own']['seconds']} | {w['warm_seconds']} | {check} | "
                   f"{ratio:.1f}x | {'yes' if ok else 'no'} |")
    out += ["", f"- Visible condition: {passes} of {n} projects within the mark. "
            "The ratio is the check alone; the warm-up is paid once per baseline.", ""]
    return out


def behaviour_changing(rows: list[dict]) -> set[str]:
    """Tasks whose developers' fix fails the project's own existing tests:
    the fix changes behaviour those tests assert, and the hidden test patch
    rewrites them. A right fix that leaves the old tests alone fails them."""
    return {r["instance"] for r in rows if r["candidate"] == "gold" and r["condition"] == "visible"
            and r["script"] and not r["script"]["accept"]}


def honest_and_catch(rows: list[dict]) -> list[str]:
    changing = behaviour_changing(rows)
    out = ["## 3. Leaves honest work alone (pass: at least 90% of correct changes finish without a person)", "",
           f"Tasks whose correct fix fails the project's existing tests: {', '.join(sorted(changing)) or 'none'}. "
           "In those, a right fix must also change old tests, which EMI sends to a person; the agent patches here "
           "change no tests, so they fail the old ones. Rows marked *other tasks* leave them out.", "",
           "| Condition | Tasks | Correct changes | EMI finishes | Script finishes |", "| --- | --- | --- | --- | --- |"]
    for cond in ("visible", "spec_laws"):
        rs = [r for r in rows if r["condition"] == cond and r["applies"] and r["resolved"]
              and r["instance"] not in changing]
        emi_ok = sum(r["emi"]["action"] == "stop" for r in rs)
        sc_ok = sum(bool(r["script"] and r["script"]["accept"]) for r in rs)
        out.append(f"| {cond} | *other tasks* | {len(rs)} | {pct(emi_ok, len(rs))} | {pct(sc_ok, len(rs))} |")
    catch = ["## 4. Catches wrong fixes (reported; no pass mark, the sample is small)", "",
             "| Condition | Wrong changes | EMI catches | EMI could not check | Script catches |",
             "| --- | --- | --- | --- | --- |"]
    verdict = []
    for cond in ("visible", "spec_laws"):
        rs = [r for r in rows if r["condition"] == cond and r["applies"]]
        good = [r for r in rs if r["resolved"]]
        bad = [r for r in rs if r["resolved"] is False]
        emi_ok = sum(r["emi"]["action"] == "stop" for r in good)
        sc_ok = sum(bool(r["script"] and r["script"]["accept"]) for r in good)
        out.append(f"| {cond} | all | {len(good)} | {pct(emi_ok, len(good))} | {pct(sc_ok, len(good))} |")
        if cond == "visible" and good:
            verdict.append(f"- Verdict (visible, EMI): **{'pass' if emi_ok / len(good) >= 0.9 else 'fail'}**.")
        caught = sum(r["emi"]["action"] in ("repair", "ask_person") for r in bad)
        unknown = sum(r["emi"]["action"] not in REAL for r in bad)
        sc_caught = sum(bool(r["script"] and not r["script"]["accept"]) for r in bad)
        catch.append(f"| {cond} | {len(bad)} | {pct(caught, len(bad))} | {unknown} | {pct(sc_caught, len(bad))} |")
    return out + [""] + verdict + [""] + catch + [""]


def labels(rows: list[dict]) -> list[str]:
    rs = [r for r in rows if r["condition"] == "visible" and r["candidate"] != "gold"]
    agree = sum(r["applies"] and r["resolved"] == r["dataset_label"] for r in rs)
    off = [r for r in rs if not (r["applies"] and r["resolved"] == r["dataset_label"])]
    out = ["## Re-grading against the dataset's labels", "",
           f"- Agent patches whose re-graded result matches the dataset: {pct(agree, len(rs))}."]
    for r in off:
        out.append(f"  - {r['instance']} {r['candidate']} ({r['model']}): dataset "
                   f"{'resolved' if r['dataset_label'] else 'unresolved'}, here "
                   f"{'not applied' if not r['applies'] else ('resolved' if r['resolved'] else 'unresolved')}")
    return out + [""]


def repeat(rows: list[dict]) -> list[str]:
    rs = [r for r in rows if "repeat_same_decision" in r]
    same = sum(bool(r["repeat_same_decision"]) for r in rs)
    out = ["## Same input, same decision", "", f"- Developers' fix checked twice from fresh state: {pct(same, len(rs))} identical."]
    for r in rs:
        if not r["repeat_same_decision"]:
            out.append(f"  - {r['instance']} {r['condition']}: {r['emi']['action']} then {r['repeat_action']}")
    return out + [""]


def cases(rows: list[dict], wss: list[dict]) -> list[str]:
    out = ["## Where EMI and the script disagree", ""]
    for r in sorted(rows, key=lambda r: (r["instance"], r["condition"], r["candidate"])):
        if not r["script"] or not r["applies"]:
            continue
        emi_finish = r["emi"]["action"] == "stop"
        if emi_finish == r["script"]["accept"]:
            continue
        truth = "correct" if r["resolved"] else "wrong"
        said = (r["emi"].get("repair") or r["emi"].get("ask") or [r["emi"].get("error", "")])[:2]
        out.append(f"- {r['instance']} / {r['condition']} / {r['candidate']} ({truth}): EMI {r['emi']['action']}, "
                   f"script {'accept' if r['script']['accept'] else 'reject'} ({r['script']['why']}). "
                   f"EMI said: {json.dumps(said)[:400]}")
    out += ["", "## Could not check", ""]
    for r in rows:
        if r["emi"]["action"] not in REAL and r["emi"]["action"] != "not_applied":
            why = (r["emi"].get("this_run") or r["emi"].get("repair") or [r["emi"].get("error", "")])
            out.append(f"- {r['instance']} / {r['condition']} / {r['candidate']}: {r['emi']['action']}: "
                       f"{json.dumps(why)[:400]}")
    for w in wss:
        if "error" in w:
            out.append(f"- {w['instance']} / {w['condition']}: workspace not built: {w['error'][:300]}")
    return out + [""]


def main(d: str) -> int:
    root = Path(d)
    rows, inst, wss = load(root / "results.jsonl"), load(root / "instances.jsonl"), load(root / "workspaces.jsonl")
    inst = [i for i in inst if i.get("command") == "run"] or inst
    by_cond = defaultdict(int)
    for r in rows:
        by_cond[r["condition"]] += 1
    lines = ["# Trial C: eight real projects", "",
             f"{len(rows)} checks ({', '.join(f'{k} {v}' for k, v in sorted(by_cond.items()))}).", ""]
    for part in (environments(inst), works(rows, inst), speed(rows, wss), honest_and_catch(rows),
                 labels(rows), repeat(rows), cases(rows, wss)):
        lines += part
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
