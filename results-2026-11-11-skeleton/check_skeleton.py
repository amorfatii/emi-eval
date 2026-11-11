"""Throwaway check of a change against a drafted skeleton (and of the
developers' fix against the same skeleton, for comparison).

For a patch applied to the base tree it reports:
  named     each ADD/CHANGE line: does the function exist after the change,
            with the stated parameter names (and, where stated, the return
            annotation); each TYPE line: did the named node table entry change
            as stated (gast only: checked by hand-written rule below).
  extra     public functions, methods or classes added, or whose signature
            changed, that the skeleton does not name ("public" = no leading
            underscore, or a dunder method).
  rules     each RULE line: was it broken. The one RULE in this trial (esper)
            is not a call but a write ("add_component may not create entries
            in _entities"), so it is checked as: no subscript store or
            setdefault on self._entities inside World.add_component.
  touched   the functions whose bodies changed, for the comparison with the
            developers' fix.

Usage: python check_skeleton.py BASE_TREE SKELETON.md PATCH.diff [--json]
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ITEM = re.compile(r"^- (ADD|CHANGE|REMOVE|TYPE|RULE) `([^`]+)`(?: may not call `([^`]+)`)?")


def parse_skeleton(text: str) -> list[dict]:
    items = []
    for line in text.splitlines():
        m = ITEM.match(line.strip())
        if not m:
            continue
        kind, target, callee = m.groups()
        it = {"kind": kind, "raw": line.strip()}
        path, _, rest = target.partition("::")
        it["file"] = path
        sig = re.match(r"([\w.]+)\s*(?:\((.*)\))?\s*(?:->\s*(.+))?$", rest.strip())
        it["qual"] = sig.group(1) if sig else rest
        if sig and sig.group(2) is not None:
            it["params"] = [p.split(":")[0].split("=")[0].strip().lstrip("*") for p in split_params(sig.group(2))]
            it["params"] = [p for p in it["params"] if p]
        if sig and sig.group(3):
            it["returns"] = sig.group(3).strip()
        if callee:
            it["callee"] = callee
        items.append(it)
    return items


def split_params(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def functions(tree: ast.AST) -> dict[str, list[ast.FunctionDef]]:
    """Qualified name -> definitions (several when defined under version ifs)."""
    found: dict[str, list] = {}

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = prefix + child.name
                found.setdefault(q, []).append(child)
                walk(child, q + ".<locals>.")
            elif isinstance(child, ast.ClassDef):
                q = prefix + child.name
                found.setdefault(q, []).append(child)
                walk(child, q + ".")
            else:
                walk(child, prefix)  # descend into if/try blocks at the same level

    walk(tree, "")
    return found


def sig_of(fn) -> dict:
    if isinstance(fn, ast.ClassDef):
        return {"class": True}
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args]
    if a.vararg:
        names.append(a.vararg.arg)
    names += [x.arg for x in a.kwonlyargs]
    if a.kwarg:
        names.append(a.kwarg.arg)
    return {"params": names, "returns": ast.unparse(fn.returns) if fn.returns else None}


def is_public(qual: str) -> bool:
    last = qual.split(".")[-1]
    return "<locals>" not in qual and (not last.startswith("_") or (last.startswith("__") and last.endswith("__")))


def apply(base: Path, patch: str) -> Path:
    d = Path(tempfile.mkdtemp()) / "t"
    shutil.copytree(base, d, symlinks=True, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
    if patch.strip():
        p = d.parent / "p.diff"
        p.write_text(patch if patch.endswith("\n") else patch + "\n")
        r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(p)], cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            r = subprocess.run(["patch", "-p1", "--forward", "-i", str(p)], cwd=d, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("patch does not apply: " + r.stderr[-300:])
    return d


def src_files(patch: str) -> list[str]:
    files = sorted(set(re.findall(r"^\+\+\+ b/(\S+)", patch, flags=re.M)))
    return [f for f in files if f.endswith(".py") and "test" not in Path(f).name and "/tests/" not in "/" + f]


def body_dump(fn) -> str:
    return ast.dump(fn, include_attributes=False)


def esper_rule_broken(after_tree: ast.AST) -> bool:
    for fn in functions(after_tree).get("World.add_component", []):
        for node in ast.walk(fn):
            if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
                v = node.value
                if isinstance(v, ast.Attribute) and v.attr == "_entities":
                    return True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault":
                v = node.func.value
                if isinstance(v, ast.Attribute) and v.attr == "_entities":
                    return True
    return False


def gast_type_ok(after: Path) -> bool:
    text = (after / "gast/gast.py").read_text()
    m = re.search(r"\('Assign',\s*\(\(([^)]*)\)", text)
    return bool(m and "type_comment" in m.group(1))


def check(base: Path, skeleton_text: str, patch: str) -> dict:
    items = parse_skeleton(skeleton_text)
    after = apply(base, patch)
    files = sorted(set(src_files(patch)) | {i["file"] for i in items if i["kind"] in ("ADD", "CHANGE")})
    before_f, after_f = {}, {}
    for f in files:
        b = base / f
        a = after / f
        before_f[f] = functions(ast.parse(b.read_text())) if b.exists() else {}
        after_f[f] = functions(ast.parse(a.read_text())) if a.exists() else {}
    named = []
    for it in items:
        if it["kind"] in ("ADD", "CHANGE"):
            defs = after_f.get(it["file"], {}).get(it["qual"], [])
            row = {"item": it["raw"][:90], "exists": bool(defs)}
            if defs and "params" in it:
                got = [sig_of(d) for d in defs]
                row["params_ok"] = any(g.get("params") == it["params"] for g in got)
                row["got_params"] = got[0].get("params")
                if it.get("returns"):
                    rets = [g.get("returns") for g in got]
                    row["returns_annotated"] = any(rets)
                    row["returns_ok"] = (it["returns"] in rets) if any(rets) else None
            changed = False
            bdefs = before_f.get(it["file"], {}).get(it["qual"], [])
            if defs:
                changed = [body_dump(d) for d in defs] != [body_dump(d) for d in bdefs]
            row["changed"] = changed
            named.append(row)
        elif it["kind"] == "TYPE" and "gast" in it["file"]:
            named.append({"item": it["raw"][:90], "exists": True, "type_ok": gast_type_ok(after)})
    named_quals = {(i["file"], i["qual"]) for i in items if i["kind"] in ("ADD", "CHANGE")}
    extra, touched = [], []
    for f in files:
        b, a = before_f[f], after_f[f]
        for q, defs in a.items():
            if q not in b:
                touched.append(f"{f}::{q} (added)")
                if is_public(q) and (f, q) not in named_quals:
                    extra.append(f"{f}::{q} (added)")
            else:
                if [body_dump(d) for d in defs] != [body_dump(d) for d in b[q]]:
                    if not isinstance(defs[0], ast.ClassDef):
                        touched.append(f"{f}::{q}")
                    if (not isinstance(defs[0], ast.ClassDef) and is_public(q) and (f, q) not in named_quals
                            and [sig_of(d) for d in defs] != [sig_of(d) for d in b[q]]):
                        extra.append(f"{f}::{q} (signature changed)")
        for q in b:
            if q not in a and is_public(q):
                touched.append(f"{f}::{q} (removed)")
                extra.append(f"{f}::{q} (removed)")
        # module-level non-function changes (tables, constants)
        try:
            bt = ast.parse((base / f).read_text()) if (base / f).exists() else None
            at = ast.parse((after / f).read_text()) if (after / f).exists() else None
            if bt and at:
                bm = [ast.dump(n) for n in bt.body if not isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.If, ast.Try))]
                am = [ast.dump(n) for n in at.body if not isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.If, ast.Try))]
                if bm != am:
                    touched.append(f"{f}::<module-level statements>")
        except SyntaxError:
            pass
    rules = []
    for it in items:
        if it["kind"] == "RULE":
            broken = esper_rule_broken(ast.parse((after / "esper/__init__.py").read_text())) if "esper" in it["file"] else None
            rules.append({"item": it["raw"][:90], "broken": broken})
    shutil.rmtree(after.parent, ignore_errors=True)
    inside = (all(n.get("exists") and n.get("params_ok", True) is not False and n.get("type_ok", True) for n in named)
              and not extra and not any(r["broken"] for r in rules))
    return {"named": named, "extra": extra, "rules": rules, "touched": sorted(set(touched)), "inside": inside}


if __name__ == "__main__":
    base, skel, patch = Path(sys.argv[1]), Path(sys.argv[2]).read_text(), Path(sys.argv[3]).read_text()
    print(json.dumps(check(base, skel, patch), indent=1))
