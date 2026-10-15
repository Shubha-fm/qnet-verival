#!/usr/bin/env bash
set -euo pipefail
# Run this after the benchmark controller, with no other experiment worker active.
python3 src/random_testing.py
python3 src/performance.py
