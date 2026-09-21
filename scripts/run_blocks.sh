#!/usr/bin/env bash
# Run the Cassandra driver-policy experiment as independent verified blocks.
#
# Each block is one complete configured run (its own results/cassandra_policy_<...> directory).
# Because every block is self-contained and
# independently verified, a failure only loses the current block: re-running this script
# resumes from the first block that has not yet completed successfully.
#
# Usage:
#   scripts/run_blocks.sh [TOTAL_BLOCKS]
# Environment:
#   CONFIG   path to config JSON (default: config/cassandra_driver_experiments.json)
#
# Progress is tracked in results/blocks_progress/. Delete that directory to start over.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

TOTAL_BLOCKS="${1:-10}"
CONFIG="${CONFIG:-config/cassandra_driver_experiments.json}"
PROGRESS_DIR="results/cassandra_policy_blocks_progress"
VENV_PY=".venv/bin/python"
PY="python3"
[ -x "$VENV_PY" ] && VERIFY_PY="$VENV_PY" || VERIFY_PY="$PY"

mkdir -p "$PROGRESS_DIR"

echo "== Cassandra driver-policy experiment: $TOTAL_BLOCKS configured blocks =="
echo "   config:   $CONFIG"
echo "   progress: $PROGRESS_DIR"
echo

for i in $(seq 1 "$TOTAL_BLOCKS"); do
  marker="$PROGRESS_DIR/block_$(printf '%02d' "$i").done"
  if [ -f "$marker" ]; then
    echo "[block $i/$TOTAL_BLOCKS] already completed ($(cat "$marker")) - skipping"
    continue
  fi

  echo "[block $i/$TOTAL_BLOCKS] recovering cluster to a clean state..."
  "$PY" scripts/run_randomized.py --recover >/dev/null 2>&1

  echo "[block $i/$TOTAL_BLOCKS] running configured matrix..."
  if ! "$PY" scripts/run_randomized.py --config "$CONFIG"; then
    echo "[block $i/$TOTAL_BLOCKS] RUN FAILED. Recovering and stopping."
    echo "   Fix the issue (or just re-run this script) to resume from block $i."
    "$PY" scripts/run_randomized.py --recover >/dev/null 2>&1
    exit 1
  fi

  # Newest run directory is this block's output.
  RUN="$(ls -dt results/cassandra_policy_* 2>/dev/null | head -1)"
  echo "[block $i/$TOTAL_BLOCKS] verifying $RUN ..."
  if ! "$VERIFY_PY" scripts/verify_randomized.py "$RUN" >/dev/null; then
    echo "[block $i/$TOTAL_BLOCKS] VERIFICATION FAILED for $RUN. Stopping."
    echo "   Inspect it with: $VERIFY_PY scripts/verify_randomized.py $RUN"
    exit 1
  fi

  echo "$RUN" > "$marker"
  echo "[block $i/$TOTAL_BLOCKS] OK -> $RUN"
  echo
done

echo "== All $TOTAL_BLOCKS blocks completed and verified =="
echo "Run directories:"
cat "$PROGRESS_DIR"/block_*.done
