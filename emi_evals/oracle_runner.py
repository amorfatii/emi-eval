"""Run hidden oracle checks without pytest.

Usage: python oracle_runner.py ROOT PYPATH_JSON CHECK_FILE...

Each check file is a plain module of `def test_*():` functions using bare
`assert`. Running them outside pytest matters: a candidate whose product
code behaves differently when pytest (or EMI's pins plugin) is loaded must
not fool the ground truth that EMI is scored against.

Prints one JSON object: {"checks": {"file::name": "passed" | "failed: ..."}}.
"""

import json
import os
import random
import sys
import traceback


def main() -> int:
    root, pypath, files = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3:]
    os.chdir(root)
    for p in reversed(pypath):
        sys.path.insert(0, os.path.join(root, p))
    results = {}
    for f in files:
        name = os.path.basename(f)
        ns = {"__name__": "oracle_" + name.replace(".", "_"), "__file__": f}
        try:
            with open(f, encoding="utf-8") as fh:
                code = compile(fh.read(), f, "exec")
            exec(code, ns)
        except BaseException as e:  # an import error in product code fails every check
            results[name + "::<import>"] = "failed: " + _why(e)
            continue
        for key, fn in list(ns.items()):
            if key.startswith("test_") and callable(fn):
                random.seed(0)
                try:
                    fn()
                    results[f"{name}::{key}"] = "passed"
                except BaseException as e:
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    results[f"{name}::{key}"] = "failed: " + _why(e)
    sys.stdout.write("\n@@ORACLE@@" + json.dumps({"checks": results}, sort_keys=True) + "\n")
    sys.stdout.flush()
    os._exit(0)  # product code may leave threads or atexit hooks behind


def _why(e: BaseException) -> str:
    tb = traceback.extract_tb(e.__traceback__)
    where = f"{tb[-1].filename}:{tb[-1].lineno}" if tb else "?"
    return f"{type(e).__name__}: {str(e)[:200]} @ {os.path.basename(where)}"


if __name__ == "__main__":
    sys.exit(main())
