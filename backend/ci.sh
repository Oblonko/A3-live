#!/usr/bin/env bash

echo "Running backend CI (fail-fast, non-blocking)..."
echo "=============================================="

FAILED_STEP=""

run_step () {
  NAME="$1"
  shift

  echo
  echo "▶ $NAME"
  echo "----------------------------------------"

  "$@"
  STATUS=$?

  if [ $STATUS -ne 0 ]; then
    echo "❌ $NAME FAILED"
    FAILED_STEP="$NAME"
    exit 1   # <-- FAIL FAST
  else
    echo "✅ $NAME PASSED"
  fi
}

# -----------------------
# Linting
# -----------------------
run_step "Lint (ruff)" python -m ruff backend/

# -----------------------
# Type checking
# -----------------------
run_step "Type check (mypy)" python -m mypy backend/

# -----------------------
# Tests
# -----------------------
run_step "Tests (pytest)" python -m pytest backend/

# -----------------------
# Import sanity checks
# -----------------------
run_step "Import sanity check" python - <<'EOF'
import backend.api.main
import backend.engine.worker
import backend.jobs.cron
print("Backend imports OK")
EOF

# -----------------------
# Success path
# -----------------------
echo
echo "=============================================="
echo "✅ Backend CI completed successfully"
exit 0
