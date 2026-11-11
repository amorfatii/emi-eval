#!/usr/bin/env python3
"""Tables for COMPARISON.md: an old results folder against a new one.

    python3 results-2026-11-11/compare.py OLD_DIR NEW_DIR > tables.md

Each folder is expected to hold disc/, adv-final/, shapes/ and determinism/
as written by `python -m emi_evals run|determinism`. Anything missing on the
old side is shown as "no data", never as a number.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ORDER = ["tests_only", "strict", "laws", "laws_adequacy", "preserve"]
ADV_ORDER = ["tests_only", "laws", "enforced", "enforced_laws"]
GATES = ["naive_ci", "restore", "restore_laws"]


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def frac(k: int, n: int) -> str:
    return "no data" if n == 0 else f"{k}/{n} ({100 * k / n:.0f}%)"


def joined(d: Path) -> list[dict]:
    truth = {(r["task"], r["candidate"]): r for r in load(d / "truth.jsonl") if r["candidate"] != "<baseline>"}
    out = []
    for r in load(d / "results.jsonl"):
        t = truth.get((r["task"], r["candidate"]))
        if t and t["label_ok"]:
            out.append({**r, "truth": t["truth"], "gates": t["gates"], "oracle_failed": t["oracle"]["failed"]})
    return out


def act(r: dict) -> str:
    return r["emi"].get("action")


def reason(e: dict) -> str:
    for key in ("repair", "ask"):
        if e.get(key):
            v = e[key][0]
            return (v if isinstance(v, str) else json.dumps(v)).replace("\n", " ").replace("|", "/")
    if e.get("changed_old_tests"):
        return "waits for approval: " + ", ".join(e["changed_old_tests"])
    if e.get("this_run"):
        return e["this_run"][0].replace("\n", " ").replace("|", "/")
    return (e.get("error") or "").replace("\n", " ").replace("|", "/")


def score(rows: list[dict]) -> dict:
    bad = [r for r in rows if r["truth"] == "incorrect"]
    ok = [r for r in rows if r["truth"] == "correct"]
    stops = [r for r in rows if act(r) == "stop"]
    secs = sorted(r["emi"]["seconds"] for r in rows if isinstance(r["emi"].get("seconds"), (int, float)))
    return {
        "catch": (sum(act(r) != "stop" for r in bad), len(bad)),
        "accept": (sum(act(r) == "stop" for r in ok), len(ok)),
        "precision": (sum(r["truth"] == "correct" for r in stops), len(stops)),
        "median": round(statistics.median(secs), 1) if secs else None,
        "p90": round(secs[int(0.9 * (len(secs) - 1))], 1) if secs else None,
        "n": len(rows),
        "crashes": sum(1 for r in rows if not r["emi"].get("receipt")),
        "exit_mismatch": sum(1 for r in rows if r["emi"].get("receipt") and not r["emi"].get("exit_matches_action")),
        "isolation": dict(Counter(str(r["emi"].get("isolation")) for r in rows)),
        "actions_correct": dict(Counter(act(r) for r in ok)),
        "actions_incorrect": dict(Counter(act(r) for r in bad)),
    }


def gate(rows: list[dict], g: str) -> dict | None:
    rows = [r for r in rows if g in r["gates"]]
    if not rows:
        return None
    bad = [r for r in rows if r["truth"] == "incorrect"]
    ok = [r for r in rows if r["truth"] == "correct"]
    stops = [r for r in rows if r["gates"][g]["accept"]]
    return {"catch": (sum(not r["gates"][g]["accept"] for r in bad), len(bad)),
            "accept": (sum(bool(r["gates"][g]["accept"]) for r in ok), len(ok)),
            "precision": (sum(r["truth"] == "correct" for r in stops), len(stops))}


def by_cond(rows: list[dict]) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in rows:
        out[r["condition"]].append(r)
    return out


def discrimination(old: Path, new: Path, P) -> None:
    o, n = by_cond(joined(old / "disc")), by_cond(joined(new / "disc"))
    P("## Discrimination: per condition\n")
    P("| condition | who | catch (bad change not allowed to finish) | accept (correct change allowed to finish) | stop precision (a `stop` is correct work) |")
    P("|---|---|---|---|---|")
    for c in ORDER:
        if c not in n and c not in o:
            continue
        for label, src in (("EMI old", o), ("EMI new", n)):
            if c in src:
                s = score(src[c])
                P(f"| {c} | {label} | {frac(*s['catch'])} | {frac(*s['accept'])} | {frac(*s['precision'])} |")
            else:
                P(f"| {c} | {label} | no data | no data | no data |")
        for g in GATES:
            for label, src in (("old", o), ("new", n)):
                v = gate(src.get(c, []), g)
                if v:
                    P(f"| {c} | gate `{g}` ({label} run) | {frac(*v['catch'])} | {frac(*v['accept'])} | {frac(*v['precision'])} |")
    P("\n## Discrimination: run validity and seconds per check\n")
    P("| condition | run | rows | isolation | crashes | exit_mismatch | median s | p90 s | actions on correct | actions on incorrect |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for c in ORDER:
        for label, src in (("old", o), ("new", n)):
            if c in src:
                s = score(src[c])
                P(f"| {c} | {label} | {s['n']} | {s['isolation']} | {s['crashes']} | {s['exit_mismatch']} | {s['median']} | {s['p90']} | "
                  f"{s['actions_correct']} | {s['actions_incorrect']} |")
    changes(joined(old / "disc"), joined(new / "disc"), ORDER, P, "Discrimination")
    P("\n## Still wrong: incorrect candidates that get `stop` under the strongest condition they ran in\n")
    rows = joined(new / "disc")
    strongest: dict = {}
    for r in rows:
        k = (r["task"], r["candidate"])
        if k not in strongest or ORDER.index(r["condition"]) > ORDER.index(strongest[k]["condition"]):
            strongest[k] = r
    P("| task / candidate | failure mode | condition | what the oracle found wrong | restore | restore_laws | EMI's own note |")
    P("|---|---|---|---|---|---|---|")
    for k in sorted(strongest):
        r = strongest[k]
        if r["truth"] == "incorrect" and act(r) == "stop":
            why = "; ".join(f"{a.split('::')[-1]}: {b}" for a, b in list(r["oracle_failed"].items())[:1]).replace("|", "/")[:170]
            g = r["gates"]
            rl = g.get("restore_laws", {}).get("accept")
            P(f"| {k[0]} / {k[1]} | {r['mode']} | {r['condition']} | {why} | {'accepts' if g['restore']['accept'] else 'rejects'} | "
              f"{'n/a' if rl is None else 'accepts' if rl else 'rejects'} | {reason(r['emi'])[:150]} |")
    P("\n## Still wrong: correct candidates not allowed to finish\n")
    P("| task / candidate | how presented | condition | action | EMI's stated reason |")
    P("|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["task"], r["candidate"], ORDER.index(r["condition"]))):
        if r["truth"] == "correct" and act(r) != "stop":
            P(f"| {r['task']} / {r['candidate']} | {r['mode']} | {r['condition']} | {act(r)} | {reason(r['emi'])[:260]} |")
    P("\n## `every_input: true` on a failing law (discrimination rows)\n")
    for label, rs in (("old", joined(old / "disc")), ("new", rows)):
        hits = [f"{r['task']}/{r['candidate']}/{r['condition']}: {law}" for r in rs
                for law, claim in (r["emi"].get("law_every_input") or {}).items()
                if claim and (r["emi"].get("laws") or {}).get(law) in ("unmet", "broken")]
        laws_failing = sum(1 for r in rs for st in (r["emi"].get("laws") or {}).values() if st in ("unmet", "broken"))
        P(f"- {label}: {len(hits)} claim(s) over {laws_failing} failing law results" + ("" if rs else " (no data)"))
        for h in hits:
            P(f"  - {h}")


def changes(old_rows: list[dict], new_rows: list[dict], order: list[str], P, title: str) -> None:
    P(f"\n## {title}: every candidate whose EMI action changed\n")
    if not old_rows:
        P("No old rows to compare against.")
        return
    o = {(r["task"], r["candidate"], r["condition"]): r for r in old_rows}
    P("| task / candidate | condition | old | new | oracle says | better or worse | new reason |")
    P("|---|---|---|---|---|---|---|")
    n_changed = 0
    for r in sorted(new_rows, key=lambda r: (r["task"], r["candidate"], order.index(r["condition"]) if r["condition"] in order else 9)):
        b = o.get((r["task"], r["candidate"], r["condition"]))
        if b is None or act(b) == act(r):
            continue
        n_changed += 1
        truth = r.get("truth") or r["label"]
        if truth == "correct":
            verdict = "better" if act(r) == "stop" else "worse" if act(b) == "stop" else "same (still blocked)"
        else:
            verdict = "worse" if act(r) == "stop" else "better" if act(b) == "stop" else "same (still caught)"
        P(f"| {r['task']} / {r['candidate']} | {r['condition']} | {act(b)} | {act(r)} | {truth} | {verdict} | {reason(r['emi'])[:160]} |")
    same = sum(1 for r in new_rows if (k := (r["task"], r["candidate"], r["condition"])) in o and act(o[k]) == act(r))
    only_new = sum(1 for r in new_rows if (r["task"], r["candidate"], r["condition"]) not in o)
    P(f"\n{n_changed} changed, {same} unchanged, {only_new} rows with no old counterpart.")


def adversarial(old: Path, new: Path, P) -> None:
    def table(d: Path):
        t = defaultdict(dict)
        rows = [r for r in load(d / "results.jsonl") if r.get("suite") == "adversarial"]
        for r in rows:
            t[r["candidate"]][r["condition"]] = r
        truth = {r["candidate"]: r for r in load(d / "truth.jsonl") if r["candidate"] != "<baseline>"}
        return t, rows, truth

    ot, orows, _ = table(old / "adv-final")
    nt, nrows, truth = table(new / "adv-final")
    P("\n## Adversarial: per cheat and condition (old → new; ⚑ = EMI reported an escape-hatch signal)\n")
    P("| cheat | label | " + " | ".join(ADV_ORDER) + " | naive CI | restore | restore_laws |")
    P("|---|---|" + "---|" * (len(ADV_ORDER) + 3))

    def cell(t, cid, c):
        r = t.get(cid, {}).get(c)
        return None if r is None else act(r) + (" ⚑" if r["emi"].get("signals") else "")

    for cid in nt:
        cells = []
        for c in ADV_ORDER:
            a, b = cell(ot, cid, c), cell(nt, cid, c)
            cells.append(f"{b}" if a is None else (b if a == b else f"**{a} → {b}**"))
        g = (truth.get(cid) or {}).get("gates", {})
        lab = next(iter(nt[cid].values()))["label"]
        P(f"| {cid} | {lab} | " + " | ".join(cells) + " | " +
          " | ".join(("accepts" if g[k]["accept"] else "rejects") if k in g else "n/a" for k in GATES) + " |")
    P("\nCheats that end in `stop` (escapes), per condition:\n")
    P("| condition | old | new | gate `restore` accepts | gate `restore_laws` accepts |")
    P("|---|---|---|---|---|")
    for c in ADV_ORDER:
        def esc(t):
            bad = [v[c] for v in t.values() if c in v and v[c]["label"] == "incorrect"]
            return frac(sum(act(r) == "stop" for r in bad), len(bad))
        bad_ids = [cid for cid, v in nt.items() if c in v and v[c]["label"] == "incorrect"]
        gr = sum(1 for cid in bad_ids if truth[cid]["gates"]["restore"]["accept"])
        gl = sum(1 for cid in bad_ids if truth[cid]["gates"].get("restore_laws", {}).get("accept"))
        P(f"| {c} | {esc(ot)} | {esc(nt)} | {frac(gr, len(bad_ids))} | {frac(gl, len(bad_ids))} |")
    P("\nValidity of the new adversarial rows: " + json.dumps({
        "rows": len(nrows), "isolation": dict(Counter(str(r["emi"].get("isolation")) for r in nrows)),
        "crashes": sum(1 for r in nrows if not r["emi"].get("receipt")),
        "exit_mismatch": sum(1 for r in nrows if r["emi"].get("receipt") and not r["emi"].get("exit_matches_action"))}))
    changes(orows, nrows, ADV_ORDER, P, "Adversarial")
    P("\n### New adversarial rows that end in `stop` on an incorrect candidate\n")
    for r in nrows:
        if r["label"] == "incorrect" and act(r) == "stop":
            P(f"- {r['candidate']} / {r['condition']}: signals={r['emi'].get('signals')}; {reason(r['emi'])[:200]}")
    P("\n### Honest controls and expected actions (new)\n")
    for r in nrows:
        if r["label"] == "correct" or r.get("expect_actions"):
            P(f"- {r['candidate']} / {r['condition']}: {act(r)}" + (f" (expected {'/'.join(r['expect_actions'])})" if r.get("expect_actions") else "")
              + (f" — {reason(r['emi'])[:200]}" if act(r) != "stop" else ""))


def shapes(old: Path, new: Path, P) -> None:
    o = {(r["task"], r["candidate"]): r for r in load(old / "shapes" / "results.jsonl")}
    n = load(new / "shapes" / "results.jsonl")
    P("\n## Shapes\n")
    ok_old = sum(act(r) in r["expect_actions"] for r in o.values())
    ok_new = sum(act(r) in r["expect_actions"] for r in n)
    P(f"- as expected: old {frac(ok_old, len(o))}, new {frac(ok_new, len(n))}")
    P(f"- new rows isolation: {dict(Counter(str(r['emi'].get('isolation')) for r in n))}; "
      f"crashes {sum(1 for r in n if not r['emi'].get('receipt'))}; "
      f"exit_mismatch {sum(1 for r in n if r['emi'].get('receipt') and not r['emi'].get('exit_matches_action'))}")
    for label, rs in (("old", list(o.values())), ("new", n)):
        secs = sorted(r["emi"]["seconds"] for r in rs if isinstance(r["emi"].get("seconds"), (int, float)))
        if secs:
            P(f"- {label} seconds per check: median {statistics.median(secs):.1f}, p90 {secs[int(0.9 * (len(secs) - 1))]:.1f}")
        P(f"- {label} environment not identified: {sorted(r['task'] + '/' + r['candidate'] for r in rs if not r['emi'].get('environment_identified'))}")
    P("")
    P("| shape / candidate | expected | old | new |")
    P("|---|---|---|---|")
    for r in sorted(n, key=lambda r: (r["task"], r["candidate"])):
        b = o.get((r["task"], r["candidate"]))
        if b is None or act(b) != act(r) or act(r) not in r["expect_actions"]:
            P(f"| {r['task']} / {r['candidate']} | {'/'.join(r['expect_actions'])} | {act(b) if b else 'no data'} | {act(r)} — {reason(r['emi'])[:160]} |")


def determinism(old: Path, new: Path, P) -> None:
    o, n = load(old / "determinism" / "determinism.jsonl"), load(new / "determinism" / "determinism.jsonl")
    P("\n## Determinism checks (passes / rows)\n")
    P("| check | old | new |")
    P("|---|---|---|")
    checks = list(dict.fromkeys([r["check"] for r in o] + [r["check"] for r in n]))
    for c in checks:
        a, b = [r for r in o if r["check"] == c], [r for r in n if r["check"] == c]
        P(f"| {c} | {frac(sum(bool(r['pass']) for r in a), len(a))} | {frac(sum(bool(r['pass']) for r in b), len(b))} |")
    P("\nRows that fail in either run, or whose observation changed (host rows only if failing):\n")
    P("| check | case | old | new |")
    P("|---|---|---|---|")
    om = {(r["check"], r["case"]): r for r in o}
    nm = {(r["check"], r["case"]): r for r in n}

    def norm(r):  # decision ids differ between EMI versions by design
        s = str(r.get("observed", "")) if r else "no row"
        return s.split(" {")[0] if r and r["check"] == "replay" else s

    for k in list(dict.fromkeys(list(om) + list(nm))):
        a, b = om.get(k), nm.get(k)
        failing = (a and not a["pass"]) or (b and not b["pass"])
        if failing or (k[0] != "host" and norm(a) != norm(b)):
            f = lambda r: "no row" if r is None else ("PASS: " if r["pass"] else "FAIL: ") + norm(r).replace("|", "/")[:200]  # noqa: E731
            P(f"| {k[0]} | {k[1]} | {f(a)} | {f(b)} |")


def main() -> int:
    old, new = Path(sys.argv[1]), Path(sys.argv[2])
    P = print
    discrimination(old, new, P)
    adversarial(old, new, P)
    shapes(old, new, P)
    determinism(old, new, P)
    return 0


if __name__ == "__main__":
    sys.exit(main())
