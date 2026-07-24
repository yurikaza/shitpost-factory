#!/usr/bin/env bash
# Local smoke test: render one video, never publish.
set -euo pipefail
CONCEPT="${1:-text-pov}"
cd "$(dirname "$0")/.."
DRY_RUN=true .venv/bin/python -m factory.cli run --concept "$CONCEPT"
ls -lh output/
