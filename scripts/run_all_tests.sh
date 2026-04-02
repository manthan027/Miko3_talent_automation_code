#!/bin/bash
# ============================================================================
# Miko3 Talents Automation — Run All Tests (Linux/macOS)
# ============================================================================
# Activates venv and runs full test suite with report generation.
#
# Usage:
#   chmod +x scripts/run_all_tests.sh
#   scripts/run_all_tests.sh
#   scripts/run_all_tests.sh --verbose
#   scripts/run_all_tests.sh --talent video
# ============================================================================

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         Miko3 Talents Automation — Test Runner          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "[✓] Virtual environment activated"
else
    echo "[WARNING] No virtual environment found. Run scripts/setup_env.sh first."
    echo "  Attempting to run with system Python..."
fi

# Check device connection
echo ""
echo "[1/2] Checking device connection..."
adb devices
echo ""

# Run tests
echo "[2/2] Running tests..."
echo "────────────────────────────────────────────────────────────"
echo ""

if [ $# -eq 0 ]; then
    python3 runner.py --all
else
    python3 runner.py "$@"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Test run complete. Check reports/ for HTML report."
echo "════════════════════════════════════════════════════════════"
echo ""
