#!/usr/bin/env bash
# The commands that produced this folder (the original run_rest.sh was lost
# in the upload). Run from the repository root:
#   EMI_BIN=/path/to/emi WORK=/path/outside/the/repo JOBS=4 bash results-2026-11-11/run.sh
set -u
OUT="$(cd "$(dirname "$0")" && pwd)"
: "${EMI_BIN:?set EMI_BIN to the built emi binary}"
: "${WORK:?set WORK to a scratch directory outside the repository}"
JOBS="${JOBS:-$(nproc)}"
export EMI_BIN
step() {  # name, then the command; logs wall time and exit status
  local name="$1"; shift
  local t0=$(date +%s)
  echo "=== $name: start $(date -u +%FT%TZ)"
  "$@"
  echo "=== $name: exit $? after $(( $(date +%s) - t0 ))s"
}
step validate-disc python3 -m emi_evals validate --suite discrimination --emi "$EMI_BIN" --work "$WORK" --out "$OUT/validate-disc" --fresh --jobs "$JOBS"
step disc          python3 -m emi_evals run --suite discrimination --emi "$EMI_BIN" --work "$WORK" --out "$OUT/disc" --fresh --jobs "$JOBS"
step adv           python3 -m emi_evals run --suite adversarial --emi "$EMI_BIN" --work "$WORK" --out "$OUT/adv-final" --fresh --jobs "$JOBS"
step shapes        python3 -m emi_evals run --suite shapes --emi "$EMI_BIN" --work "$WORK" --out "$OUT/shapes" --fresh --jobs "$JOBS"
step determinism   python3 -m emi_evals determinism --emi "$EMI_BIN" --work "$WORK" --out "$OUT/determinism" --fresh --jobs "$JOBS"
for d in disc adv-final shapes determinism; do
  step "report-$d" python3 -m emi_evals report --out "$OUT/$d"
done
echo "=== all done $(date -u +%FT%TZ)"
