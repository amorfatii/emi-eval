"""Which rules still pass when the function under test is replaced by a
trivial body (EMI's four stand-ins, docs/laws.md: return the first argument,
return None, return the default of the return annotation, raise
NotImplementedError).

For each task the rules run on its first correct candidate ("gold"), once
as it is and once per (target function, stand-in). The targets are the
functions the request is about. A rule
"depends on" a target when some stand-in of that target makes it fail. A rule is
  - "vacuous" if, for a target it depends on, it still passes under another
    stand-in of that target (some trivial body satisfies it);
  - "untouched" if it passes under every stand-in (it does not depend on the
    target at all: it is about other code, e.g. behaviour to keep).
Rules that already fail on gold are listed but not judged.

Usage (from the repository root):
  python results-2026-11-11-drafted/scripts/vacuity.py PYTHON WORKDIR [SET...] > results-2026-11-11-drafted/raw/vacuity.jsonl
PYTHON is a venv python with pytest and hypothesis (the harness venv).
"""
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from emi_evals.model import CORRECT  # noqa: E402
from emi_evals.workspace import write_files  # noqa: E402
from suites import DISCRIMINATION  # noqa: E402

# module file, attribute path, default of the return annotation (None: no annotation)
TARGETS = {
    "t01_slugify": [("textutil.py", "slugify", '""')],
    "t02_invoice_rounding": [("billing.py", "invoice_total", None)],
    "t03_business_days": [("calendar_utils.py", "business_days", "0")],
    "t04_order_cancel": [("orders.py", "cancel", None)],
    "t05_kv_quotes": [("kvparse.py", "parse", "{}")],
    "t06_lru_recency": [("lru.py", "LRUCache.get", None), ("lru.py", "LRUCache.put", None)],
    "t07_backoff_cap": [("retry.py", "backoff_delays", "[]")],
    "t08_pricing_refactor": [("pricing.py", "member_price", "0.0"), ("pricing.py", "bulk_price", "0.0")],
    "t09_semver": [("versions.py", "compare", "0")],
    "t10_median": [("stats.py", "median", None)],
}


def standins(default):
    out = {"returns_first_argument": "return _a[0] if _a else None",
           "returns_none": "return None",
           "raises_not_implemented": "raise NotImplementedError"}
    if default is not None:
        out["returns_annotation_default"] = f"return {default}"
    return out


def patch(attr: str, body: str) -> str:
    if "." in attr:  # a method: the first argument after self
        cls, meth = attr.split(".")
        body = body.replace("_a[0] if _a", "_a[1] if len(_a) > 1")
        return f"\n\ndef _emi_standin(*_a, **_k):\n    {body}\n\n{cls}.{meth} = _emi_standin\n"
    return f"\n\ndef _emi_standin(*_a, **_k):\n    {body}\n\n{attr} = _emi_standin\n"


def run_laws(tree: Path, python: str) -> dict[str, str]:
    xml = tree / "junit.xml"
    if xml.exists():
        xml.unlink()
    subprocess.run([python, "-m", "pytest", "-q", "-p", "no:cacheprovider", ".emi/laws", f"--junitxml={xml}"],
                   cwd=tree, capture_output=True, text=True, timeout=600,
                   env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "HYPOTHESIS_PROFILE": ""})
    res = {}
    if not xml.exists():
        return res
    for tc in ET.parse(xml).getroot().iter("testcase"):
        cls = tc.get("classname", "")
        parts = cls.split(".")
        # classname is a dotted path like ".emi.laws.test_x" or ".emi.laws.test_x.TestMachine"
        fname = next((p for p in parts if p.startswith("test_")), parts[-1]) + ".py"
        klass = parts[-1] if parts[-1] != fname[:-3] else ""
        rid = f"{fname}::{klass + '::' if klass else ''}{tc.get('name')}"
        status = "passed"
        for child in tc:
            if child.tag in ("failure", "error"):
                status = "failed"
            elif child.tag == "skipped":
                status = "skipped"
        rid = rid.split("[")[0]  # a parametrized rule is one rule: it passes only if every case does
        if res.get(rid) != "failed":
            res[rid] = status if res.get(rid) in (None, "passed") else res[rid]
    return res


def main() -> int:
    python, work = sys.argv[1], Path(sys.argv[2])
    sets = {"drafted_no_questions": None, "drafted_questions": None, "laws": "hand"}
    if len(sys.argv) > 3:
        sets = {k: v for k, v in sets.items() if k in sys.argv[3:]}
    for t in DISCRIMINATION:
        gold = next(c for c in t.candidates if c.label == CORRECT)
        for sname, kind in sets.items():
            laws = t.laws if kind == "hand" else {p.name: p.read_text()
                                                   for p in sorted((HERE / "laws" / sname / t.id).glob("*.py"))}
            if not laws:
                continue
            tree = work / sname / t.id
            if tree.exists():
                shutil.rmtree(tree)
            tree.mkdir(parents=True)
            write_files(tree, dict(t.files))
            write_files(tree, dict(gold.edits))
            write_files(tree, {f".emi/laws/{k}": v for k, v in laws.items()})
            on_gold = run_laws(tree, python)
            under = {}
            for mod, attr, default in TARGETS[t.id]:
                original = (tree / mod).read_text()
                for sid, body in standins(default).items():
                    (tree / mod).write_text(original + patch(attr, body))
                    under[f"{attr}:{sid}"] = run_laws(tree, python)
                (tree / mod).write_text(original)
            for rid, st in sorted(on_gold.items()):
                passes = sorted(k for k, r in under.items() if r.get(rid) == "passed")
                # the targets this rule depends on: some stand-in of it makes the rule fail
                depends = sorted({k.split(":")[0] for k, r in under.items() if r.get(rid) != "passed"})
                vac = sorted(k for k in passes if k.split(":")[0] in depends)
                print(json.dumps({"set": sname, "task": t.id, "rule": rid, "on_gold": st,
                                  "passes_under": passes, "depends_on": depends, "standins_tried": len(under),
                                  "vacuous": st == "passed" and bool(vac), "vacuous_under": vac,
                                  "untouched": st == "passed" and not depends}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
