#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

IMGUI_DIR="${1:-${IMGUI_DIR:-}}"
if [ -z "$IMGUI_DIR" ] || [ ! -d "$IMGUI_DIR" ]; then
    echo "Usage: $0 <path-to-imgui> (or set IMGUI_DIR environment variable)" >&2
    exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "Generating dcimgui bindings..."
python3 "$REPO_ROOT/dear_bindings.py" -o "$WORK/dcimgui" "$IMGUI_DIR/imgui.h"

echo "Generating dcimgui_internal bindings with IMGUI_ENABLE_TEST_ENGINE..."
printf '#define IMGUI_ENABLE_TEST_ENGINE\n' > "$WORK/imconfig_te.h"
python3 "$REPO_ROOT/dear_bindings.py" -o "$WORK/dcimgui_internal" \
    --include "$IMGUI_DIR/imgui.h" \
    --imconfig-path "$WORK/imconfig_te.h" \
    "$IMGUI_DIR/imgui_internal.h"

echo "Compiling dcimgui.cpp (no test engine)..."
g++ -std=c++11 -I"$IMGUI_DIR" -I"$WORK" -c "$WORK/dcimgui.cpp" -o "$WORK/dcimgui.o"

echo "Compiling dcimgui_internal.cpp (with IMGUI_ENABLE_TEST_ENGINE)..."
g++ -std=c++11 -DIMGUI_ENABLE_TEST_ENGINE -I"$IMGUI_DIR" -I"$WORK" -c "$WORK/dcimgui_internal.cpp" -o "$WORK/dcimgui_internal.o"

echo "Compiling and linking log_forward_test..."
g++ -std=c++11 -DIMGUI_ENABLE_TEST_ENGINE -I"$IMGUI_DIR" -I"$WORK" \
    "$SCRIPT_DIR/log_forward_test.cpp" "$WORK/dcimgui_internal.o" \
    "$IMGUI_DIR/imgui.cpp" "$IMGUI_DIR/imgui_draw.cpp" "$IMGUI_DIR/imgui_tables.cpp" "$IMGUI_DIR/imgui_widgets.cpp" \
    -o "$WORK/log_forward_test"

echo "Running log_forward_test..."
"$WORK/log_forward_test"

echo "All tests passed successfully."
