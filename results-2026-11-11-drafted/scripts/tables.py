"""Make every table in REPORT.md from the raw rows. Prints Markdown.

Usage (from the repository root):
  python results-2026-11-11-drafted/scripts/tables.py > results-2026-11-11-drafted/tables.md

Reads raw/<run>/results.jsonl and truth.jsonl (EMI's decision and the oracle
truth with the comparison gates), raw/vacuity.jsonl, raw/timing/*,
raw/typecheck.jsonl, and the question, answer and rule files.
"""
from __future__ import annotations

import ast
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RAW = HERE / "raw"
DRAFTED = ("drafted_no_questions", "drafted_questions")
SHORT = {"tests_only": "tests_only", "laws": "laws (hand-written)",
         "drafted_no_questions": "A drafted_no_questions", "drafted_questions": "B drafted_questions"}
SLIPPED = ["t01_slugify/drops_digits", "t01_slugify/forgets_sep", "t03_business_days/generator_consumed",
           "t03_business_days/subtracts_all_holidays", "t04_order_cancel/cancels_shipped",
           "t04_order_cancel/drops_pay_history", "t04_order_cancel/wrong_exception", "t07_backoff_cap/cap_only",
           "t09_semver/no_padding", "t10_median/sorts_in_place"]
FAILING = ("unmet", "broken", "stopped")

# The runner's reading (not the Drafter's) of whether a question asked in B
# touches the case a slipped candidate gets wrong. Question ids are per task.
TOUCHES = {
    "t01_slugify/drops_digits": ([], "no question about digits"),
    "t01_slugify/forgets_sep": ([], "Q3 asks about sep='' only, not whether a custom separator is stripped from the ends"),
    "t03_business_days/generator_consumed": ([], "no question about holidays given as a generator"),
    "t03_business_days/subtracts_all_holidays": (["Q2"], "Q2 (a holiday listed twice) separates it: this candidate counts the duplicate twice; answered \"doesn't matter\""),
    "t04_order_cancel/cancels_shipped": (["Q3"], "Q3 asks what a refused cancel of a shipped order leaves behind"),
    "t04_order_cancel/drops_pay_history": (["Q2"], "Q2 asks for the history after cancel(pay(order)): ['paid', 'cancelled']"),
    "t04_order_cancel/wrong_exception": (["Q3"], "Q3 presupposes OrderError on a shipped order; only indirectly"),
    "t07_backoff_cap/cap_only": ([], "no question about negative attempts (the request already settles it)"),
    "t09_semver/no_padding": ([], "Q4 is about extra components; padding is settled by the request"),
    "t10_median/sorts_in_place": ([], "no question about changing the caller's list or tuple input"),
}


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def runs() -> dict[str, list[dict]]:
    """Rows per condition, joined with the oracle truth and the gates of the same run."""
    out = defaultdict(list)
    for d in ("tests_only_and_laws", *DRAFTED):
        truth = {(r["task"], r["candidate"]): r for r in load(RAW / d / "truth.jsonl") if r["candidate"] != "<baseline>"}
        for r in load(RAW / d / "results.jsonl"):
            t = truth[(r["task"], r["candidate"])]
            out[r["condition"]].append({**r, "truth": t["truth"], "label_ok": t["label_ok"], "gates": t["gates"]})
    return out


def rule_of(law_id: str) -> str:
    """'.emi/laws/f.py::TestM::runTest' -> 'f.py::TestM'; 'f.py::test_x[True]' -> 'f.py::test_x'."""
    rid = law_id.split("/")[-1].split("[")[0]
    return rid[: -len("::runTest")] if rid.endswith("::runTest") else rid


def failing_rules(row: dict) -> list[str]:
    laws = ((row["emi"].get("raw") or {}).get("laws") or {}).get("laws") or []
    return sorted({rule_of(x["id"]) for x in laws if x.get("status") in FAILING})


