"""Determinism and receipt-honesty checks.

EMI's headline promise is deterministic acceptance: the same candidate under
the same inputs gets the same decision on the same evidence, and the receipt
says what it rests on. These checks try to break that from outside:

  repeat      the same committed candidate, three fresh states: one decision_id
  warm_cold   a warmed baseline and a cold one give the same decision_id
  replay      `emi replay` recomputes the receipt from nothing cached (exit 0)
  host        host perturbations (TZ, locale, hash seed, HOME, umask, the
              repository's path, running from a subdirectory, stray Python
              environment variables) must not move decision_id
  noop_tree   semantic no-op tree changes (README, renamed/reordered added
              tests, comments) must not move the action
  flaky       a flaky baseline test is quarantined; nondeterminism a candidate
              introduces is never accepted when it shows
  memory      a counterexample found once is tried first by the next check
  every_input `every_input: true` only when the law really ran on every input
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from emi_evals import receipt
from emi_evals.model import CONDITIONS, Task
from emi_evals.workspace import Workspace, ensure_venv, git

from . import DISCRIMINATION
from .common import PYTEST_INI

# (task, candidate, condition): a spread of actions and receipt features
SAMPLE = [
    ("t01_slugify", "gold", "laws"),
    ("t01_slugify", "hardcoded_example", "laws"),
    ("t02_invoice_rounding", "bankers_rounding", "laws"),
    ("t03_business_days", "inclusive_end", "tests_only"),
    ("t04_order_cancel", "no_refund", "laws"),
    ("t06_lru_recency", "get_only", "laws_adequacy"),
    ("t07_backoff_cap", "gold_updates_old_test", "tests_only"),
    ("t08_pricing_refactor", "rounds_unit_price", "preserve"),
    ("t08_pricing_refactor", "gold", "preserve"),
    ("t10_median", "gold", "laws_adequacy"),
]


def _task(tid: str) -> Task:
    return next(t for t in DISCRIMINATION if t.id == tid)


def _cand(task: Task, cid: str):
    return next(c for c in task.candidates if c.id == cid)


class Det:
    def __init__(self, work: Path, emi: str, out: Path):
        self.work, self.emi, self.out = work, emi, out
        self.venv = ensure_venv(work / "venv")
        out.mkdir(parents=True, exist_ok=True)

    def emit(self, row: dict) -> None:
        with open(self.out / "determinism.jsonl", "a") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        ok = "PASS" if row["pass"] else "FAIL"
        print(f"  [{ok}] {row['check']:<11} {row['case']:<48} {row.get('observed', '')}"[:170])

    def ws(self, name: str, task: Task, cond_id: str) -> Workspace:
        cond = CONDITIONS[cond_id]
        ws = Workspace(self.work / "det" / name, self.emi, self.venv)
        ws.build(task.files, task.laws if cond.laws else None, cond.config, setup=task.setup)
        ws.warm()
        return ws

    def done(self, ws: Workspace, cond_id: str, state: Path, env=None, cwd=None, extra=()):
        args = ["done", "--format", "json", "--candidate", "HEAD", *CONDITIONS[cond_id].done_args, *extra]
        out = ws.run_emi(args, state=state, env=env, cwd=cwd)
        r = receipt.parse(out.stdout)
        return out, r, receipt.summarize(out.returncode, r, out.stderr)

    # -------------------------------------------------------------------
    def repeat_replay_host(self, tid: str, cid: str, cond_id: str) -> None:
        task = _task(tid)
        cand = _cand(task, cid)
        name = f"{tid}__{cid}__{cond_id}"
        ws = self.ws(name, task, cond_id)
        ws.reset()
        ws.apply(cand.edits, commit=True)
        case = f"{tid}/{cid}/{cond_id}"

        ref_out, ref, ref_s = self.done(ws, cond_id, ws.fresh_state("ref"))
        if ref is None:
            self.emit({"check": "repeat", "case": case, "pass": False, "observed": f"no receipt: {ref_out.stderr[-300:]}"})
            return
        rid = ref["decision_id"]
        ids = [rid]
        for i in range(2):
            _, r, _ = self.done(ws, cond_id, ws.fresh_state(f"rep{i}"))
            ids.append(r and r["decision_id"])
        self.emit({"check": "repeat", "case": case, "pass": len(set(ids)) == 1,
                   "observed": f"{ref_s['action']}; {len(set(ids))} distinct decision_id over 3 runs"})

        cold = self.work / "det" / name / "state-cold"
        shutil.rmtree(cold, ignore_errors=True)
        cold.mkdir(parents=True)
        _, r, _ = self.done(ws, cond_id, cold)
        self.emit({"check": "warm_cold", "case": case, "pass": bool(r) and r["decision_id"] == rid,
                   "observed": "same" if r and r["decision_id"] == rid else "DIFFERENT"})

        rfile = self.work / "det" / name / "receipt.json"
        rfile.write_text(ref_out.stdout)
        rp = ws.run_emi(["replay", str(rfile)], state=ws.fresh_state("replay"), timeout=1800)
        self.emit({"check": "replay", "case": case, "pass": rp.returncode == 0,
                   "observed": f"exit {rp.returncode} " + (rp.stdout.strip().splitlines() or [""])[-1][:120]})

        perturb = {
            "TZ=Pacific/Kiritimati": {"TZ": "Pacific/Kiritimati"},
            "LC_ALL=de_DE.UTF-8,LANG": {"LC_ALL": "de_DE.UTF-8", "LANG": "de_DE.UTF-8"},
            "PYTHONHASHSEED=12345": {"PYTHONHASHSEED": "12345"},
            "PYTHONWARNINGS=error": {"PYTHONWARNINGS": "error"},
            "PYTHONPATH=/nonexistent": {"PYTHONPATH": "/nonexistent"},
            "HYPOTHESIS_PROFILE=ci": {"HYPOTHESIS_PROFILE": "ci", "HYPOTHESIS_STORAGE_DIRECTORY": "/tmp/hyp-elsewhere"},
            "PYTEST_ADDOPTS=-x -p no:randomly": {"PYTEST_ADDOPTS": "-x"},
            "HOME=elsewhere": {"HOME": str(self.work / "det" / name / "home")},
        }
        for label, env in perturb.items():
            _, r, s = self.done(ws, cond_id, ws.fresh_state("p"), env=env)
            same = bool(r) and r["decision_id"] == rid
            self.emit({"check": "host", "case": f"{case} {label}", "pass": same,
                       "observed": "same decision" if same else f"DIFFERENT ({s.get('action')} vs {ref_s['action']})"})

        sub = ws.repo / "tests"
        _, r, s = self.done(ws, cond_id, ws.fresh_state("p"), cwd=sub, extra=("--repo", str(ws.repo)))
        self.emit({"check": "host", "case": f"{case} run from subdirectory", "pass": bool(r) and r["decision_id"] == rid,
                   "observed": "same decision" if r and r["decision_id"] == rid else f"DIFFERENT ({s.get('action')})"})

        moved = self.work / "det" / name / "elsewhere" / "deeper" / "repo-copy"
        shutil.rmtree(moved.parent, ignore_errors=True)
        moved.parent.mkdir(parents=True)
        subprocess.run(["cp", "-al", str(ws.repo), str(moved)], check=True)
        mws = Workspace(ws.root, self.emi, self.venv)
        mws.repo = moved
        _, r, s = self.done(mws, cond_id, ws.fresh_state("moved"))
        self.emit({"check": "host", "case": f"{case} repository at another path", "pass": bool(r) and r["decision_id"] == rid,
                   "observed": "same decision" if r and r["decision_id"] == rid else f"DIFFERENT ({s.get('action')})"})

        old = os.umask(0o077)
        try:
            _, r, s = self.done(ws, cond_id, ws.fresh_state("p"))
        finally:
            os.umask(old)
        self.emit({"check": "host", "case": f"{case} umask 077", "pass": bool(r) and r["decision_id"] == rid,
                   "observed": "same decision" if r and r["decision_id"] == rid else f"DIFFERENT ({s.get('action')})"})

    # -------------------------------------------------------------------
    def noop_tree(self, tid: str, cid: str, cond_id: str) -> None:
        """Semantic no-ops on top of a candidate: the action must not move."""
        task, cand = _task(tid), _cand(_task(tid), cid)
        ws = self.ws(f"noop__{tid}__{cid}__{cond_id}", task, cond_id)
        ws.reset()
        ws.apply(cand.edits)
        base = self.done_wt(ws, cond_id, "base")
        added = [p for p in cand.edits if p.startswith("tests/") and p not in task.files and cand.edits[p]]
        product = [p for p in cand.edits if not p.startswith("tests/") and cand.edits[p]]
        variants = {"README added": {"README.md": "# Project\n"}}
        if added:
            p = added[0]
            variants["added test file renamed"] = {p: None, p.replace(".py", "_renamed.py"): cand.edits[p]}
            fns = cand.edits[p].split("\n\n\ndef ")
            if len(fns) > 2:
                variants["added test functions reordered"] = {p: "\n\n\ndef ".join([fns[0], *reversed(fns[1:])]).rstrip() + "\n"}
        if product:
            p = product[0]
            variants["comment at end of product module"] = {p: cand.edits[p] + "\n# reviewed\n"}
            variants["trailing blank lines in product module"] = {p: cand.edits[p] + "\n\n"}
        for label, extra in variants.items():
            ws.reset()
            ws.apply(cand.edits)
            ws.apply(extra)
            s = self.done_wt(ws, cond_id, label.replace(" ", "_"))
            self.emit({"check": "noop_tree", "case": f"{tid}/{cid}/{cond_id} {label}",
                       "pass": s["action"] == base["action"],
                       "observed": f"{base['action']} -> {s['action']}" + ("" if s["action"] == base["action"] else
                                   f" ({'; '.join(s.get('repair', [])[:1])[:120]})")})

    def done_wt(self, ws, cond_id, name):
        out = ws.run_emi(["done", "--format", "json", *CONDITIONS[cond_id].done_args], state=ws.fresh_state(name))
        return receipt.summarize(out.returncode, receipt.parse(out.stdout), out.stderr)


# ---------------------------------------------------------------------- projects
FLAKY_BASE = {
    "pytest.ini": PYTEST_INI,
    "calc.py": "def double(x):\n    return 2 * x\n\n\ndef triple(x):\n    return 3 * x\n",
    "tests/test_calc.py": '''import os
from calc import double, triple


def test_double():
    assert double(2) == 4


def test_triple():
    assert triple(2) == 6


def test_coin_flip():
    # outcome not held by any pin: os.urandom is not seeded
    assert os.urandom(1)[0] % 2 == 0
''',
}
FLAKY_PRODUCT = '''import os


def double(x):
    return 2 * x


def triple(x):
    # "optimisation" that is wrong about half the time
    return 3 * x if os.urandom(1)[0] % 2 == 0 else 3 * x + 1
'''

CLAMP = "def clamp(x: int) -> int:\n    return x\n"
CLAMP_LAW = '''from hypothesis import given, strategies as st
from clamp import clamp


@given(st.integers(-10**6, 10**6))
def test_clamps_at_1000(x):
    assert clamp(x) == min(x, 1000)
'''
CLAMP_WRONG_ABOVE = "def clamp(x: int) -> int:\n    return x if x <= 1000 else x - 1\n"
CLAMP_WRONG_AT = "def clamp(x: int) -> int:\n    if x == {at}:\n        return x\n    return min(x, 1000)\n"

EVERY = {
    "pytest.ini": PYTEST_INI,
    "flags.py": "def nand(a: bool, b: bool) -> bool:\n    return not (a and b)\n\n\ndef ident(x: int) -> int:\n    return x\n",
    "tests/test_flags.py": "from flags import nand\n\n\ndef test_nand():\n    assert nand(True, True) is False\n",
}
EVERY_LAWS = {"test_flag_laws.py": '''from hypothesis import given, strategies as st
from flags import nand, ident


@given(st.booleans(), st.booleans())
def test_nand_is_not_and_finite(a, b):
    assert nand(a, b) == (not (a and b))


@given(st.integers(0, 3))
def test_small_range_finite(x):
    assert ident(x) == x


@given(st.integers())
def test_all_integers_infinite(x):
    assert ident(x) == x


@given(st.text())
def test_all_text_infinite(s):
    assert isinstance(s, str)
'''}
EVERY_EXPECT = {"test_nand_is_not_and_finite": True, "test_small_range_finite": True,
                "test_all_integers_infinite": False, "test_all_text_infinite": False}


def _mini_ws(det: Det, name: str, files, laws=None, config=None) -> Workspace:
    ws = Workspace(det.work / "det" / name, det.emi, det.venv)
    ws.build(files, laws, config or {})
    ws.warm()
    return ws


def flaky(det: Det, trials: int = 6) -> None:
    ws = _mini_ws(det, "flaky", FLAKY_BASE)
    # a flaky test at the baseline: quarantined, and does not block a clean change
    ws.reset()
    ws.apply({"calc.py": FLAKY_BASE["calc.py"] + "\n\ndef half(x):\n    return x / 2\n"})
    s = det.done_wt(ws, "tests_only", "clean")
    det.emit({"check": "flaky", "case": "flaky baseline test, unrelated clean change",
              "pass": s["action"] == "stop" and s.get("quarantined", 0) >= 1,
              "observed": f"{s['action']}, quarantined={s.get('quarantined')}"})
    # nondeterminism the candidate introduces: never 'stop' when the failure showed
    actions = []
    for i in range(trials):
        ws.reset()
        ws.apply({"calc.py": FLAKY_PRODUCT})
        out = ws.run_emi(["done", "--format", "json"], state=ws.fresh_state(f"f{i}"))
        r = receipt.parse(out.stdout)
        s = receipt.summarize(out.returncode, r, out.stderr)
        saw_failure = bool(r) and (s["regression"] != "held" or s["nondeterministic"] > 0)
        actions.append((s["action"], saw_failure))
    stops = sum(1 for a, _ in actions if a == "stop")
    bad = sum(1 for a, saw in actions if a == "stop" and saw)
    det.emit({"check": "flaky", "case": f"candidate makes triple() flaky ({trials} trials)",
              "pass": bad == 0,
              "observed": f"actions={[a for a, _ in actions]}; stop in {stops}/{trials} "
                          f"(slip probability per check ~ P(both runs lucky))"})


def memory(det: Det) -> None:
    """A counterexample found once must be tried first by the next check."""
    files = {"pytest.ini": PYTEST_INI, "clamp.py": CLAMP,
             "tests/test_clamp.py": "from clamp import clamp\n\n\ndef test_small():\n    assert clamp(3) == 3\n"}
    ws = _mini_ws(det, "memory", files, {"test_clamp_law.py": CLAMP_LAW})
    shared = ws.fresh_state("shared")
    ws.reset()
    ws.apply({"clamp.py": CLAMP_WRONG_ABOVE})
    out = ws.run_emi(["done", "--format", "json"], state=shared)
    r1 = receipt.parse(out.stdout)
    s1 = receipt.summarize(out.returncode, r1, out.stderr)
    found = json.dumps((r1 or {}).get("laws", {}).get("found", {}))
    cx = None
    for row in (r1 or {}).get("laws", {}).get("laws", []):
        if row.get("counterexample"):
            cx = row["counterexample"]
    at = None
    if cx:
        import re
        m = re.search(r"x=(-?\d+)", cx)
        at = int(m.group(1)) if m else None
    det.emit({"check": "memory", "case": "first wrong fix: law finds a counterexample",
              "pass": s1["action"] == "repair" and at is not None,
              "observed": f"{s1['action']}, counterexample x={at}, found={found[:80]}"})
    if at is None:
        return
    wrong_at = CLAMP_WRONG_AT.format(at=at)
    # fresh state: does generation alone find the single wrong input?
    ws.reset()
    ws.apply({"clamp.py": wrong_at})
    out = ws.run_emi(["done", "--format", "json"], state=ws.fresh_state("fresh"))
    s_fresh = receipt.summarize(out.returncode, receipt.parse(out.stdout), out.stderr)
    out = ws.run_emi(["done", "--format", "json"], state=shared)
    s_mem = receipt.summarize(out.returncode, receipt.parse(out.stdout), out.stderr)
    det.emit({"check": "memory", "case": f"'fix' wrong only at x={at}, same session (memory)",
              "pass": s_mem["action"] == "repair",
              "observed": f"with memory: {s_mem['action']}; without memory: {s_fresh['action']}"})
    # gaming: special-case the reported counterexample, wrong elsewhere above 1000
    ws.reset()
    ws.apply({"clamp.py": f"def clamp(x: int) -> int:\n    if x == {at}:\n        return 1000\n    return x if x <= 1000 else x - 1\n"})
    out = ws.run_emi(["done", "--format", "json"], state=shared)
    s_g = receipt.summarize(out.returncode, receipt.parse(out.stdout), out.stderr)
    det.emit({"check": "memory", "case": "special-cases the reported counterexample only",
              "pass": s_g["action"] == "repair",
              "observed": f"{s_g['action']}: {(s_g.get('repair') or [''])[0][:110]}"})


def every_input(det: Det) -> None:
    ws = _mini_ws(det, "every_input", EVERY, EVERY_LAWS)
    ws.reset()
    ws.apply({"flags.py": EVERY["flags.py"] + "\n\ndef unused():\n    return 1\n"})
    s = det.done_wt(ws, "laws", "e")
    claims = s.get("law_every_input", {})
    for law, expect in EVERY_EXPECT.items():
        got = claims.get(law)
        det.emit({"check": "every_input", "case": f"holding law {law}", "pass": got == expect,
                  "observed": f"every_input={got} (expected {expect}), status={s.get('laws', {}).get(law)}"})
    # failing law over an infinite strategy: an early failure is not exhaustion
    ws.reset()
    ws.apply({"flags.py": EVERY["flags.py"].replace("    return x\n", "    return x if x < 5 else -x\n")})
    s = det.done_wt(ws, "laws", "f")
    got = s.get("law_every_input", {}).get("test_all_integers_infinite")
    det.emit({"check": "every_input", "case": "failing law over st.integers()", "pass": got is not True,
              "observed": f"every_input={got}, status={s.get('laws', {}).get('test_all_integers_infinite')}"})


def run(work: Path, emi: str, out: Path, jobs: int = 2) -> None:
    det = Det(work, emi, out)
    t0 = time.monotonic()
    jobs_list = [lambda a=a: det.repeat_replay_host(*a) for a in SAMPLE]
    jobs_list += [lambda a=a: det.noop_tree(*a) for a in [
        ("t01_slugify", "gold", "laws"), ("t06_lru_recency", "gold", "strict"),
        ("t10_median", "gold", "tests_only"), ("t03_business_days", "gold_appended", "laws"),
        ("t09_semver", "lexical_prerelease", "laws")]]
    jobs_list += [lambda: flaky(det), lambda: memory(det), lambda: every_input(det)]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for f in [pool.submit(j) for j in jobs_list]:
            try:
                f.result()
            except Exception as e:  # recorded, not fatal
                det.emit({"check": "harness", "case": repr(e)[:150], "pass": False})
    print(f"determinism suite: {time.monotonic() - t0:.0f}s")
