#!/usr/bin/env bash
# End-to-end: run generator then analyzer.
set -e
EXAMPLE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$EXAMPLE_DIR/generator" && python3 generator.py
cd "$EXAMPLE_DIR/analyzer" && python3 analyzer.py