def rule_meta(cond: str) -> dict[tuple[str, str], dict]:
    """(task, 'file::rule') -> {'says': ..., 'source': ...} from the two comment lines above each rule."""
    meta = {}
    for task_dir in sorted((HERE / "laws" / cond).iterdir()):
        for f in sorted(task_dir.glob("*.py")):
            lines = f.read_text().splitlines()
            tree = ast.parse(f.read_text())
            machines, assign_line = {}, {}
            for node in tree.body:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and node.value.attr == "TestCase":
                    machines[node.value.value.id] = node.targets[0].id
                    assign_line[node.value.value.id] = node.lineno
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    name = node.name
                elif isinstance(node, ast.ClassDef) and node.name in machines:
                    name = machines[node.name]
                else:
                    continue
                first = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
                comments = []
                i = first - 1
                while i >= 0 and lines[i].lstrip().startswith("#"):
                    comments.insert(0, lines[i].lstrip("# ").rstrip())
                    i -= 1
                if not comments and isinstance(node, ast.ClassDef):  # comment put above `TestX = X.TestCase`
                    i = assign_line[node.name] - 2
                    while i >= 0 and lines[i].lstrip().startswith("#"):
                        comments.insert(0, lines[i].lstrip("# ").rstrip())
                        i -= 1
                src = next((c for c in comments if c.startswith("Source:")), "")
                says = " ".join(c for c in comments if not c.startswith("Source:"))
                meta[(task_dir.name, f"{f.name}::{name}")] = {"says": says, "source": src[len("Source:"):].strip()}
    return meta


def frac(k, n):
    return f"{k}/{n}"


def score(rows, act=lambda r: r["emi"]["action"]):
    rows = [r for r in rows if r["label_ok"]]
    bad = [r for r in rows if r["truth"] == "incorrect"]
    ok = [r for r in rows if r["truth"] == "correct"]
    return (sum(act(r) != "stop" for r in bad), len(bad), sum(act(r) == "stop" for r in ok), len(ok))


def gate_score(rows, gate):
    rows = [r for r in rows if r["label_ok"] and gate in r["gates"]]
    if not rows:
        return None
    return score(rows, act=lambda r: "stop" if r["gates"][gate]["accept"] else "reject")


