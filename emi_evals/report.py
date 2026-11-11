"""Score a results directory into summary.json and report.md.

Definitions (per condition, over candidates whose oracle label is valid):

  catch rate      P(action != stop | incorrect)   false completions EMI stops
  slip rate       P(action == stop | incorrect)   false completions that get through
  accept rate     P(action == stop | correct)     correct work EMI lets finish
  friction        P(action != stop | correct)     split into repair (EMI was wrong to
                                                  send it back, or demanded more evidence),
                                                  ask_person (escalation) and incomplete
  stop precision  P(correct | stop)               how much a `stop` is worth
  feedback hit    among caught incorrect candidates with known defect markers,
                  how often EMI's repair/ask text names one of them
Gates (naive_ci, restore, restore_laws) get the same catch/accept rates on the
same candidates, so EMI's lift over "CI is green" is explicit.
Rates carry 95% Wilson intervals: with tens of candidates, they are wide.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .receipt import feedback_text
from .taxonomy import MODES, family


def wilson(k: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def pct(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    p, lo, hi = wilson(k, n)
    return f"{100 * p:.0f}% ({k}/{n}; {100 * lo:.0f}–{100 * hi:.0f})"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _join(results: list[dict], truth: list[dict]) -> list[dict]:
    t = {(r["task"], r["candidate"]): r for r in truth if r["candidate"] != "<baseline>"}
    out = []
    for r in results:
        tr = t.get((r["task"], r["candidate"]))
        if tr is None:
            continue
        out.append({**r, "truth": tr["truth"], "label_ok": tr["label_ok"], "gates": tr["gates"],
                    "oracle_failed": tr["oracle"]["failed"]})
    return out


def score_condition(rows: list[dict]) -> dict:
    bad = [r for r in rows if r["truth"] == "incorrect"]
    ok = [r for r in rows if r["truth"] == "correct"]
    act = lambda r: r["emi"].get("action")  # noqa: E731
    caught = [r for r in bad if act(r) != "stop"]
    stops = [r for r in rows if act(r) == "stop"]
    with_markers = [r for r in caught if r.get("mentions")]
    hits = [r for r in with_markers if any(m in feedback_text(r["emi"]) for m in r["mentions"])]
    secs = [r["emi"].get("seconds") for r in rows if isinstance(r["emi"].get("seconds"), (int, float))]
    return {
        "n": len(rows), "n_correct": len(ok), "n_incorrect": len(bad),
        "catch": (len(caught), len(bad)),
        "catch_by_action": dict(Counter(act(r) for r in caught)),
        "accept": (sum(1 for r in ok if act(r) == "stop"), len(ok)),
        "friction_by_action": dict(Counter(act(r) for r in ok if act(r) != "stop")),
        "stop_precision": (sum(1 for r in stops if r["truth"] == "correct"), len(stops)),
        "feedback_hit": (len(hits), len(with_markers)),
        "seconds_median": round(statistics.median(secs), 1) if secs else None,
        "seconds_p90": round(sorted(secs)[int(0.9 * (len(secs) - 1))], 1) if secs else None,
        "crashes": sum(1 for r in rows if not r["emi"].get("receipt")),
        "exit_mismatch": sum(1 for r in rows if r["emi"].get("receipt") and not r["emi"].get("exit_matches_action")),
    }


def score_gate(rows: list[dict], gate: str) -> dict | None:
    rows = [r for r in rows if gate in r["gates"]]
    if not rows:
        return None
    bad = [r for r in rows if r["truth"] == "incorrect"]
    ok = [r for r in rows if r["truth"] == "correct"]
    return {"catch": (sum(1 for r in bad if not r["gates"][gate]["accept"]), len(bad)),
            "accept": (sum(1 for r in ok if r["gates"][gate]["accept"]), len(ok))}


def _first_reason(e: dict) -> str:
    for key in ("repair", "ask"):
        if e.get(key):
            v = e[key][0]
            return (v if isinstance(v, str) else json.dumps(v))[:220]
    if e.get("changed_old_tests"):
        return "waits for approval: " + ", ".join(e["changed_old_tests"])
    if e.get("this_run"):
        return e["this_run"][0][:220]
    return e.get("error", "")[:220]


def discrimination(out: Path) -> dict | None:
    rows = _join(load(out / "results.jsonl"), load(out / "truth.jsonl"))
    rows = [r for r in rows if r.get("suite", "discrimination") == "discrimination"]
    if not rows:
        return None
    invalid = sorted({(r["task"], r["candidate"]) for r in rows if not r["label_ok"]})
    rows = [r for r in rows if r["label_ok"]]
    by_cond = defaultdict(list)
    for r in rows:
        by_cond[r["condition"]].append(r)
    order = [c for c in ("tests_only", "strict", "laws", "laws_adequacy", "preserve") if c in by_cond]
    conds = {c: score_condition(by_cond[c]) for c in order}

    # gates on the same candidate set as each condition
    gates = {}
    for c in order:
        gates[c] = {g: score_gate(by_cond[c], g) for g in ("naive_ci", "restore", "restore_laws")}

    # mode x condition: how often an incorrect candidate of this mode slips (stop)
    mode_tab = defaultdict(dict)
    for c in order:
        groups = defaultdict(list)
        for r in by_cond[c]:
            groups[r["mode"]].append(r)
        for m, rs in groups.items():
            stop = sum(1 for r in rs if r["emi"].get("action") == "stop")
            mode_tab[m][c] = (stop, len(rs))
    gate_by_mode = defaultdict(dict)
    for m in mode_tab:
        rs = [r for r in by_cond[order[0]] if r["mode"] == m]
        for g in ("naive_ci", "restore"):
            gate_by_mode[m][g] = (sum(1 for r in rs if r["gates"][g]["accept"]), len(rs))

    strongest = {}
    for r in rows:
        k = (r["task"], r["candidate"])
        rank = order.index(r["condition"])
        if k not in strongest or rank > order.index(strongest[k]["condition"]):
            strongest[k] = r
    slips = [{"task": r["task"], "candidate": r["candidate"], "mode": r["mode"], "condition": r["condition"],
              "why_wrong": "; ".join(f"{k}: {v}" for k, v in list(r["oracle_failed"].items())[:2])[:260]}
             for r in strongest.values() if r["truth"] == "incorrect" and r["emi"].get("action") == "stop"]
    friction = [{"task": r["task"], "candidate": r["candidate"], "mode": r["mode"], "condition": r["condition"],
                 "action": r["emi"].get("action"), "reason": _first_reason(r["emi"])}
                for r in rows if r["truth"] == "correct" and r["emi"].get("action") != "stop"]
    # what each extra investment changed, candidate by candidate
    transitions = {}
    base = {(r["task"], r["candidate"]): r for r in by_cond.get("tests_only", [])}
    for c in order[1:]:
        newly_caught, newly_blocked = [], []
        for r in by_cond[c]:
            b = base.get((r["task"], r["candidate"]))
            if not b:
                continue
            if r["truth"] == "incorrect" and b["emi"]["action"] == "stop" and r["emi"]["action"] != "stop":
                newly_caught.append(f"{r['task']}/{r['candidate']}")
            if r["truth"] == "correct" and b["emi"]["action"] == "stop" and r["emi"]["action"] != "stop":
                newly_blocked.append(f"{r['task']}/{r['candidate']}")
        transitions[c] = {"newly_caught": newly_caught, "newly_blocked_correct": newly_blocked}
    every_input_claims = []
    for r in rows:
        for law, claim in (r["emi"].get("law_every_input") or {}).items():
            if claim and r["emi"]["laws"].get(law) in ("unmet", "broken"):
                every_input_claims.append(f"{r['task']}/{r['candidate']}/{r['condition']}: {law}")
    return {"conditions": conds, "gates": gates, "modes": dict(mode_tab), "gate_by_mode": dict(gate_by_mode),
            "slips": slips, "friction": friction, "transitions": transitions, "invalid_labels": invalid,
            "every_input_on_failing_law": every_input_claims, "order": order}


def adversarial(out: Path) -> dict | None:
    rows = [r for r in load(out / "results.jsonl") if r.get("suite") == "adversarial"]
    if not rows:
        return None
    truth = {r["candidate"]: r for r in load(out / "truth.jsonl") if r.get("task", "").startswith("a")}
    table = defaultdict(dict)
    for r in rows:
        table[r["candidate"]][r["condition"]] = {
            "action": r["emi"].get("action"), "signals": r["emi"].get("signals", []),
            "reason": _first_reason(r["emi"])}
    meta = {r["candidate"]: {"mode": r["mode"], "label": r["label"]} for r in rows}
    gates = {c: {g: v["accept"] for g, v in t.get("gates", {}).items()} for c, t in truth.items()}
    escapes = defaultdict(lambda: [0, 0])
    from suites.adversarial import CANDIDATES  # tier lives in the note
    tier = {c.id: (c.note.split("]")[0].strip("[") if c.note.startswith("[") else "control") for c in CANDIDATES}
    for cid, conds in table.items():
        if meta[cid]["label"] != "incorrect":
            continue
        for cond, v in conds.items():
            escapes[(tier.get(cid, "?"), cond)][1] += 1
            if v["action"] == "stop":
                escapes[(tier.get(cid, "?"), cond)][0] += 1
    return {"table": dict(table), "meta": meta, "tier": tier, "gates": gates,
            "escapes": {f"{t}|{c}": v for (t, c), v in escapes.items()}}


def shapes(out: Path) -> dict | None:
    rows = [r for r in load(out / "results.jsonl") if r.get("suite") == "shapes"]
    if not rows:
        return None
    res = []
    for r in rows:
        e = r["emi"]
        res.append({"shape": r["task"], "candidate": r["candidate"], "expected": r["expect_actions"],
                    "action": e.get("action"), "ok": e.get("action") in r["expect_actions"],
                    "seconds": e.get("seconds"), "warm_seconds": r.get("warm_seconds"),
                    "env_identified": e.get("environment_identified"), "reason": _first_reason(e)})
    return {"rows": sorted(res, key=lambda x: (x["shape"], x["candidate"]))}


def determinism(out: Path) -> dict | None:
    rows = load(out / "determinism.jsonl")
    if not rows:
        return None
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        by[r["check"]][1] += 1
        by[r["check"]][0] += bool(r["pass"])
    return {"by_check": dict(by), "failures": [r for r in rows if not r["pass"]], "rows": rows}


def write_report(out: Path) -> dict:
    summary = {"discrimination": discrimination(out), "adversarial": adversarial(out),
               "shapes": shapes(out), "determinism": determinism(out)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=list))
    (out / "report.md").write_text(render(summary))
    return summary


def render(s: dict) -> str:
    L = ["# EMI evaluation report", ""]
    d = s.get("discrimination")
    if d:
        L += ["## Discrimination: does `stop` mean the work is right?", "",
              "| condition | catch rate (incorrect → not stop) | accept rate (correct → stop) | stop precision | feedback names the defect | median s |",
              "|---|---|---|---|---|---|"]
        for c in d["order"]:
            x = d["conditions"][c]
            L.append(f"| {c} | {pct(*x['catch'])} | {pct(*x['accept'])} | {pct(*x['stop_precision'])} | "
                     f"{pct(*x['feedback_hit'])} | {x['seconds_median']} |")
        L += ["", "Comparison gates on the same candidates:", "", "| condition set | gate | catch | accept |", "|---|---|---|---|"]
        for c in d["order"]:
            for g, v in d["gates"][c].items():
                if v:
                    L.append(f"| {c} | {g} | {pct(*v['catch'])} | {pct(*v['accept'])} |")
        L += ["", "### Slip rate by failure mode (stop / candidates)", "",
              "| mode | family | " + " | ".join(d["order"]) + " | naive CI accepts |", "|---|---|" + "---|" * (len(d["order"]) + 1)]
        for m in sorted(d["modes"], key=lambda m: (family(m), m)):
            cells = [f"{d['modes'][m][c][0]}/{d['modes'][m][c][1]}" if c in d["modes"][m] else "–" for c in d["order"]]
            g = d["gate_by_mode"].get(m, {}).get("naive_ci", (0, 0))
            L.append(f"| {m} | {family(m)} | " + " | ".join(cells) + f" | {g[0]}/{g[1]} |")
        L += ["", "### Incorrect work that still gets `stop` under the strongest condition", ""]
        for x in d["slips"]:
            L.append(f"- **{x['task']}/{x['candidate']}** ({x['mode']}, {x['condition']}): {x['why_wrong']}")
        L += ["", "### Correct work EMI did not let finish", ""]
        for x in d["friction"]:
            L.append(f"- {x['task']}/{x['candidate']} ({x['mode']}, {x['condition']}) → **{x['action']}**: {x['reason']}")
        if d["every_input_on_failing_law"]:
            L += ["", "### `every_input: true` reported on failing laws", ""] + [f"- {x}" for x in d["every_input_on_failing_law"]]
    a = s.get("adversarial")
    if a:
        conds = sorted({c for v in a["table"].values() for c in v})
        L += ["", "## Adversarial: cheats that hide a broken change", "",
              "| cheat | tier | " + " | ".join(conds) + " | naive CI | restore |", "|---|---|" + "---|" * (len(conds) + 2)]
        for cid, v in a["table"].items():
            g = a["gates"].get(cid, {})
            cells = [(v[c]["action"] + (" ⚑" if v[c]["signals"] else "")) if c in v else "–" for c in conds]
            L.append(f"| {cid} | {a['tier'].get(cid, '')} | " + " | ".join(cells) +
                     f" | {'accept' if g.get('naive_ci') else 'reject'} | {'accept' if g.get('restore') else 'reject'} |")
        L += ["", "⚑ = an escape-hatch signal was reported. Escapes (stop on a cheat) by tier and condition:", ""]
        for k, (e, n) in sorted(a["escapes"].items()):
            L.append(f"- {k}: {e}/{n}")
    sh = s.get("shapes")
    if sh:
        L += ["", "## Project shapes", "", "| shape | candidate | expected | got | s | env id | note |", "|---|---|---|---|---|---|---|"]
        for r in sh["rows"]:
            L.append(f"| {r['shape']} | {r['candidate']} | {'/'.join(r['expected'])} | {'✅' if r['ok'] else '❌'} {r['action']} | "
                     f"{r['seconds']} | {r['env_identified']} | {'' if r['ok'] else r['reason'][:140]} |")
    dt = s.get("determinism")
    if dt:
        L += ["", "## Determinism and receipt honesty", ""]
        for k, (p, n) in dt["by_check"].items():
            L.append(f"- {k}: {p}/{n} pass")
        if dt["failures"]:
            L += ["", "Failures:", ""] + [f"- [{r['check']}] {r['case']}: {r.get('observed', '')}" for r in dt["failures"]]
    return "\n".join(L) + "\n"
