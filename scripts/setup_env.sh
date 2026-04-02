#!/bin/bash
# ============================================================================
# Miko3 Talents Automation — Environment Setup (Linux/macOS)
# ============================================================================
# This script creates a Python virtual environment and installs dependencies.
#
# Usage:
#   chmod +x scripts/setup_env.sh
#   scripts/setup_env.sh
# ============================================================================

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       Miko3 Talents Automation — Environment Setup      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed."
    echo "  Install with:"
    echo "    Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "    macOS:         brew install python3"
    exit 1
fi
echo "✓ Python: $(python3 --version)"

# Check ADB
if ! command -v adb &> /dev/null; then
    echo "[WARNING] ADB is not installed or not in PATH."
    echo "  Install with:"
    echo "    Ubuntu/Debian: sudo apt install adb"
    echo "    macOS:         brew install android-platform-tools"
    echo ""
fi

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Create virtual environment
echo "[1/3] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ Virtual environment created"
else
    echo "  ✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "[2/3] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "[3/3] Installing dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✓ Environment setup complete!"
echo ""
echo "  To activate the environment:"
echo "    source venv/bin/activate"
echo ""
echo "  To run tests:"
echo "    python runner.py --help"
echo "    python runner.py --all"
echo "    python runner.py --discover"
echo "════════════════════════════════════════════════════════════"
echo ""
