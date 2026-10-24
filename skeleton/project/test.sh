#!/usr/bin/env bash
# Contract check for a project skeleton. Run by the gate if present.
set -euo pipefail
python3 -m py_compile run
