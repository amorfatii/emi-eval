"""Write what each role is allowed to see, one file per task.

drafter/<task>.md   the task's prompt and its baseline project files, nothing else
answerer/<task>.md  the task's prompt and its hidden oracle checks
Run from the repository root: python results-2026-11-11-drafted/scripts/make_packets.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from suites import DISCRIMINATION  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "inputs"


def fence(name, text):
    return f"`{name}`:\n\n```python\n{text.rstrip()}\n```\n"


for t in DISCRIMINATION:
    head = f"## Task {t.id}\n\n**Request to the coding agent:**\n\n> {t.prompt}\n\n"
    files = "".join(fence(p, s) for p, s in sorted(t.files.items()) if p != "pytest.ini")
    (OUT / "drafter" / f"{t.id}.md").write_text(
        head + "**Baseline project** (also has `pytest.ini` with `pythonpath = .`):\n\n" + files)
    oracle = "".join(fence(p, s) for p, s in sorted(t.oracle.items()))
    (OUT / "answerer" / f"{t.id}.md").write_text(
        head + "**The hidden acceptance checks you, the task author, wrote** "
        "(work is correct if and only if all of them pass):\n\n" + oracle)
print("wrote", len(DISCRIMINATION), "tasks")