def main() -> None:
    R = runs()
    L = []
    p = L.append
    conds = ["tests_only", "laws", *DRAFTED]
    nine = lambda rows: [r for r in rows if r["task"] != "t08_pricing_refactor"]  # noqa: E731

    p("## Table 1. Catch and accept counts\n")
    p("Catch = incorrect candidates EMI did not let finish (anything but `stop`). "
      "Accept = correct candidates EMI let finish (`stop`). `restore_laws` = restore the baseline's tests, "
      "run them and the same laws with pytest; accept if both pass.\n")
    p("| condition | tasks | EMI catch | EMI accept | restore_laws catch | restore_laws accept | restore (no laws) catch | restore accept |")
    p("|---|---|---|---|---|---|---|---|")
    for c in conds:
        for label, sel in (("all 10", lambda x: x), ("9 with hand-written laws", nine)):
            rows = sel(R[c])
            if c == "laws" and label == "all 10":
                continue
            if not rows:
                continue
            k, n, a, m = score(rows)
            g = gate_score(rows, "restore_laws") if c != "tests_only" else None
            rs = gate_score(rows, "restore")
            gl = f"{frac(g[0], g[1])} | {frac(g[2], g[3])}" if g else "– | –"
            p(f"| {SHORT[c]} | {label} | {frac(k, n)} | {frac(a, m)} | {gl} | {frac(rs[0], rs[1])} | {frac(rs[2], rs[3])} |")
    p("")

    # Table 2: the ten slipped candidates
    meta = {c: rule_meta(c) for c in DRAFTED}
    by = {c: {(r["task"], r["candidate"]): r for r in R[c]} for c in conds}
    p("## Table 2. The 10 incorrect candidates that slipped under the strongest condition on 2026-11-11\n")
    p("| candidate | laws (this build) | A | rules in A that fail on it | B | rules in B that fail on it |")
    p("|---|---|---|---|---|---|")
    caught = {c: 0 for c in DRAFTED}
    for s in SLIPPED:
        k = tuple(s.split("/"))
        cells = [s, by["laws"][k]["emi"]["action"]]
        for c in DRAFTED:
            r = by[c][k]
            act = r["emi"]["action"]
            caught[c] += act != "stop"
            fr = failing_rules(r)
            cells += [f"**{act}**" if act != "stop" else act, "<br>".join(
                f"`{x.split('::', 1)[1]}`: {meta[c].get((k[0], x), {}).get('says', '?')}" for x in fr) or "–"]
        p("| " + " | ".join(cells) + " |")
    p("")
    p("Caught out of 10: " + ", ".join(f"{SHORT[c]} {caught[c]}" for c in DRAFTED) + ".\n")

    # Table 3: correct candidates not allowed to finish, and wrong rules
    p("## Table 3. Correct candidates not allowed to finish, and wrong rules\n")
    wrong = {c: defaultdict(set) for c in DRAFTED}
    for c in ("laws", *DRAFTED):
        rows = [r for r in R[c] if r["label_ok"] and r["truth"] == "correct" and r["emi"]["action"] != "stop"]
        p(f"**{SHORT[c]}**: {len(rows)} blocked.\n")
        for r in rows:
            fr = failing_rules(r)
            reason = (r["emi"].get("repair") or r["emi"].get("ask") or [""])[0]
            reason = reason if isinstance(reason, str) else json.dumps(reason)
            p(f"- {r['task']}/{r['candidate']} → **{r['emi']['action']}**; failing rules: "
              f"{', '.join('`' + x + '`' for x in fr) or 'none'}; EMI says: {reason[:240]}")
            if c in DRAFTED:
                for x in fr:
                    wrong[c][(r["task"], x)].add(r["candidate"])
        # the gate too: correct candidates restore_laws rejects
        g = [r for r in R[c] if r["label_ok"] and r["truth"] == "correct" and "restore_laws" in r["gates"]
             and not r["gates"]["restore_laws"]["accept"]]
        if g:
            p(f"- restore_laws gate rejects {len(g)} correct: " +
              "; ".join(f"{r['task']}/{r['candidate']} ({r['gates']['restore_laws']['why'][:80]})" for r in g))
        p("")
    for c in DRAFTED:
        p(f"**Wrong rules in {SHORT[c]}: {len(wrong[c])}**\n")
        for (task, rid), cands in sorted(wrong[c].items()):
            m = meta[c].get((task, rid), {})
            p(f"- `{task}/{rid}` (fails on {', '.join(sorted(cands))}). Says: \"{m.get('says', '?')}\" "
              f"Came from: {m.get('source', '?')}")
        p("")

    # Table 4: B, questions and the slipped candidates
    p("## Table 4. B: did a question touch the case each slipped candidate gets wrong?\n")
    answers = {}
    for f in sorted((HERE / "answers").glob("*.md")):
        for line in f.read_text().splitlines():
            m = re.match(r"(Q\d+): (.*)", line)
            if m:
                answers[(f.stem, m[1])] = m[2].strip()
    p("| candidate | question that touches it | answer | caught by B? |")
    p("|---|---|---|---|")
    for s in SLIPPED:
        qs, why = TOUCHES[s]
        task = s.split("/")[0]
        ans = ", ".join(f"{q}: {answers.get((task, q), '?')}" for q in qs) or "–"
        act = by["drafted_questions"][tuple(s.split("/"))]["emi"]["action"]
        p(f"| {s} | {why} | {ans} | {'yes (' + act + ')' if act != 'stop' else 'no'} |")
    p("")
    p("### Did each answer lead to a rule?\n")
    srcs = defaultdict(list)
    for (task, rid), m in meta["drafted_questions"].items():
        for q in re.findall(r"\bQ(\d+)\b", m["source"]):
            srcs[(task, f"Q{q}")].append(rid.split("::")[1])
    p("| task | question | answer | rules citing it |")
    p("|---|---|---|---|")
    for (task, q), a in sorted(answers.items()):
        p(f"| {task} | {q} | {a} | {', '.join('`' + x + '`' for x in srcs.get((task, q), [])) or '–'} |")
    p("")
    n_q = len(answers)
    n_dm = sum(a == "doesn't matter" for a in answers.values())
    n_led = sum(bool(srcs.get(k)) for k in answers)
    p(f"{n_q} questions; {n_q - n_dm} answered with a letter, {n_dm} \"doesn't matter\"; {n_led} led to a rule.\n")

    # Table 5: rules per task, vacuity, time
    p("## Table 5. Rules per task, vacuous rules, check time\n")
    vac = load(RAW / "vacuity.jsonl")
    vt = defaultdict(lambda: [0, 0, 0, 0])  # rules, vacuous, untouched, failing on gold
    for v in vac:
        x = vt[(v["set"], v["task"])]
        x[0] += 1
        x[1] += v["vacuous"]
        x[2] += v["untouched"]
        x[3] += v["on_gold"] != "passed"
    tasks = sorted({v["task"] for v in vac})
    p("Cells: rules / vacuous / not depending on the function under test at all. "
      "Vacuous = still passes when a function it depends on is given a trivial body (EMI's four stand-ins).\n")
    p("| task | hand-written laws | A | B |")
    p("|---|---|---|---|")
    tot = defaultdict(lambda: [0, 0, 0, 0])
    for t in tasks:
        cells = []
        for s in ("laws", *DRAFTED):
            x = vt.get((s, t))
            if x:
                for i in range(4):
                    tot[s][i] += x[i]
            cells.append(f"{x[0]} / {x[1]} / {x[2]}" + (f" ({x[3]} fail on gold)" if x and x[3] else "") if x else "–")
        p(f"| {t} | " + " | ".join(cells) + " |")
    p("| **total** | " + " | ".join(f"**{tot[s][0]} / {tot[s][1]} / {tot[s][2]}**" for s in ("laws", *DRAFTED)) + " |")
    p("")
    p("Vacuous rules, one by one:\n")
    for v in vac:
        if v["vacuous"]:
            p(f"- {v['set']} {v['task']} `{v['rule']}` passes under: {', '.join(v['vacuous_under'])}")
    p("")

    p("### How long a check takes\n")
    p("Seconds per `emi done`, median and 90th percentile. The main runs shared 4 cores with other runs "
      "(timings inflated). The timing pass ran each gold candidate alone, one at a time.\n")
    p("| condition | main run median | main run p90 | timing pass median (10 gold candidates, one at a time) |")
    p("|---|---|---|---|")
    timing = {}
    for d in (RAW / "timing").glob("*") if (RAW / "timing").exists() else []:
        for r in load(d / "results.jsonl"):
            timing.setdefault(r["condition"], []).append(r["emi"]["seconds"])
    for c in conds:
        secs = sorted(r["emi"]["seconds"] for r in R[c] if isinstance(r["emi"].get("seconds"), (int, float)))
        tp = timing.get(c)
        p(f"| {SHORT[c]} | {statistics.median(secs):.1f} | {secs[int(0.9 * (len(secs) - 1))]:.1f} | "
          f"{f'{statistics.median(tp):.1f} (n={len(tp)})' if tp else '–'} |")
    p("")

    # Table 6: type checkers
    p("## Table 6. Type checkers (mypy and pyright, default settings)\n")
    tc = load(RAW / "typecheck.jsonl")
    base = [r for r in tc if r["candidate"] == "<baseline>"]
    p(f"Baselines with errors: " + ", ".join(f"{r['task']} ({len(r['errors'])})" for r in base if r["errors"]) + ".\n")
    cands = [r for r in tc if r["candidate"] != "<baseline>"]
    p("| checker | correct candidates flagged | incorrect candidates flagged |")
    p("|---|---|---|")
    for ch in ("mypy", "pyright", "either"):
        def hit(r):
            return bool(r["new_errors"]) if ch == "either" else bool(r["new_by_checker"].get(ch))
        ok = [r for r in cands if r["label"] == "correct"]
        bad = [r for r in cands if r["label"] == "incorrect"]
        p(f"| {ch} | {sum(map(hit, ok))}/{len(ok)} | {sum(map(hit, bad))}/{len(bad)} |")
    p("")
    p("Every flagged candidate and the new message:\n")
    for r in cands:
        for e in r["new_errors"]:
            p(f"- {r['label']} {r['task']}/{r['candidate']}: {e['checker']} `{e['file']}:{e['line']}` "
              f"[{e['code']}] {e['message']}")
    slipped_flagged = [s for s in SLIPPED if any(r["new_errors"] for r in cands if f"{r['task']}/{r['candidate']}" == s)]
    p(f"\nOf the 10 slipped candidates, type checkers flag: {', '.join(slipped_flagged) or 'none'}.")
    print("\n".join(L))


if __name__ == "__main__":
    main()
