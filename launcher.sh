#!/usr/bin/env bash
# POSIX launcher for VisionDeploy Studio
#  - Detects python3 and runs launch_studio.py
#  - If python3 is missing, offers to run setup.py to install an embedded Python

set -euo pipefail

echo "========================================="
echo "  VisionDeploy Studio - launcher (POSIX)"
echo "========================================="

# Check for python3
if command -v python3 >/dev/null 2>&1; then
    echo "✓ Found python3: $(command -v python3)"
else
    echo "⚠ python3 not found on PATH."
    echo
    echo "Options:"
    echo "  1) Try to run setup.py to install embedded Python (requires network)"
    echo "  2) Print download URLs and exit"
    echo "  3) Exit"
    read -rp "Choose an option [1/2/3]: " opt
    case "$opt" in
        1)
            if command -v python >/dev/null 2>&1; then
                echo "Running setup.py with available python"
                python setup.py
            elif command -v python3 >/dev/null 2>&1; then
                python3 setup.py
            else
                # Try sh invocation
                /usr/bin/env python3 setup.py || true
            fi
            ;;
        2)
            echo "Download Python from: https://www.python.org/downloads/"
            exit 1
            ;;
        *)
            exit 1
            ;;
    esac
fi

# Run the studio launcher
python3 launch_studio.py

exit 0
