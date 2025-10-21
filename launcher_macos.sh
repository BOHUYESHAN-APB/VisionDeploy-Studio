#!/usr/bin/env bash
# macOS launcher for VisionDeploy Studio
#  - Detects python3 and runs launch_studio.py
#  - If python3 is missing, offers to run setup.py or open the Python download page

set -euo pipefail

echo "========================================="
echo "  VisionDeploy Studio - launcher (macOS)"
echo "========================================="

if command -v python3 >/dev/null 2>&1; then
    echo "✓ Found python3: $(command -v python3)"
else
    echo "⚠ python3 not found on PATH."
    echo
    echo "Options:"
    echo "  1) Try to run setup.py to install embedded Python (requires network)"
    echo "  2) Open Python downloads page in browser"
    echo "  3) Exit"
    read -rp "Choose an option [1/2/3]: " opt
    case "$opt" in
        1)
            if command -v python3 >/dev/null 2>&1; then
                python3 setup.py
            elif command -v python >/dev/null 2>&1; then
                python setup.py
            else
                /usr/bin/env python3 setup.py || true
            fi
            ;;
        2)
            open "https://www.python.org/downloads/"
            exit 1
            ;;
        *)
            exit 1
            ;;
    esac
fi

python3 launch_studio.py

exit 0
